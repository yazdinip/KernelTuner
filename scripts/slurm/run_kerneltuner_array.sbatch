#!/bin/bash --login
#SBATCH --job-name=kerneltuner
#SBATCH --partition=gpunodes
#SBATCH --time=0-02:00
#SBATCH -c 4
#SBATCH --mem=24GB
#SBATCH --gres=gpu:1
#SBATCH --array=0-0
#SBATCH --output=slurm_jobs/kerneltuner_%A_%a.out
#SBATCH --error=slurm_jobs/kerneltuner_%A_%a.err

set -euo pipefail

send_alert() {
  local phase="$1"
  local details="$2"
  local email="${ALERT_EMAIL:-}"
  if [[ -z "$email" ]]; then
    return 0
  fi
  local subject_prefix="${ALERT_SUBJECT_PREFIX:-[KernelTuner]}"
  local subject="${subject_prefix} ${phase} job=${SLURM_JOB_ID:-local} task=${SLURM_ARRAY_TASK_ID:-0}"
  local body
  body=$(
    cat <<EOF
host: $(hostname)
job_id: ${SLURM_JOB_ID:-local}
task_id: ${SLURM_ARRAY_TASK_ID:-0}
phase: ${phase}
cwd: $(pwd)
details: ${details}
EOF
  )
  if command -v mail >/dev/null 2>&1; then
    printf '%s\n' "$body" | mail -s "$subject" "$email" || true
  elif command -v sendmail >/dev/null 2>&1; then
    {
      printf 'To: %s\n' "$email"
      printf 'Subject: %s\n' "$subject"
      printf '\n%s\n' "$body"
    } | sendmail -t || true
  fi
}

on_exit() {
  local exit_code=$?
  if [[ $exit_code -ne 0 && "${ALERT_ON_FAIL:-1}" == "1" ]]; then
    send_alert "FAIL" "exit_code=${exit_code}"
  fi
}
trap on_exit EXIT

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <experiment_list_file> [workspace_root] [venv_name]" >&2
  exit 2
fi

EXPERIMENT_LIST_FILE="$1"
WORKSPACE_ROOT="${2:-$SLURM_SUBMIT_DIR}"
VENV_NAME="${3:-kerneltuner_env}"

if [[ ! -f "$EXPERIMENT_LIST_FILE" ]]; then
  echo "ERROR: Experiment list file not found: $EXPERIMENT_LIST_FILE" >&2
  exit 1
fi

mkdir -p "$WORKSPACE_ROOT/slurm_jobs"

mapfile -t EXPERIMENTS < <(awk 'NF && $1 !~ /^#/' "$EXPERIMENT_LIST_FILE")

if [[ "${#EXPERIMENTS[@]}" -eq 0 ]]; then
  echo "ERROR: No experiments found in $EXPERIMENT_LIST_FILE" >&2
  exit 1
fi

