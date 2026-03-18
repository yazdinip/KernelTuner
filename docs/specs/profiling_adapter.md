# Module Spec: Profiling Adapter

## Purpose

Define selective profiling for calibration data using named counter sets, isolated profiler execution, and explicit failure handling.

## Responsibilities

- translate profile requests into profiler invocations
- validate counter set references
- run profiling only on the calibration subset
- parse profiler outputs into typed records
- capture unsupported counters and profiling failures explicitly
- preserve enough metadata for later counter-availability and bottleneck analysis

## Non-Responsibilities

- deciding which configs should be profiled
- broad runtime benchmarking
- selector ranking itself
- report generation

## Public Inputs and Outputs

Inputs:

- profile request containing `run_id`, `strategy_id`, `kernel_id`, `shape_id`, `config_id`, and `counter_set_id`
- named counter set config
- profiling settings from `ExperimentSpec`
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

Counter set fields that affect profiling semantics:

- `diagnostic_only`
- `minimum_availability`
- `replay_mode`
- `kernel_name_regex`
- `ncu_args`

Profile status values:

- `success`
- `unsupported_counter`
- `tool_unavailable`
- `profile_failed`
- `skipped_budget`

## Internal Workflow

1. Validate that the request belongs to the calibration subset.
2. Load the named counter set config.
3. Validate that the target config compiled successfully and passed correctness checks unless the experiment explicitly profiles failing paths.
4. Assemble the profiler command for one isolated kernel execution.
5. Execute the profiler through the internal `_profile-once` helper path so profiler-side timing does not contaminate benchmark timing.
6. Capture profiler version, invocation options, replay mode, and any kernel filter metadata.
7. Parse the profiler output into normalized counter names and values.
8. Emit a `ProfileMeasurement` record regardless of success or failure.

## Persisted Artifacts Touched

- reads `configs/counters/<counter_set_id>.yaml`
- writes `profile_measurements.parquet` through the storage layer

Counter-availability and acceptance summaries are derived later by the analysis layer from these persisted profile records.

## Failure Modes and Fallback Behavior

- missing `ncu`: emit `tool_unavailable`
- unsupported counters: emit `unsupported_counter` and record which counters failed
- profiler invocation error: emit `profile_failed`
- budget exhaustion: emit `skipped_budget`

Profiling failure must not invalidate the whole experiment unless profiling is the only subject of the run.
Profiler runs are never authoritative replacements for benchmark-harness timing measurements.

## Logging and Observability Requirements

- log the counter set ID for each request
- log whether the counter set is reportable-tier or diagnostic-only
- log the profiler tool version when available
- keep stdout or stderr references when the profiler fails
- log profiling duration for each request
- log replay mode and any profiler-side kernel filter used

## Test Cases

- valid counter set request produces a normalized `counter_map`
- unsupported counters are marked explicitly
- missing profiler binary yields `tool_unavailable`
- non-calibration profile request is rejected or skipped before invocation
- profiler metadata includes tool version and invocation settings
- `minimum_availability` and `diagnostic_only` fields are preserved from the loaded config

## Extension Points

- alternate profiling tools in future research branches
- richer parser support for profiler output formats
- per-kernel counter set overrides

## Stable Contract vs Exploratory Areas

Stable contract:

- profiling is restricted to the calibration subset in v1
- named counter sets are required
- a profile record must be emitted for every attempted request
- profiling runs are isolated from benchmark timing runs
- counter-set availability is judged after collection, not assumed

Exploratory areas:

- exact counter choices
- exact profiler output parsing strategy
- exact thresholding used in future availability policies
