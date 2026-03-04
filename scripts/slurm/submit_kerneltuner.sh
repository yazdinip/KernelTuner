#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/slurm/submit_kerneltuner.sh --list <experiment_list_file> [options]

Options:
  --list <path>           Required. Text file with one experiment YAML path per line.
  --job-name <name>       Slurm job name. Default: kerneltuner
  --partition <name>      Slurm partition. Default: gpunodes
  --time <d-hh:mm>        Slurm time limit. Default: 0-02:00
  --cpus <n>              CPUs per task. Default: 4
  --mem <size>            Memory per task. Default: 24GB
  --gpu-type <name>       GPU type for --gres (e.g. rtx_a2000)
  --gpus <n>              Number of GPUs. Default: 1
  --mail-user <email>     Email for Slurm notifications (optional)
  --mail-type <types>     Slurm mail type string (optional)
  --venv-name <name>      Virtualenv directory name. Default: kerneltuner_env
  --workspace <path>      Workspace root. Default: current directory
  --log-dir <path>        Directory for Slurm .out/.err files. Default: <workspace>/slurm_jobs
  --scratch-root <path>   Override SCRATCH_ROOT used by worker script
  --artifact-root <path>  Override experiment artifact_root for this submission
  --alert-email <email>   Send worker alerts to this email (mail/sendmail on node)
  --alert-on-start        Enable start alert from worker
  --alert-on-end          Enable success/skip alert from worker
  --alert-on-fail         Enable failure alert from worker (default on)
  --dry-run               Print sbatch command without submitting

Environment vars passed through to worker script:
  RUN_COMMAND_TEMPLATE    e.g. 'ktune run-experiment --experiment "{experiment}"'
  DRY_RUN                 Set to 1 for worker-level dry run
  INSTALL_PACKAGES        Set to 0 to skip pip install
  EXTRA_PIP_PACKAGES      Extra pip packages to install in job env
  SKIP_IF_ARTIFACTS_EXIST Set to 0 to disable skip-on-existing-summary behavior
EOF
}

LIST_FILE=""
JOB_NAME="kerneltuner"
PARTITION="gpunodes"
TIME_LIMIT="0-02:00"
CPUS="4"
MEMORY="24GB"
GPU_TYPE=""
GPU_COUNT="1"
MAIL_USER=""
MAIL_TYPE=""
VENV_NAME="kerneltuner_env"
WORKSPACE_ROOT="$(pwd)"
LOG_DIR=""
SCRATCH_ROOT_OVERRIDE=""
ARTIFACT_ROOT_OVERRIDE=""
ALERT_EMAIL=""
ALERT_ON_START="0"
ALERT_ON_END="1"
ALERT_ON_FAIL="1"
DRY_RUN_SUBMIT="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list) LIST_FILE="${2:-}"; shift 2 ;;
    --job-name) JOB_NAME="${2:-}"; shift 2 ;;
    --partition) PARTITION="${2:-}"; shift 2 ;;
    --time) TIME_LIMIT="${2:-}"; shift 2 ;;
    --cpus) CPUS="${2:-}"; shift 2 ;;
    --mem) MEMORY="${2:-}"; shift 2 ;;
    --gpu-type) GPU_TYPE="${2:-}"; shift 2 ;;
    --gpus) GPU_COUNT="${2:-}"; shift 2 ;;
    --mail-user) MAIL_USER="${2:-}"; shift 2 ;;
    --mail-type) MAIL_TYPE="${2:-}"; shift 2 ;;
    --venv-name) VENV_NAME="${2:-}"; shift 2 ;;
    --workspace) WORKSPACE_ROOT="${2:-}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:-}"; shift 2 ;;
    --scratch-root) SCRATCH_ROOT_OVERRIDE="${2:-}"; shift 2 ;;
    --artifact-root) ARTIFACT_ROOT_OVERRIDE="${2:-}"; shift 2 ;;
    --alert-email) ALERT_EMAIL="${2:-}"; shift 2 ;;
    --alert-on-start) ALERT_ON_START="1"; shift ;;
    --alert-on-end) ALERT_ON_END="1"; shift ;;
    --alert-on-fail) ALERT_ON_FAIL="1"; shift ;;
    --dry-run) DRY_RUN_SUBMIT="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$LIST_FILE" ]]; then
  echo "ERROR: --list is required" >&2
  usage
  exit 2
