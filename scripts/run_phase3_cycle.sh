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

echo "phase3 cycle start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
python3 --version
ncu --version | head -n 1

ktune validate-counter-set --experiment configs/experiments/gemm_v3_reportable.yaml
ktune validate-counter-set --experiment configs/experiments/gemm_v3_aligned_reportable.yaml
ktune validate-counter-set --experiment configs/experiments/gemm_v3_schedule_diag.yaml || true
ktune validate-counter-set --experiment configs/experiments/layernorm_v2_small_microstudy.yaml
ktune validate-counter-set --experiment configs/experiments/layernorm_v2_large_microstudy.yaml

ktune validate-study --spec configs/studies/gemm_v3_baseline_mapping.yaml
ktune validate-study --spec configs/studies/gemm_v3_selector_ablation.yaml
ktune validate-study --spec configs/studies/gemm_v3_schedule_diag.yaml
ktune validate-study --spec configs/studies/gemm_v3_aligned_reference.yaml
ktune validate-study --spec configs/studies/layernorm_v2_small_microstudy.yaml
ktune validate-study --spec configs/studies/layernorm_v2_large_microstudy.yaml

ktune run-campaign --spec configs/campaigns/gemm_v3_baseline_mapping.yaml
ktune compare-runs --spec configs/studies/gemm_v3_baseline_mapping.yaml

ktune run-campaign --spec configs/campaigns/gemm_v3_selector_ablation.yaml
ktune compare-runs --spec configs/studies/gemm_v3_selector_ablation.yaml

ktune run-campaign --spec configs/campaigns/gemm_v3_schedule_diag.yaml
ktune compare-runs --spec configs/studies/gemm_v3_schedule_diag.yaml

ktune run-campaign --spec configs/campaigns/gemm_v3_aligned_reference.yaml
ktune compare-runs --spec configs/studies/gemm_v3_aligned_reference.yaml

ktune run-campaign --spec configs/campaigns/layernorm_v2_microstudy.yaml
ktune compare-runs --spec configs/studies/layernorm_v2_small_microstudy.yaml
ktune compare-runs --spec configs/studies/layernorm_v2_large_microstudy.yaml

echo "phase3 cycle complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
