#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

export KTUNE_REPO_ROOT="$REPO_ROOT"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.9}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

SCRATCH_BASE="$(ls -d /scratch/scratch-space/expires-* 2>/dev/null | sort | tail -n 1 || true)"
if [[ -n "$SCRATCH_BASE" ]]; then
  export KTUNE_SCRATCH="${KTUNE_SCRATCH:-$SCRATCH_BASE/$USER/kerneltuner}"
else
  export KTUNE_SCRATCH="${KTUNE_SCRATCH:-/tmp/$USER/kerneltuner}"
fi

VENV_PATH="${KTUNE_SCRATCH}/venv-py312"
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  "$REPO_ROOT/scripts/bootstrap_env.sh" "$VENV_PATH"
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

cd "$REPO_ROOT"

PROGRAM_ID="${PROGRAM_ID:-phase3_remainder_program_$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_PATH="${REPO_ROOT}/artifacts/${PROGRAM_ID}.log"
STATUS_PATH="${REPO_ROOT}/artifacts/${PROGRAM_ID}.status"

mkdir -p "${REPO_ROOT}/artifacts"
: > "$LOG_PATH"
: > "$STATUS_PATH"
exec > >(tee -a "$LOG_PATH") 2>&1

CURRENT_STEP="startup"

record() {
  printf '%s %s\n' "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$STATUS_PATH"
}

on_error() {
  local exit_code=$?
  record "FAIL ${CURRENT_STEP} exit_code=${exit_code}"
  exit "$exit_code"
}

trap on_error ERR

start_step() {
  CURRENT_STEP="$1"
  record "START ${CURRENT_STEP}"
}

finish_step() {
  record "DONE ${CURRENT_STEP}"
}

cleanup_remainder_artifacts() {
  local targets=(
    "artifacts/campaigns/gemm_v3_schedule_diag"
    "artifacts/campaigns/gemm_v3_aligned_reference"
    "artifacts/campaigns/layernorm_v2_microstudy"
    "artifacts/studies/gemm_v3_schedule_diag"
    "artifacts/studies/gemm_v3_aligned_reference"
    "artifacts/studies/layernorm_v2_small_microstudy"
    "artifacts/studies/layernorm_v2_large_microstudy"
    "artifacts/gemm_v3_schedule_diag"
    "artifacts/gemm_v3_aligned_reportable"
    "artifacts/layernorm_v2_small_microstudy"
    "artifacts/layernorm_v2_large_microstudy"
  )
  for target in "${targets[@]}"; do
    rm -rf "$REPO_ROOT/$target"
  done
}

validate_counter_set() {
  local experiment="$1"
  local tolerate_failure="${2:-0}"
  if [[ "$tolerate_failure" == "1" ]]; then
    if ! ktune validate-counter-set --experiment "$experiment"; then
      echo "diagnostic counter-set validation failed for $experiment; continuing because it is non-reportable"
    fi
  else
    ktune validate-counter-set --experiment "$experiment"
  fi
}

run_campaign_and_compare() {
  local label="$1"
  local campaign_spec="$2"
  shift 2
  local study_specs=("$@")
  start_step "campaign_${label}"
  ktune run-campaign --spec "$campaign_spec"
  finish_step

  for study_spec in "${study_specs[@]}"; do
    local study_label
    study_label="$(basename "$study_spec" .yaml)"
    start_step "compare_${label}_${study_label}"
    ktune compare-runs --spec "$study_spec"
    finish_step
  done
}

start_step "environment_snapshot"
echo "program_id=${PROGRAM_ID}"
echo "repo_root=${REPO_ROOT}"
echo "scratch=${KTUNE_SCRATCH}"
echo "phase3_completed_parent_studies:"
echo "  - artifacts/studies/gemm_v3_baseline_mapping"
echo "  - artifacts/studies/gemm_v3_selector_ablation"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
python3 --version
ncu --version | head -n 1
finish_step

start_step "cleanup_remainder_artifacts"
cleanup_remainder_artifacts
finish_step

start_step "phase3_remainder_preflight"
validate_counter_set "configs/experiments/gemm_v3_reportable.yaml"
validate_counter_set "configs/experiments/gemm_v3_ablation_parent.yaml"
validate_counter_set "configs/experiments/gemm_v3_ablation_frontier.yaml"
validate_counter_set "configs/experiments/gemm_v3_ablation_profiled.yaml"
validate_counter_set "configs/experiments/gemm_v3_aligned_reportable.yaml"
validate_counter_set "configs/experiments/gemm_v3_schedule_diag.yaml" 1
validate_counter_set "configs/experiments/layernorm_v2_small_microstudy.yaml"
validate_counter_set "configs/experiments/layernorm_v2_large_microstudy.yaml"

ktune validate-study --spec configs/studies/gemm_v3_schedule_diag.yaml
ktune validate-study --spec configs/studies/gemm_v3_aligned_reference.yaml
ktune validate-study --spec configs/studies/layernorm_v2_small_microstudy.yaml
ktune validate-study --spec configs/studies/layernorm_v2_large_microstudy.yaml
ktune validate-study --spec configs/studies/gemm_v3_baseline_mapping.yaml
ktune validate-study --spec configs/studies/gemm_v3_selector_ablation.yaml
finish_step

run_campaign_and_compare \
  "main_gemm_v3_schedule_diag" \
  "configs/campaigns/gemm_v3_schedule_diag.yaml" \
  "configs/studies/gemm_v3_schedule_diag.yaml"

run_campaign_and_compare \
  "main_gemm_v3_aligned_reference" \
  "configs/campaigns/gemm_v3_aligned_reference.yaml" \
  "configs/studies/gemm_v3_aligned_reference.yaml"

run_campaign_and_compare \
  "main_layernorm_v2_microstudy" \
  "configs/campaigns/layernorm_v2_microstudy.yaml" \
  "configs/studies/layernorm_v2_small_microstudy.yaml" \
  "configs/studies/layernorm_v2_large_microstudy.yaml"

run_campaign_and_compare \
  "confirm_gemm_v3_baseline_mapping" \
  "configs/campaigns/gemm_v3_baseline_mapping.yaml" \
  "configs/studies/gemm_v3_baseline_mapping.yaml"

run_campaign_and_compare \
  "confirm_gemm_v3_selector_ablation" \
  "configs/campaigns/gemm_v3_selector_ablation.yaml" \
  "configs/studies/gemm_v3_selector_ablation.yaml"

run_campaign_and_compare \
  "confirm_gemm_v3_aligned_reference" \
  "configs/campaigns/gemm_v3_aligned_reference.yaml" \
  "configs/studies/gemm_v3_aligned_reference.yaml"

run_campaign_and_compare \
  "confirm_layernorm_v2_microstudy" \
  "configs/campaigns/layernorm_v2_microstudy.yaml" \
  "configs/studies/layernorm_v2_small_microstudy.yaml" \
  "configs/studies/layernorm_v2_large_microstudy.yaml"

start_step "program_complete"
finish_step
record "DONE program_complete success"
