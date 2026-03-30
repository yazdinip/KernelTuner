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
else
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

cd "$REPO_ROOT"

echo "followup cycle start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
python3 --version
ncu --version | head -n 1

ktune validate-counter-set --experiment configs/experiments/gemm_reportable_g3_h2followup.yaml
ktune validate-counter-set --experiment configs/experiments/layernorm_reportable_g3_baselinefix.yaml
ktune validate-counter-set --experiment configs/experiments/gemm_reportable_g3_h4parent.yaml
ktune validate-counter-set --experiment configs/experiments/gemm_reportable_g3_v3h4.yaml
ktune validate-counter-set --experiment configs/experiments/layernorm_diag_regimes_g3.yaml || true

ktune run-experiment --experiment configs/experiments/layernorm_diag_regimes_g3.yaml
ktune run-campaign --spec configs/campaigns/h2_followup_g3_baselinefix.yaml
ktune compare-runs --spec configs/studies/h2_followup_g3_baselinefix.yaml
ktune run-campaign --spec configs/campaigns/h4_retry_g3.yaml
ktune compare-runs --spec configs/studies/h4_retry_g3.yaml

echo "followup cycle complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
