#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

export KTUNE_REPO_ROOT="$REPO_ROOT"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.9}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export KTUNE_SCRATCH="${KTUNE_SCRATCH:-/tmp/$USER/kerneltuner}"

VENV_PATH="${KTUNE_SCRATCH}/venv-py312"

venv_is_healthy() {
  [[ -x "$VENV_PATH/bin/python" ]] || return 1
  [[ -x "$VENV_PATH/bin/ktune" ]] || return 1
  "$VENV_PATH/bin/python" - <<'PY' >/dev/null 2>&1
import importlib.util

if importlib.util.find_spec("torch") is None or importlib.util.find_spec("triton") is None:
    raise SystemExit(1)

import torch
import triton

assert hasattr(torch, "float16")
assert hasattr(torch, "cuda")
assert hasattr(triton, "__version__")
PY
}

ensure_r6_venv() {
  if venv_is_healthy; then
    return 0
  fi

  rm -rf "$VENV_PATH"
  "$REPO_ROOT/scripts/bootstrap_env.sh" "$VENV_PATH"

  if ! venv_is_healthy; then
    echo "R6 environment bootstrap produced an unusable virtualenv at $VENV_PATH" >&2
    return 1
  fi
}

ensure_r6_venv

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

cd "$REPO_ROOT"

PROGRAM_ID="${PROGRAM_ID:-r6_final_cycle_$(date -u +%Y%m%dT%H%M%SZ)}"
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

cleanup_r6_artifacts() {
  local targets=(
    "artifacts/campaigns/gemm_final_baseline_mapping"
    "artifacts/campaigns/gemm_final_selector_ablation"
    "artifacts/campaigns/gemm_final_aligned_reference"
    "artifacts/studies/gemm_final_baseline_mapping"
    "artifacts/studies/gemm_final_selector_ablation"
    "artifacts/studies/gemm_final_aligned_reference"
    "artifacts/gemm_final_reportable"
    "artifacts/gemm_final_ablation_parent"
    "artifacts/gemm_final_ablation_frontier"
    "artifacts/gemm_final_ablation_profiled"
    "artifacts/gemm_final_aligned_reportable"
  )
  for target in "${targets[@]}"; do
    rm -rf "$REPO_ROOT/$target"
  done
}

latest_run_dir() {
  local root="$1"
  find "$root" -maxdepth 1 -type d -name 'run_*' | sort | tail -n 1
}

