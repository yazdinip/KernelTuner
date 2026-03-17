# Experiment Protocol

## Purpose

This document defines the scientific and measurement rules for `KernelTuner` v1. It is the authoritative source for benchmark fairness, budget semantics, calibration behavior, and result reporting.

## End-to-End Workflow

1. Load `ExperimentSpec`.
2. Resolve exactly one `KernelSpec`.
3. Partition shapes into calibration and held-out scopes.
4. Generate candidate configs for each shape.
5. Run compile-time signal collection for the shared candidate set.
6. Benchmark only the calibration candidates requested under the experiment budget.
7. Run selective profiling on the calibration subset only.
8. Apply selector and baselines under matched budgets.
9. Evaluate on held-out shapes.
10. Optionally run analysis-only exhaustive or oracle measurements after strategy decisions are fixed.
11. Write artifacts and summary outputs.
12. Generate analysis tables, plots, counter-availability outputs, and opportunity records.

## Fairness Rules

All selector and baseline comparisons must satisfy the following:

1. Use the same kernel implementation.
2. Use the same input shapes and dtype/layout definitions.
3. Use the same candidate pool after hard validation.
4. Use the same benchmark harness and measurement settings.
5. Use the same `SelectionBudget` semantics.
6. Use the same calibration and held-out partitioning.
7. Evaluate final chosen configurations on held-out shapes using the same measurement protocol.

If any comparison violates these rules, it must be marked as non-comparable in the summary outputs.

## Search Budget Semantics

`SelectionBudget` is the controlling fairness object for selector and baseline strategies.

### Budget fields

- `max_candidates`: maximum number of candidate configurations a strategy may consider after hard validation
- `max_benchmarks`: maximum number of runtime measurements the strategy may request during selection on calibration data
- `max_profiles`: maximum number of profile measurements the strategy may request during selection on calibration data
- `wall_clock_limit_s`: optional maximum wall-clock time for the strategy during selection
- `seed`: random seed used for deterministic ordering or sampling

### Budget rules

- Candidate generation may produce more than `max_candidates`, but the experiment must derive one shared candidate subset before strategy-specific selection begins.
- Calibration-phase runtime measurements count against `max_benchmarks`.
- Calibration-phase profile collection counts against `max_profiles`.
- Held-out evaluation of the final selected configuration does not count against the selection budget.
- Profiling is optional for baselines, but a baseline cannot exceed the selector's budget object.
- If a strategy cannot complete within budget, it must emit a partial decision with explicit status rather than silently overrunning.

## Measurement Access Model

- The orchestrator is the only component allowed to invoke runtime benchmarking and profiling during strategy execution.
- Selector and baseline modules may nominate candidates for measurement, but they may not inspect calibration runtime or profile data that was never requested on their behalf.
- Calibration-time runtime measurements count against `max_benchmarks`.
- Calibration-time profile measurements count against `max_profiles`.
- Optional exhaustive evaluation, oracle measurement, or additional diagnostics may run only after strategy decisions are frozen and must be marked as `oracle_only` or otherwise non-comparable in reporting.

## Default Protocol Values

Unless overridden by the experiment config:

- warmup iterations per timed benchmark: `10`
- timed iterations per benchmark: `30`
- timing backend: CUDA events or an equivalent GPU-side timing path with explicit synchronization guarantees
- benchmark stream mode: one dedicated stream per benchmark worker unless a kernel requires another documented mode
- calibration split: `70%`
- held-out split: `30%`
- primary latency metric: median runtime in microseconds
- supplementary latency metrics: mean, standard deviation, p95

## Calibration and Held-Out Splits

- Shapes are partitioned by `shape_id`, not by individual benchmark sample.
- The split must be deterministic under the experiment seed.
- The selector may use calibration shapes for signal analysis, runtime measurement, and selective profiling.
- The selector may not consume held-out runtime or held-out profiling data during calibration.
- Held-out shapes are used only for final evaluation of chosen configurations and baselines.
- Reportable studies must include at least one calibration shape and at least one held-out shape.
- Single-shape or zero-held-out experiments are allowed only for smoke or development validation and must not be presented as final comparative results.

## Runtime Measurement Protocol

Each runtime benchmark must:

