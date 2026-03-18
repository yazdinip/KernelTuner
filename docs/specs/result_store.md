# Module Spec: Result Store

## Purpose

Define how run artifacts are laid out, written atomically, versioned, indexed, and read back.

## Responsibilities

- create run and study output directory structures
- write manifests, YAML, JSON, CSV, Parquet, and binary artifacts atomically
- enforce schema version metadata
- provide typed artifact readback
- persist environment and invocation provenance in the manifest
- finalize run status in the manifest

## Non-Responsibilities

- experiment orchestration decisions
- kernel execution
- selector or baseline logic
- deciding what analyses should exist

## Public Inputs and Outputs

Inputs:

- typed records from upstream modules
- artifact schema versions
- run metadata and environment metadata

Outputs:

- files under `artifacts/<experiment_id>/<run_id>/`
- files under `artifacts/studies/<study_id>/<run_id>/`
- typed readback handles for downstream analysis

Required run-level layout:

```text
artifacts/<experiment_id>/<run_id>/
  manifest.json
  experiment_spec.yaml
  *.parquet
  *.csv
  *.yaml
  *.json
  *.png
  logs/
```

Required study-level layout:

```text
artifacts/studies/<study_id>/<run_id>/
  manifest.json
  *.csv
  *.json
  *.png
  logs/
```

Only the manifest and the artifacts actually written for a given run or study are guaranteed to exist. Optional derived outputs are indexed only when produced.

## Internal Workflow

1. Create the output directory and initial manifest.
2. Write artifacts via temporary files.
3. Atomically move completed files into place.
4. Update manifest entries with schema version, row count, and file metadata.
5. Persist references to raw sample files, profiler stdout/stderr, or archived diffs under `logs/` when those references are present in typed records.
6. Finalize terminal run status after orchestration or comparison completes.

## Persisted Artifacts Touched

- all run-level and study-level artifacts indexed by the manifest

## Failure Modes and Fallback Behavior

- write failure: leave the previous successful artifact untouched and record failure in the manifest
- schema mismatch: reject the write or read operation
- partial artifact set due to run failure: keep the directory and finalize the manifest with partial status

## Logging and Observability Requirements

- log artifact path, schema version, and row count on successful writes
- log atomic write failures with the target artifact name
- log manifest finalization with terminal status
- log whether environment provenance was captured completely or partially

## Test Cases

- manifest is written before data artifacts
- Parquet artifact round-trip preserves schema and row count
- JSON, YAML, CSV, and binary artifacts are indexed in the manifest
- partial failure still leaves a readable manifest
- unsupported schema version fails fast on readback
- manifest captures git-dirty and Slurm metadata when provided by the orchestrator

## Extension Points

- content hashes for all artifact files
- compression policy tuning
- future analysis subdirectories beyond `logs/`

## Stable Contract vs Exploratory Areas

Stable contract:

- writes must be atomic at the file level
- `manifest.json` is the canonical output index
- environment and invocation provenance live in the manifest, not in ad hoc side files
- derived analysis artifacts are tracked in the same manifest as core artifacts

Exploratory areas:

- exact hashing policy
- compression details for large artifacts
