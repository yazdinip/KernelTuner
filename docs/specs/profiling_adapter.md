# Module Spec: Profiling Adapter

## Purpose

Define selective profiling for calibration data using named counter sets and explicit failure handling.

## Responsibilities

- translate profile requests into profiler invocations
- validate counter set references
- run profiling only on the calibration subset
- parse profiler outputs into typed records
- capture unsupported counters and profiling failures explicitly

## Non-Responsibilities

- deciding which configs should be profiled
- broad runtime benchmarking
- selector ranking itself
- report generation

## Public Inputs and Outputs

Inputs:

- profile request containing `run_id`, `strategy_id`, `kernel_id`, `shape_id`, `config_id`, and `counter_set_id`
- named counter set config
- resolved kernel object and inputs

Outputs:

- `ProfileMeasurement` with:
  - `run_id`
  - `strategy_id`
  - `kernel_id`
  - `shape_id`
  - `config_id`
  - `counter_set_id`
  - `profile_status`
  - `counter_map`
  - `profiler_metadata`

Profile status values:

- `success`
- `unsupported_counter`
- `tool_unavailable`
- `profile_failed`
- `skipped_budget`

## Internal Workflow

1. Validate that the request belongs to the calibration subset.
2. Load the named counter set config.
3. Assemble the profiler command for the target kernel execution.
4. Execute the profiler with one isolated measurement request.
5. Parse the profiler output into normalized counter names and values.
6. Emit a `ProfileMeasurement` record regardless of success or failure.

## Persisted Artifacts Touched

- reads `configs/counters/<counter_set_id>.yaml`
- writes `profile_measurements.parquet` through the storage layer

## Failure Modes and Fallback Behavior

- missing `ncu`: emit `tool_unavailable`
- unsupported counters: emit `unsupported_counter` and record which counters failed
- profiler invocation error: emit `profile_failed`
- budget exhaustion: emit `skipped_budget`

Profiling failure must not invalidate the whole experiment unless profiling is the only subject of the run.

## Logging and Observability Requirements

- log the counter set ID for each request
- log the profiler tool version when available
- keep stdout or stderr references when the profiler fails
- log profiling duration for each request

## Test Cases

- valid counter set request produces a normalized `counter_map`
- unsupported counters are marked explicitly
- missing profiler binary yields `tool_unavailable`
- non-calibration profile request is rejected or skipped before invocation

## Extension Points

- alternate profiling tools in future research branches
- richer parser support for profiler output formats
- per-kernel counter set overrides

## Stable Contract vs Exploratory Areas

Stable contract:

- profiling is restricted to the calibration subset in v1
- named counter sets are required
- a profile record must be emitted for every attempted request

Exploratory areas:

- exact counter choices
- exact profiler output parsing strategy