1. Materialize the required inputs for the target shape and dtype.
2. Use deterministic input generation or persist the input seed so the inputs are reproducible.
3. Compile or lower the kernel outside the timed region unless a study explicitly targets compile latency.
4. Allocate or reuse benchmark tensors outside the timed region unless allocation cost is an explicit study variable.
5. Run correctness validation before reporting a successful timing result for a new `(kernel_id, shape_id, config_id)` combination.
6. Run the kernel for the configured number of warmup iterations.
7. Synchronize the device before entering timed measurement.
8. Run the configured number of timed iterations using CUDA events or an equivalent method with explicit synchronization guarantees.
9. Record all latency samples and derived statistics.
10. Record the timing backend, stream mode, and any raw-sample reference when raw samples are stored.

The benchmark harness must mark measurement status explicitly as:

- `success`
- `compile_failed`
- `runtime_failed`
- `invalid_config`
- `skipped_budget`
- `skipped_dependency`

Runtime measurements collected under a profiler must not be reused as authoritative benchmark timings for matched-budget comparisons.

## Noise Control and Evaluation Ordering

- Held-out evaluation should measure competing final configurations in a paired or alternating order on the same host allocation whenever feasible.
- The system must record candidate and strategy ordering when randomization or adaptive measurement is involved.
- If thermal throttling, background jobs, or cluster migration appear to affect results materially, the run must be flagged with a warning in the summary.
- Host-side launch overhead diagnostics from tools such as `nsys` may be used for debugging, but they are development diagnostics unless explicitly declared as non-comparable analysis artifacts.

## Compile-Time and Compile-Adjacent Signals

The broad candidate set should collect cheap signals whenever possible, including:

- register count
- shared-memory bytes
- occupancy estimate
- compile success flag
- free-form notes for tool-specific or kernel-specific conditions

Missing values are allowed only when accompanied by a non-success status or an explanatory note.

## Selective Profiling Protocol

- Profiling is limited to the calibration subset.
- Profiling must use named counter sets defined in config files.
- Unsupported counters or failed profiler invocations must be recorded explicitly.
- The profile budget is consumed per `(kernel_id, shape_id, config_id, counter_set_id)` measurement.
- Profiling runs must be isolated from benchmark timing runs.
- The profiler tool version, invocation options, replay mode, and any kernel filters must be recorded with the profile metadata.
- Profiling should be attempted only for configs that are known to compile and satisfy correctness checks unless the experiment explicitly studies failing paths.

Counter-set policy for reportable studies:

- A Tier 1 matched-budget counter set is acceptable only if the recorded non-null availability of requested counters meets its configured `minimum_availability` threshold.
- Counter sets marked `diagnostic_only: true` may still be collected, but their outputs must not be treated as matched-budget evidence for final comparative claims.

## Reporting Metrics

Required summary metrics:

- median runtime for each chosen configuration
- relative speedup versus the default baseline
- relative speedup versus the naive baselines
- budget consumption by strategy
- number of valid, failed, and skipped candidates
- calibration-to-held-out transfer behavior
- paired held-out comparison data per shape
- reportability and comparability status for each strategy
- environment provenance summary sufficient to reconstruct the run

Recommended analysis metrics:

- correlation between cheap signals and runtime
- counter availability by strategy and counter set
- bottleneck signature distribution
- opportunity counts derived from profiler and runtime evidence
- rank quality of the selector compared with the small-space oracle when available
- sensitivity of selection quality to budget size
- uncertainty estimates such as confidence intervals or bootstrap intervals for aggregate speedup metrics

## Reportable Study Requirements

A study is considered reportable only if all of the following hold:

- environment provenance is captured completely enough to recreate the run
- selector and baselines are compared under matched budgets or are explicitly marked non-comparable
- calibration and held-out data remain disjoint
- at least one matched-budget naive baseline is present
- held-out evaluation uses the same measurement protocol across compared strategies
- summary outputs include uncertainty estimates or an explicit statement of why they are unavailable
- any Tier 1 counter set used for reportable profiling meets its availability threshold or is explicitly downgraded

## Negative-Result Reporting Rule

If the selector does not outperform naive baselines, the report must still include:

- whether budget usage was fair,
- which signals failed to predict performance,
- where pruning removed useful candidates or ranking missed good ones,
- whether the failure appears workload-specific or more general.

## Stable Contracts

- The workflow in this document is fixed for v1.
- Calibration and held-out data must stay disjoint.
- Held-out evaluation is separate from the selection budget.
- All failed and skipped cases must be recorded explicitly.
- Runtime and profile measurements during selection are brokered by the orchestrator.
- Smoke or development-only runs must not be confused with reportable matched-budget studies.

## Exploratory Areas

- Exact budget sizes used in individual experiments
- Exact counter sets used during calibration
- Whether a learned ranker is introduced after the heuristic path is working
