# Experiment Protocol

## Purpose

This document defines the scientific and measurement rules for `KernelTuner` v1. It is the authoritative source for benchmark fairness, budget semantics, calibration behavior, and result reporting.

## End-to-End Workflow

1. Load `ExperimentSpec`.
2. Resolve one or more `KernelSpec` entries.
3. Generate candidate configs for each shape.
4. Run compile-time signal collection for the broad candidate set.
5. Benchmark or sample benchmark candidates under the experiment budget.
6. Run selective profiling on the calibration subset only.
7. Fit or calibrate selector logic if needed.
8. Apply selector and baselines under matched budgets.
9. Evaluate on held-out shapes.
10. Write artifacts and summary outputs.
11. Generate analysis tables and plots.

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

## Default Protocol Values

Unless overridden by the experiment config:

- warmup iterations per timed benchmark: `10`
- timed iterations per benchmark: `30`
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

## Runtime Measurement Protocol

Each runtime benchmark must:

1. Materialize the required inputs for the target shape and dtype.
2. Run the kernel for the configured number of warmup iterations.
3. Synchronize the device before entering timed measurement.
4. Run the configured number of timed iterations.
5. Synchronize after each timed execution or use an equivalent timing method with explicit synchronization guarantees.
6. Record all latency samples and derived statistics.

The benchmark harness must mark measurement status explicitly as:

- `success`
- `compile_failed`
- `runtime_failed`
- `invalid_config`
- `skipped_budget`
- `skipped_dependency`

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

## Reporting Metrics

Required summary metrics:

- median runtime for each chosen configuration
- relative speedup versus the default baseline
- relative speedup versus the naive baseline
- budget consumption by strategy
- number of valid, failed, and skipped candidates
- calibration-to-held-out transfer behavior

Recommended analysis metrics:

- correlation between cheap signals and runtime
- rank quality of the selector compared with the small-space oracle when available
- sensitivity of selection quality to budget size

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

## Exploratory Areas

- Exact budget sizes used in individual experiments
- Exact counter sets used during calibration
- Whether a learned ranker is introduced after the heuristic path is working
