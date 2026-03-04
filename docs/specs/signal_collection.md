# Module Spec: Signal Collection

## Purpose

Define compile-time and compile-adjacent signal extraction for the broad candidate set.

## Responsibilities

- compile or lower the kernel as needed to access cheap metadata
- extract v1 compile signals
- compute occupancy-related estimates when possible
- emit explicit status and notes when signals are unavailable

## Non-Responsibilities

- runtime benchmarking
- hardware counter profiling
- selector ranking decisions
- artifact summarization

## Public Inputs and Outputs

Inputs:

- resolved kernel object
- `ProblemShape`
- `CandidateConfig`
- device metadata when needed for occupancy estimation

Outputs:

- `CompileSignalRecord` with:
  - `run_id`
  - `kernel_id`
  - `shape_id`
  - `config_id`
  - `compile_status`
  - `compile_success`
  - `register_count`
  - `shared_memory_bytes`
  - `occupancy_estimate`
  - `notes`

v1 required signals:

- register count
- shared-memory bytes
- occupancy estimate
- compile success flag
- compile status

## Internal Workflow

1. Prepare the kernel and config for compilation or lowering.
2. Invoke the cheapest path that exposes backend resource metadata.
3. Extract resource counts if available.
4. Estimate occupancy from device properties and resource usage when possible.
5. Emit a `CompileSignalRecord` whether extraction succeeds or fails.

## Persisted Artifacts Touched

- writes `compile_signals.parquet` through the storage layer

## Failure Modes and Fallback Behavior

- compile failure: emit `compile_success=false` and record the reason
- unavailable metadata field: emit null for the field and explain in `notes`
- unsupported estimation path: leave `occupancy_estimate` null and record that limitation

Signal collection must not silently drop records.

## Logging and Observability Requirements

- log signal extraction start and end for each `(kernel_id, shape_id, config_id)`
- log missing metadata paths distinctly from hard failures
- record the method used to compute occupancy estimates

## Test Cases

- successful compile produces all required fields when metadata is available
- unavailable metadata is represented without schema breakage
- compile failure produces a record rather than a missing row
- occupancy estimation path is deterministic for fixed inputs

## Extension Points

- additional compile-adjacent metadata fields
- family-specific signal extractors
- alternate occupancy estimation methods

## Stable Contract vs Exploratory Areas

Stable contract:

- v1 required signals listed above
- null values are allowed only with status or note context
- one record must be emitted per attempted candidate

Exploratory areas:

- exact compiler APIs used to extract metadata
- additional optional resource signals beyond v1