fi

if [[ ! -f "$LIST_FILE" ]]; then
  echo "ERROR: list file not found: $LIST_FILE" >&2
  exit 1
fi

readarray -t EXP_LINES < <(awk 'NF && $1 !~ /^#/' "$LIST_FILE")
NUM_EXPERIMENTS="${#EXP_LINES[@]}"
if [[ "$NUM_EXPERIMENTS" -eq 0 ]]; then
  echo "ERROR: no experiment entries found in $LIST_FILE" >&2
  exit 1
fi

ARRAY_SPEC="0-$((NUM_EXPERIMENTS - 1))"
if [[ -z "$LOG_DIR" ]]; then
  LOG_DIR="$WORKSPACE_ROOT/slurm_jobs"
fi
mkdir -p "$LOG_DIR"

if [[ -n "$GPU_TYPE" ]]; then
  GRES="gpu:${GPU_TYPE}:${GPU_COUNT}"
else
  GRES="gpu:${GPU_COUNT}"
fi

SBATCH_CMD=(
  sbatch
  "--job-name=$JOB_NAME"
  "--partition=$PARTITION"
  "--time=$TIME_LIMIT"
  "--cpus-per-task=$CPUS"
  "--mem=$MEMORY"
  "--gres=$GRES"
  "--array=$ARRAY_SPEC"
  "--output=$LOG_DIR/${JOB_NAME}_%A_%a.out"
  "--error=$LOG_DIR/${JOB_NAME}_%A_%a.err"
)

if [[ -n "$MAIL_USER" ]]; then
  SBATCH_CMD+=("--mail-user=$MAIL_USER")
fi
if [[ -n "$MAIL_TYPE" ]]; then
  SBATCH_CMD+=("--mail-type=$MAIL_TYPE")
fi

EXPORT_VARS=("ALL")
if [[ -n "$SCRATCH_ROOT_OVERRIDE" ]]; then
  EXPORT_VARS+=("SCRATCH_ROOT=$SCRATCH_ROOT_OVERRIDE")
fi
if [[ -n "$ARTIFACT_ROOT_OVERRIDE" ]]; then
  EXPORT_VARS+=("ARTIFACT_ROOT_OVERRIDE=$ARTIFACT_ROOT_OVERRIDE")
fi
if [[ -n "$ALERT_EMAIL" ]]; then
  EXPORT_VARS+=("ALERT_EMAIL=$ALERT_EMAIL")
fi
EXPORT_VARS+=("ALERT_ON_START=$ALERT_ON_START")
EXPORT_VARS+=("ALERT_ON_END=$ALERT_ON_END")
EXPORT_VARS+=("ALERT_ON_FAIL=$ALERT_ON_FAIL")
SBATCH_CMD+=("--export=$(IFS=,; echo "${EXPORT_VARS[*]}")")

SBATCH_CMD+=(
  "$WORKSPACE_ROOT/scripts/slurm/run_kerneltuner_array.sbatch"
  "$LIST_FILE"
  "$WORKSPACE_ROOT"
  "$VENV_NAME"
)

echo "Submitting $NUM_EXPERIMENTS experiments as array: $ARRAY_SPEC"
echo "sbatch command:"
printf '  %q' "${SBATCH_CMD[@]}"
echo

if [[ "$DRY_RUN_SUBMIT" == "1" ]]; then
  echo "Dry run enabled; not submitting."
  exit 0
fi

"${SBATCH_CMD[@]}"
