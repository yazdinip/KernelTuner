# Profiling Reliability Validation On gpunode2

Purpose: record the profiling reliability fix, the counter-set audit, and the first reportable reruns on the pinned validation host.
Status: Log
Update Rule: append-only; do not rewrite past observations except to fix factual errors.
Feeds Paper Sections: operational methodology, profiling validity, limitations.
Depends On: [../04_signal_and_profiling_plan.md](../04_signal_and_profiling_plan.md), [../06_hypotheses_and_ablation_plan.md](../06_hypotheses_and_ablation_plan.md), [../08_evidence_registry.md](../08_evidence_registry.md), [../../04_experiment_protocol.md](../../04_experiment_protocol.md)

## What Changed

- preserved the CUDA toolchain exports by making `source scripts/bootstrap_env.sh <venv>` the canonical launch contract for both manual GPU-shell runs and the Slurm worker path
- updated profiler invocation and provenance capture to resolve tool paths through `CUDA_HOME/bin` before falling back to `PATH`
- tightened profiling diagnostics so artifacts distinguish missing profiler binaries, missing queried metrics, invocation failures, kernel attribution failures, and runs that return null counter values
- replaced the fragile `default_calibration` long-scoreboard counter with a queryable and populated variant on `gpunode2`

## Original Failure

- baseline smoke run: `artifacts/gemm_smoke/run_20260328T153717Z_fb053320`
- observed failure: `counter_compatibility.notes` reported `ncu executable not found`
- root cause: `bootstrap_env.sh` was executed in a subprocess, so the exported CUDA tool paths were lost before `ktune` launched profiling

## Intermediate Validation

- post-bootstrap-fix smoke run: `artifacts/gemm_smoke/run_20260328T155619Z_7fd01b07`
- result: profiler path was fixed and `counter_compatibility.validation_backend` became `ncu_query_metrics`
- remaining issue: `smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.avg` populated `0/4` rows and caused `unsupported_counter` failures in the calibration profile path
- interpretation: the environment bug was resolved, but the default smoke counter set still contained a metric that was operationally fragile on the pinned host

## Counter Audit Outcome

### `default_calibration`

- replaced `smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.avg`
- with `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct`
- reason: the original metric queried successfully but returned null values in live smoke profiling on `gpunode2`

### `compute_lite`

- validation command reported `6/6` queried metrics available
- reportable GEMM run populated every configured counter for profiled strategies
- no counter replacement was required

### `memory_lite`

- validation command reported `6/6` queried metrics available
- reportable LayerNorm run populated every configured counter for profiled strategies
- no counter replacement was required

## Rerun Results

### Smoke

- rerun: `artifacts/gemm_smoke/run_20260328T182208Z_78c5f7dc`
- `profile_failures` reduced to `{"success": 4}`
- `counter_set_accepted` was `true`
- all calibration counters populated `4/4` rows in `counter_availability_report.csv`

### GEMM reportable

- rerun: `artifacts/gemm_reportable/run_20260328T182338Z_6e92e07c`
- `terminal_status`: `success`
- `profile_failures`: `{"skipped_budget": 24, "success": 8}`
- `counter_set_accepted`: `true`
- all `compute_lite` counters populated `4/4` rows for `prune_rank_profiled` and `prune_rank_revised`
- `reportability.is_reportable`: `false`
- limiting reason: `budget_limited_decision_present`

### LayerNorm reportable

- rerun: `artifacts/layernorm_reportable/run_20260328T182601Z_5351e70a`
- `terminal_status`: `success`
- `profile_failures`: `{"success": 8, "skipped_budget": 8}`
- `counter_set_accepted`: `true`
- all `memory_lite` counters populated `4/4` rows for `prune_rank_profiled` and `prune_rank_revised`
- `reportability.is_reportable`: `false`
- limiting reason: `budget_limited_decision_present`

## Interpretation

- profiling is now operationally trustworthy on `gpunode2` for the audited smoke and reportable paths
- the resolved problem was environment propagation, not a fundamental incompatibility between Nsight Compute and the pinned host
- the remaining obstacle to study-level hypothesis testing is reportability semantics under matched-budget runs, not counter availability or profiler invocation
- this means the profiling hypothesis can now be tested operationally, but the current `validation_phase` study spec still does not admit these first reruns as study evidence because it requires reportable runs and broader repeat/seed coverage

## Immediate Follow-up

- treat the profiling tool-path issue as closed for PR `#11`
- keep `default_calibration` as a smoke-only compatibility set with intentionally robust counters
- address `budget_limited_decision_present` semantics before expecting `compare-runs --spec configs/studies/validation_phase.yaml` to ingest these reruns
- expand reportable validation coverage to satisfy the study spec's repeat and seed requirements before drawing hypothesis-level conclusions
