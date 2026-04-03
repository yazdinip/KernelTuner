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

required = ("pandas", "matplotlib", "torch", "triton")
for module in required:
    if importlib.util.find_spec(module) is None:
        raise SystemExit(1)
PY
}

ensure_r7_venv() {
  if venv_is_healthy; then
    return 0
  fi

  rm -rf "$VENV_PATH"
  "$REPO_ROOT/scripts/bootstrap_env.sh" "$VENV_PATH"

  if ! venv_is_healthy; then
    echo "R7 environment bootstrap produced an unusable virtualenv at $VENV_PATH" >&2
    return 1
  fi
}

ensure_r7_venv

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

cd "$REPO_ROOT"

PROGRAM_ID="${PROGRAM_ID:-r7_paper_hardening_$(date -u +%Y%m%dT%H%M%SZ)}"
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

cleanup_r7_artifacts() {
  local targets=(
    "artifacts/campaigns/gemm_final_budget_sweep"
    "artifacts/campaigns/gemm_final_stability_extension"
    "artifacts/studies/gemm_final_budget_sweep"
    "artifacts/studies/gemm_final_stability_extension"
    "artifacts/gemm_final_budget_sweep_b6p2"
    "artifacts/gemm_final_budget_sweep_b9p3"
    "artifacts/gemm_final_budget_sweep_b12p4"
    "artifacts/gemm_final_budget_sweep_b18p6"
    "artifacts/gemm_final_stability_reportable"
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

emit_budget_sweep_metrics() {
  local study_dir="$1"
  python - "$study_dir/study_strategy_metrics.csv" <<'PY'
import csv
import math
import sys
from collections import defaultdict

path = sys.argv[1]
rows = list(csv.DictReader(open(path, encoding="utf-8")))

def mean(values):
    return sum(values) / len(values) if values else float("nan")

metrics = defaultdict(lambda: defaultdict(list))
for row in rows:
    budget_id = str(row.get("budget_id") or "")
    strategy_id = row.get("strategy_id") or ""
    selector_revision_id = row.get("selector_revision_id") or ""
    try:
        value = float(row["geomean_speedup_vs_default_config"])
    except (TypeError, ValueError):
        continue
    key = None
    if strategy_id == "prune_rank":
        key = "parent"
    elif strategy_id == "naive_random_search":
        key = "random"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_frontier":
        key = "frontier"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
        key = "profiled"
    if key is None:
        continue
    metrics[budget_id][key].append(value)

loss_points = 0
positive_points = 0
canonical_delta = float("nan")
canonical_gap_to_random = float("nan")

for budget_id in sorted(metrics):
    parent = mean(metrics[budget_id]["parent"])
    random_v = mean(metrics[budget_id]["random"])
    frontier = mean(metrics[budget_id]["frontier"])
    profiled = mean(metrics[budget_id]["profiled"])
    if not math.isnan(parent) and not math.isnan(profiled):
        if profiled < parent:
            loss_points += 1
        if profiled > parent:
            positive_points += 1
    if budget_id == "gemm_final_budget_b12p4":
        canonical_delta = profiled - parent
        canonical_gap_to_random = random_v - profiled
    print(f"BUDGET_{budget_id}_PARENT={parent:.6f}")
    print(f"BUDGET_{budget_id}_RANDOM={random_v:.6f}")
    print(f"BUDGET_{budget_id}_FRONTIER={frontier:.6f}")
    print(f"BUDGET_{budget_id}_PROFILED={profiled:.6f}")
    print(f"BUDGET_{budget_id}_PROFILED_DELTA={profiled - parent:.6f}")
    print(f"BUDGET_{budget_id}_PROFILED_GAP_TO_RANDOM={random_v - profiled:.6f}")

print(f"PROFILED_LOSS_BUDGET_POINTS={loss_points}")
print(f"PROFILED_POSITIVE_BUDGET_POINTS={positive_points}")
print(f"CANONICAL_PROFILED_DELTA={canonical_delta:.6f}")
print(f"CANONICAL_PROFILED_GAP_TO_RANDOM={canonical_gap_to_random:.6f}")
PY
}

emit_stability_metrics() {
  local study_dir="$1"
  python - "$study_dir/study_strategy_metrics.csv" <<'PY'
import csv
import sys
from collections import defaultdict

path = sys.argv[1]
rows = list(csv.DictReader(open(path, encoding="utf-8")))

def mean(values):
    return sum(values) / len(values) if values else float("nan")

per_seed = defaultdict(lambda: defaultdict(list))
repeatability = defaultdict(list)
for row in rows:
    strategy_id = row.get("strategy_id") or ""
    selector_revision_id = row.get("selector_revision_id") or ""
    seed = str(row.get("seed") or "")
    repeat_index = row.get("repeat_index")
    try:
        value = float(row["geomean_speedup_vs_default_config"])
    except (TypeError, ValueError):
        continue
    key = None
    if strategy_id == "prune_rank":
        key = "parent"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_frontier":
        key = "frontier"
    elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
        key = "profiled"
    elif strategy_id == "naive_random_search":
        key = "random"
    if key is None:
        continue
    per_seed[key][seed].append(value)
    if seed == "7" and repeat_index not in ("", None):
        repeatability[key].append(value)

profiled_positive = 0
frontier_positive = 0
for seed in ("7", "19", "43", "61", "97"):
    parent = mean(per_seed["parent"].get(seed, []))
    profiled = mean(per_seed["profiled"].get(seed, []))
    frontier = mean(per_seed["frontier"].get(seed, []))
    if profiled > parent:
        profiled_positive += 1
    if frontier > parent:
        frontier_positive += 1
    print(f"SEED_{seed}_PARENT={parent:.6f}")
    print(f"SEED_{seed}_FRONTIER={frontier:.6f}")
    print(f"SEED_{seed}_PROFILED={profiled:.6f}")

def stdev(values):
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    return (sum((value - mu) ** 2 for value in values) / (len(values) - 1)) ** 0.5

print(f"PROFILED_POSITIVE_STABILITY_SEEDS={profiled_positive}")
print(f"FRONTIER_POSITIVE_STABILITY_SEEDS={frontier_positive}")
print(f"PROFILED_REPEATABILITY_STD={stdev(repeatability['profiled']):.6f}")
print(f"FRONTIER_REPEATABILITY_STD={stdev(repeatability['frontier']):.6f}")
print(f"PARENT_REPEATABILITY_STD={stdev(repeatability['parent']):.6f}")
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

start_step "cleanup_r7_artifacts"
cleanup_r7_artifacts
finish_step

start_step "r7_preflight"
validate_counter_set "configs/experiments/gemm_final_budget_sweep_b6p2.yaml"
validate_counter_set "configs/experiments/gemm_final_budget_sweep_b9p3.yaml"
validate_counter_set "configs/experiments/gemm_final_budget_sweep_b12p4.yaml"
validate_counter_set "configs/experiments/gemm_final_budget_sweep_b18p6.yaml"
validate_counter_set "configs/experiments/gemm_final_stability_reportable.yaml"
ktune validate-study --spec configs/studies/gemm_final_budget_sweep.yaml
ktune validate-study --spec configs/studies/gemm_final_stability_extension.yaml
finish_step

start_step "sanity_run_experiment"
ktune run-experiment --experiment configs/experiments/gemm_final_budget_sweep_b12p4.yaml
finish_step

start_step "campaign_gemm_final_budget_sweep"
ktune run-campaign --spec configs/campaigns/gemm_final_budget_sweep.yaml
finish_step

SWEEP_STUDY_DIR="$(latest_run_dir "$REPO_ROOT/artifacts/studies/gemm_final_budget_sweep")"
eval "$(emit_budget_sweep_metrics "$SWEEP_STUDY_DIR")"
echo "budget_sweep_metrics positive_points=${PROFILED_POSITIVE_BUDGET_POINTS} loss_points=${PROFILED_LOSS_BUDGET_POINTS} canonical_delta=${CANONICAL_PROFILED_DELTA} canonical_gap=${CANONICAL_PROFILED_GAP_TO_RANDOM}"

start_step "campaign_gemm_final_stability_extension"
ktune run-campaign --spec configs/campaigns/gemm_final_stability_extension.yaml
finish_step

STABILITY_STUDY_DIR="$(latest_run_dir "$REPO_ROOT/artifacts/studies/gemm_final_stability_extension")"
eval "$(emit_stability_metrics "$STABILITY_STUDY_DIR")"
echo "stability_metrics profiled_positive_seeds=${PROFILED_POSITIVE_STABILITY_SEEDS} frontier_positive_seeds=${FRONTIER_POSITIVE_STABILITY_SEEDS} profiled_repeatability_std=${PROFILED_REPEATABILITY_STD}"

start_step "headline_decision"
python - <<PY
loss_points = int("${PROFILED_LOSS_BUDGET_POINTS}")
positive_points = int("${PROFILED_POSITIVE_BUDGET_POINTS}")
positive_stability = int("${PROFILED_POSITIVE_STABILITY_SEEDS}")
canonical_delta = float("${CANONICAL_PROFILED_DELTA}")

if loss_points >= 2:
    decision = "bounded_fragile_mainline"
elif positive_points >= 3 and positive_stability >= 3:
    decision = "small_stable_mainline_improvement"
elif canonical_delta > 0:
    decision = "bounded_mainline_improvement"
else:
    decision = "mainline_inconclusive"

print(f"R7_HEADLINE_DECISION={decision}")
print(f"R7_PROFILED_POSITIVE_BUDGET_POINTS={positive_points}")
print(f"R7_PROFILED_LOSS_BUDGET_POINTS={loss_points}")
print(f"R7_PROFILED_POSITIVE_STABILITY_SEEDS={positive_stability}")
PY
finish_step

start_step "cycle_complete"
echo "R7 paper-hardening cycle completed successfully."
finish_step
