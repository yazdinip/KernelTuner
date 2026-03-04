# Module Spec: Result Store

## Purpose

Define how run artifacts are laid out, written atomically, versioned, indexed, and read back.

## Responsibilities

- create run directory structure
- write manifests, YAML, JSON, and Parquet artifacts
- enforce schema version metadata
- provide typed artifact readback
- finalize run status in the manifest

## Non-Responsibilities

- experiment orchestration decisions
- kernel execution
- selector or baseline logic
- plot generation

## Public Inputs and Outputs

Inputs:

- typed records from upstream modules
- artifact schema versions
- run metadata and environment metadata

Outputs:

- files under `artifacts/<experiment_id>/<run_id>/`
- typed readback handles for downstream analysis

Required v1 layout:

```text
artifacts/<experiment_id>/<run_id>/
  manifest.json
  experiment_spec.yaml
  candidates.parquet
  compile_signals.parquet
  runtime_measurements.parquet
  profile_measurements.parquet
  selection_decisions.parquet
  summary.json
  logs/
```

## Internal Workflow

1. Create the run directory and initial manifest.
2. Write artifacts via temporary files.
3. Atomically move completed files into place.
4. Update manifest entries with schema version, row count, and file metadata.
5. Finalize terminal run status after orchestration completes.

## Persisted Artifacts Touched

- all required run artifacts

## Failure Modes and Fallback Behavior

- write failure: leave the previous successful artifact untouched and record failure in the manifest
- schema mismatch: reject the write or read operation
- partial artifact set due to run failure: keep the directory and finalize the manifest with partial status

## Logging and Observability Requirements

- log artifact path, schema version, and row count on successful writes
- log atomic write failures with the target artifact name
- log manifest finalization with terminal status

## Test Cases

- manifest is written before data artifacts
- Parquet artifact round-trip preserves schema and row count
- partial failure still leaves a readable manifest
- unsupported schema version fails fast on readback

## Extension Points

- content hashes for all artifact files
- compression policy tuning
- future analysis subdirectories beyond `logs/`

## Stable Contract vs Exploratory Areas

Stable contract:

- artifact layout is fixed for v1
- writes must be atomic at the file level
- `manifest.json` is the canonical run index

Exploratory areas:

- exact hashing policy
- compression details for large artifacts