validate_counter_set() {
  local experiment="$1"
  ktune validate-counter-set --experiment "$experiment"
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

emit_gate_metrics() {
  local study_dir="$1"
  python - "$study_dir/study_strategy_metrics.csv" <<'PY'
import csv
import sys
from collections import defaultdict

path = sys.argv[1]
rows = list(csv.DictReader(open(path, encoding="utf-8")))

def mean(values):
    return sum(values) / len(values) if values else float("nan")

overall = defaultdict(list)
per_seed = defaultdict(lambda: defaultdict(list))

for row in rows:
    strategy_id = row["strategy_id"]
    selector_revision_id = row.get("selector_revision_id") or ""
    selector_version = row.get("selector_version") or ""
    try:
        metric = float(row["geomean_speedup_vs_default_config"])
    except (TypeError, ValueError):
        continue
    seed = str(row.get("seed") or "")
    key = None
    if strategy_id == "prune_rank":
        key = "parent"
    elif strategy_id == "naive_random_search":
        key = "random"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_frontier":
        key = "frontier"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
        key = "profiled"
    elif strategy_id == "prune_rank_profiled" and selector_version == "phase6_gemm_final":
        key = "profiled_parent"
    if key is None:
        continue
    overall[key].append(metric)
    per_seed[key][seed].append(metric)

def seed_positive_count(key):
    count = 0
    for seed in ("7", "19", "43"):
        strategy_values = per_seed[key].get(seed, [])
        parent_values = per_seed["parent"].get(seed, [])
        if strategy_values and parent_values and mean(strategy_values) > mean(parent_values):
            count += 1
    return count

parent = mean(overall["parent"])
random_v = mean(overall["random"])
frontier = mean(overall["frontier"])
profiled = mean(overall["profiled"])

print(f"PARENT_MEAN={parent:.6f}")
print(f"RANDOM_MEAN={random_v:.6f}")
print(f"FRONTIER_MEAN={frontier:.6f}")
print(f"PROFILED_MEAN={profiled:.6f}")
print(f"FRONTIER_DELTA={frontier - parent:.6f}")
print(f"PROFILED_DELTA={profiled - parent:.6f}")
print(f"FRONTIER_GAP_TO_RANDOM={random_v - frontier:.6f}")
print(f"PROFILED_GAP_TO_RANDOM={random_v - profiled:.6f}")
print(f"FRONTIER_POSITIVE_SEEDS={seed_positive_count('frontier')}")
print(f"PROFILED_POSITIVE_SEEDS={seed_positive_count('profiled')}")
PY
}

pick_best_revision() {
  python - "$1" "$2" "$3" "$4" "$5" "$6" <<'PY'
import sys

frontier_delta = float(sys.argv[1])
profiled_delta = float(sys.argv[2])
frontier_gap = float(sys.argv[3])
profiled_gap = float(sys.argv[4])
frontier_seeds = int(sys.argv[5])
profiled_seeds = int(sys.argv[6])

if profiled_delta >= frontier_delta:
    print("BEST_REVISION=profiled")
    print(f"BEST_DELTA={profiled_delta:.6f}")
    print(f"BEST_GAP_TO_RANDOM={profiled_gap:.6f}")
    print(f"BEST_POSITIVE_SEEDS={profiled_seeds}")
else:
    print("BEST_REVISION=frontier")
    print(f"BEST_DELTA={frontier_delta:.6f}")
    print(f"BEST_GAP_TO_RANDOM={frontier_gap:.6f}")
    print(f"BEST_POSITIVE_SEEDS={frontier_seeds}")
PY
}

start_step "environment_snapshot"
echo "program_id=${PROGRAM_ID}"
echo "repo_root=${REPO_ROOT}"
echo "scratch=${KTUNE_SCRATCH}"
echo "venv_path=${VENV_PATH}"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
python3 --version
ncu --version | head -n 1
python - <<'PY'
import torch
import triton
print("torch", torch.__version__)
print("triton", triton.__version__)
print("torch_float16", hasattr(torch, "float16"))
PY
finish_step

start_step "cleanup_r6_artifacts"
cleanup_r6_artifacts
finish_step

start_step "r6_preflight"
validate_counter_set "configs/experiments/gemm_final_reportable.yaml"
validate_counter_set "configs/experiments/gemm_final_ablation_parent.yaml"
validate_counter_set "configs/experiments/gemm_final_ablation_frontier.yaml"
validate_counter_set "configs/experiments/gemm_final_ablation_profiled.yaml"
validate_counter_set "configs/experiments/gemm_final_aligned_reportable.yaml"
ktune validate-study --spec configs/studies/gemm_final_baseline_mapping.yaml
ktune validate-study --spec configs/studies/gemm_final_selector_ablation.yaml
ktune validate-study --spec configs/studies/gemm_final_aligned_reference.yaml
finish_step

start_step "sanity_run_experiment"
ktune run-experiment --experiment configs/experiments/gemm_final_ablation_parent.yaml
finish_step

run_campaign_and_compare \
  "gemm_final_baseline_mapping" \
  "configs/campaigns/gemm_final_baseline_mapping.yaml" \
  "configs/studies/gemm_final_baseline_mapping.yaml"

BASELINE_STUDY_DIR="$(latest_run_dir "$REPO_ROOT/artifacts/studies/gemm_final_baseline_mapping")"
eval "$(emit_gate_metrics "$BASELINE_STUDY_DIR")"
eval "$(pick_best_revision \
  "$FRONTIER_DELTA" \
  "$PROFILED_DELTA" \
  "$FRONTIER_GAP_TO_RANDOM" \
  "$PROFILED_GAP_TO_RANDOM" \
  "$FRONTIER_POSITIVE_SEEDS" \
  "$PROFILED_POSITIVE_SEEDS")"

echo "baseline_gate_metrics parent=${PARENT_MEAN} random=${RANDOM_MEAN} frontier=${FRONTIER_MEAN} profiled=${PROFILED_MEAN} best=${BEST_REVISION}"

BASELINE_BEST_REVISION="$BEST_REVISION"
BASELINE_BEST_DELTA="$BEST_DELTA"
BASELINE_BEST_GAP_TO_RANDOM="$BEST_GAP_TO_RANDOM"
BASELINE_BEST_POSITIVE_SEEDS="$BEST_POSITIVE_SEEDS"

if python - <<PY
frontier_delta = float("${FRONTIER_DELTA}")
profiled_delta = float("${PROFILED_DELTA}")
import sys
sys.exit(0 if frontier_delta < -0.02 and profiled_delta < -0.02 else 1)
PY
then
  start_step "stop_negative_mapping_gate"
  echo "Both v5 revisions fell more than 0.02 below parent; stopping after mapping."
  finish_step
else
  run_campaign_and_compare \
    "gemm_final_selector_ablation" \
    "configs/campaigns/gemm_final_selector_ablation.yaml" \
    "configs/studies/gemm_final_selector_ablation.yaml"

  ABLATION_STUDY_DIR="$(latest_run_dir "$REPO_ROOT/artifacts/studies/gemm_final_selector_ablation")"
  eval "$(emit_gate_metrics "$ABLATION_STUDY_DIR")"
  eval "$(pick_best_revision \
    "$FRONTIER_DELTA" \
    "$PROFILED_DELTA" \
    "$FRONTIER_GAP_TO_RANDOM" \
    "$PROFILED_GAP_TO_RANDOM" \
    "$FRONTIER_POSITIVE_SEEDS" \
    "$PROFILED_POSITIVE_SEEDS")"

  echo "ablation_gate_metrics parent=${PARENT_MEAN} frontier=${FRONTIER_MEAN} profiled=${PROFILED_MEAN} best=${BEST_REVISION}"

  if python - <<PY
baseline_best_delta = float("${BASELINE_BEST_DELTA}")
import sys
sys.exit(0 if baseline_best_delta >= 0.05 else 1)
PY
  then
    run_campaign_and_compare \
      "gemm_final_aligned_reference" \
      "configs/campaigns/gemm_final_aligned_reference.yaml" \
      "configs/studies/gemm_final_aligned_reference.yaml"
  else
    start_step "skip_aligned_reference"
    echo "No v5 revision cleared +0.05 over parent in representative mapping; skipping aligned reference."
    finish_step
  fi

  if python - <<PY
baseline_best_delta = float("${BASELINE_BEST_DELTA}")
baseline_best_gap = float("${BASELINE_BEST_GAP_TO_RANDOM}")
baseline_best_seeds = int("${BASELINE_BEST_POSITIVE_SEEDS}")
ablation_best_delta = float("${BEST_DELTA}")
import sys
passes = (
    baseline_best_delta >= 0.05
    and baseline_best_gap <= 0.03
    and baseline_best_seeds >= 2
    and ablation_best_delta >= 0.05
)
sys.exit(0 if passes else 1)
PY
  then
    run_campaign_and_compare \
      "gemm_final_baseline_mapping_confirmation" \
      "configs/campaigns/gemm_final_baseline_mapping.yaml" \
      "configs/studies/gemm_final_baseline_mapping.yaml"

    run_campaign_and_compare \
      "gemm_final_selector_ablation_confirmation" \
      "configs/campaigns/gemm_final_selector_ablation.yaml" \
      "configs/studies/gemm_final_selector_ablation.yaml"
  else
    start_step "skip_confirmation_reruns"
    echo "Final confirmation gate not satisfied; skipping extra reruns."
    finish_step
  fi
fi

start_step "cycle_complete"
echo "R6 final cycle completed successfully."
finish_step