TASK_ID="${SLURM_ARRAY_TASK_ID:-0}"
if (( TASK_ID < 0 || TASK_ID >= ${#EXPERIMENTS[@]} )); then
  echo "ERROR: SLURM_ARRAY_TASK_ID=$TASK_ID out of range (0..$((${#EXPERIMENTS[@]} - 1)))" >&2
  exit 1
fi

EXPERIMENT_CFG="${EXPERIMENTS[$TASK_ID]}"
if [[ ! -f "$EXPERIMENT_CFG" ]]; then
  echo "ERROR: Experiment config not found: $EXPERIMENT_CFG" >&2
  exit 1
fi

resolve_artifact_root() {
  local cfg_path="$1"
  local raw_root
  raw_root="$(awk -F': *' '$1=="artifact_root"{print $2; exit}' "$cfg_path" | tr -d "\"'[:space:]")"
  if [[ -z "$raw_root" ]]; then
    raw_root="artifacts"
  fi
  if [[ "$raw_root" = /* ]]; then
    printf '%s\n' "$raw_root"
  else
    printf '%s/%s\n' "$WORKSPACE_ROOT" "$raw_root"
  fi
}

echo ">>> KernelTuner Slurm Task <<<"
echo "Working directory: $WORKSPACE_ROOT"
echo "Experiment list:   $EXPERIMENT_LIST_FILE"
echo "Array task id:     $TASK_ID"
echo "Experiment config: $EXPERIMENT_CFG"
if [[ "${ALERT_ON_START:-0}" == "1" ]]; then
  send_alert "START" "experiment_cfg=${EXPERIMENT_CFG}"
fi

EXPERIMENT_ID="$(awk -F': *' '$1=="experiment_id"{print $2; exit}' "$EXPERIMENT_CFG" | tr -d "\"'[:space:]")"
if [[ -z "${EXPERIMENT_ID}" ]]; then
  EXPERIMENT_ID="$(basename "$EXPERIMENT_CFG" .yaml)"
fi

EXPERIMENT_TO_RUN="$EXPERIMENT_CFG"

SCRATCH_ROOT="${SCRATCH_ROOT:-}"
if [[ -z "$SCRATCH_ROOT" ]]; then
  SCRATCH_ROOT="$(ls -d /scratch/scratch-space/expires-* 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$SCRATCH_ROOT" ]]; then
  SCRATCH_ROOT="$WORKSPACE_ROOT/.scratch/$USER"
fi
mkdir -p "$SCRATCH_ROOT"
echo "Scratch root: $SCRATCH_ROOT"

if [[ -n "${ARTIFACT_ROOT_OVERRIDE:-}" ]]; then
  mkdir -p "$SCRATCH_ROOT/kerneltuner_tmp"
  OVERRIDE_CFG="$SCRATCH_ROOT/kerneltuner_tmp/${EXPERIMENT_ID}_${SLURM_JOB_ID:-local}_${TASK_ID}.yaml"
  awk -v override="$ARTIFACT_ROOT_OVERRIDE" '
    BEGIN { seen = 0 }
    /^artifact_root:/ { print "artifact_root: " override; seen = 1; next }
    { print }
    END { if (seen == 0) print "artifact_root: " override }
  ' "$EXPERIMENT_CFG" > "$OVERRIDE_CFG"
  EXPERIMENT_TO_RUN="$OVERRIDE_CFG"
  echo "Using artifact_root override: $ARTIFACT_ROOT_OVERRIDE"
fi

if [[ "${SKIP_IF_ARTIFACTS_EXIST:-1}" == "1" ]]; then
  ARTIFACT_ROOT_RESOLVED="$(resolve_artifact_root "$EXPERIMENT_TO_RUN")"
  if compgen -G "$ARTIFACT_ROOT_RESOLVED/$EXPERIMENT_ID/*/summary.json" > /dev/null; then
    echo ">>> Found existing summary for experiment_id=$EXPERIMENT_ID; skipping."
    if [[ "${ALERT_ON_END:-0}" == "1" ]]; then
      send_alert "SKIP" "existing_summary=1 experiment_id=${EXPERIMENT_ID}"
    fi
    exit 0
  fi
fi

VENV_PATH="$SCRATCH_ROOT/$VENV_NAME"
if [[ ! -d "$VENV_PATH" ]]; then
  echo "Creating virtual environment at $VENV_PATH"
  python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

if [[ "${INSTALL_PACKAGES:-1}" == "1" ]]; then
  echo "Installing dependencies into $VENV_PATH"
  pip install --upgrade pip
  pip install --no-cache-dir -e "$WORKSPACE_ROOT" pyyaml pandas pyarrow
  if [[ -n "${EXTRA_PIP_PACKAGES:-}" ]]; then
    pip install --no-cache-dir ${EXTRA_PIP_PACKAGES}
  fi
fi

export PYTHONPATH="$WORKSPACE_ROOT/src:${PYTHONPATH:-}"

RUN_COMMAND_TEMPLATE="${RUN_COMMAND_TEMPLATE:-ktune run-experiment --experiment \"{experiment}\"}"
EXPERIMENT_TOKEN='{experiment}'
WORKSPACE_TOKEN='{workspace}'
RUN_COMMAND="${RUN_COMMAND_TEMPLATE//$EXPERIMENT_TOKEN/$EXPERIMENT_TO_RUN}"
RUN_COMMAND="${RUN_COMMAND//$WORKSPACE_TOKEN/$WORKSPACE_ROOT}"

echo "Run command: $RUN_COMMAND"
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN=1 set; not executing."
  exit 0
fi

bash -lc "$RUN_COMMAND"

echo ">>> Task complete"
if [[ "${ALERT_ON_END:-1}" == "1" ]]; then
  send_alert "SUCCESS" "experiment_cfg=${EXPERIMENT_TO_RUN}"
fi
