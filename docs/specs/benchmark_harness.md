# Module Spec: Benchmark Harness

## Purpose

Define correctness checking, warmup behavior, timed benchmarking, synchronization rules, retries, and runtime measurement outputs for v1.

## Responsibilities

- run reference-versus-candidate correctness checks
- execute warmup and timed benchmark loops
- collect latency statistics and throughput metrics
- emit explicit status codes for success and failure paths
- provide a consistent measurement protocol for selector and baselines

## Non-Responsibilities

- generating candidate configs
- collecting compile-time signals
- invoking Nsight Compute
- deciding which configs to select

## Public Inputs and Outputs

Inputs:

- resolved kernel object
- `ProblemShape`
- `CandidateConfig`
- benchmark settings from `ExperimentSpec`

Outputs:

- `RuntimeMeasurement` with:
  - `run_id`
  - `strategy_id`
  - `measurement_phase`
  - `kernel_id`
  - `shape_id`
  - `config_id`
  - `warmup_count`
  - `timed_run_count`
  - latency statistics
  - throughput value and unit
  - `status`

Status values:

- `success`
- `compile_failed`
- `runtime_failed`
- `invalid_config`
- `skipped_budget`
- `skipped_dependency`

## Internal Workflow

1. Materialize inputs for the requested shape and dtype.
2. Optionally run the kernel once for shape and config validation.
3. Run reference output generation and correctness validation when the measurement phase requires it.
4. Execute warmup iterations.
5. Synchronize the device before timing.
6. Execute timed iterations with explicit synchronization guarantees.
7. Compute latency statistics and throughput.
8. Emit a `RuntimeMeasurement` record.

## Persisted Artifacts Touched

- writes `runtime_measurements.parquet` through the storage layer

## Failure Modes and Fallback Behavior

- correctness mismatch: emit non-success status and stop benchmarking that config
- compile failure: emit `compile_failed`
- runtime exception: emit `runtime_failed`
- invalid config detected before execution: emit `invalid_config`

The harness must not abort the entire experiment because one config fails.

## Logging and Observability Requirements

- log `kernel_id`, `shape_id`, `config_id`, and `measurement_phase`
- log correctness failures with concise mismatch details
- log benchmark retries or skipped measurements
- record the benchmark settings used for the measurement

## Test Cases

- failed config produces a persisted non-success record
- warmup and timed-run counts match config defaults
- latency metrics are computed from the recorded sample set
- correctness failure prevents misleading runtime reporting
- one config failure does not terminate the experiment scope

## Extension Points

- alternate timing backends with equivalent synchronization semantics
- optional raw sample persistence
- benchmark batching strategies for future throughput-oriented kernels

## Stable Contract vs Exploratory Areas

Stable contract:

- benchmark behavior follows the protocol in `docs/04_experiment_protocol.md`
- status codes listed above are required
- correctness checks happen before reporting a successful measurement

Exploratory areas:

- exact retry policy for transient runtime failures
- optional raw-sample storage format
