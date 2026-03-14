# Data Model and Artifacts

## Purpose

This document defines the v1 persisted artifacts, schema contracts, identifier rules, and serialization choices for `KernelTuner`.

## Storage Principles

- Human-authored configuration is stored as YAML.
- Run metadata and summaries are stored as JSON and YAML.
- Tabular experiment artifacts are stored as Parquet.
- Every run writes into its own immutable run directory.
- Missing values are represented explicitly; failed records are not dropped.
- Every persisted schema has a version.

## Artifact Root Layout

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

## Canonical Manifest

`manifest.json` is the canonical index for a run. It must include:

- `schema_version`
- `experiment_id`
- `run_id`
- `created_at_utc`
- `git_commit`
- `git_branch`
- `git_dirty`
- `environment`
- `invocation`
- `slurm`
- `artifact_files`
- `status`
- `warnings`

When a run does not execute under Slurm, the manifest `slurm` field should be present as `null` or an equivalent explicit empty object.

`artifact_files` must list every artifact with:

- logical name
- relative path
- schema version
- row count if applicable
- content hash if available

## Required Run Provenance

The manifest `environment` object must capture enough state to reconstruct or audit the run. Required fields:

- `hostname`
- `os_name`
- `os_version`
- `python_version`
- `gpu_name`
- `gpu_uuid` or an equivalent stable device identifier when available
- `nvidia_driver_version`
- `cuda_runtime_version`
- `pytorch_version`
- `triton_version`
- `ncu_version` when profiling is enabled
- `cuda_visible_devices` when available

The manifest `invocation` object must capture:

- top-level command or CLI entrypoint
- resolved experiment config path
- active seed

The manifest `slurm` object is required when Slurm was used and should capture:

- `job_id`
- `array_task_id`
- `partition`
- `node_name`
- `gres`
- `cpus_per_task`
- `mem`

Recommended optional provenance:

- `working_tree_diff_ref`
- `pip_freeze_ref`
- `cache_roots`
- `clock_policy`

## Identifier Rules

- `experiment_id`: stable identifier for a human-authored experiment config
- `run_id`: unique execution instance identifier
- `kernel_id`: stable kernel registry identifier
- `shape_id`: canonical identifier derived from a kernel family and normalized shape description
- `config_id`: canonical identifier derived from a normalized configuration record
- `strategy_id`: identifier for selector or baseline strategy

IDs must be deterministic where derived from normalized input data.

## Serialization Matrix

| Type | Serialized | Primary Location |
| --- | --- | --- |
| `KernelSpec` | Yes | `configs/kernels/<kernel_id>.yaml` |
| `ProblemShape` | Yes | Embedded in `experiment_spec.yaml`; optionally denormalized into tables |
| `CandidateConfig` | Yes | `candidates.parquet` |
| `CompileSignalRecord` | Yes | `compile_signals.parquet` |
| `RuntimeMeasurement` | Yes | `runtime_measurements.parquet` |
| `ProfileMeasurement` | Yes | `profile_measurements.parquet` |
| `SelectionBudget` | Yes | Embedded in `experiment_spec.yaml` and manifest |
| `SelectionDecision` | Yes | `selection_decisions.parquet` |
| `ExperimentSpec` | Yes | `experiment_spec.yaml` |
| `ExperimentResult` | Derived serialization | `summary.json` |

## Stable Public Types

### `KernelSpec`

Serialized as YAML. Required fields:

- `kernel_id`
- `family`
- `description`
- `shape_schema`
- `dtype_support`
- `config_parameters`
- `reference_impl`
- `supports_profiling`

Optional fields:

- `tags`
- `notes`
- `default_config`
- `correctness_policy`

### `ProblemShape`

Serialized inside `ExperimentSpec`. Required fields:

- `shape_id`
- kernel-family-specific dimensions
- `dtype`
- `layout`

Optional fields:

- `batch_group`
- `notes`

### `CandidateConfig`

Serialized in `candidates.parquet`. Required fields:

- `schema_version`
- `experiment_id`
- `kernel_id`
- `shape_id`
- `config_id`
- tiling parameters
- `num_warps`
- `num_stages`
- `is_valid`
- `validation_notes`

Optional fields:

- extra launch metadata
- generation provenance

Primary key:

- `(experiment_id, kernel_id, shape_id, config_id)`

### `CompileSignalRecord`

Serialized in `compile_signals.parquet`. Required fields:

- `schema_version`
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

Nullability rules:

- numeric signal fields may be null only when `compile_success` is `false` or the signal is unavailable and the reason is recorded in `notes`

Optional fields:

- `signal_backend`
- `occupancy_method`

Primary key:

- `(run_id, kernel_id, shape_id, config_id)`

### `RuntimeMeasurement`

Serialized in `runtime_measurements.parquet`. Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `measurement_phase`
- `kernel_id`
- `shape_id`
- `config_id`
- `warmup_count`
- `timed_run_count`
- `latency_median_us`
- `latency_mean_us`
- `latency_std_us`
- `latency_p95_us`
- `throughput_value`
- `throughput_unit`
- `status`

Optional fields:

- raw sample storage reference
- timing backend
- measurement order index
- error message
- attempt index

Primary key:

- `(run_id, strategy_id, measurement_phase, kernel_id, shape_id, config_id)`

### `ProfileMeasurement`

Serialized in `profile_measurements.parquet`. Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `kernel_id`
- `shape_id`
- `config_id`
- `counter_set_id`
- `profile_status`
- `counter_map`
- `profiler_metadata`

Optional fields:

- profiler stdout/stderr references
- notes

Primary key:

- `(run_id, strategy_id, kernel_id, shape_id, config_id, counter_set_id)`

### `SelectionBudget`

Serialized in `experiment_spec.yaml` and manifest. Required fields:

- `max_candidates`
- `max_benchmarks`
- `max_profiles`
- `seed`

Optional fields:

- `wall_clock_limit_s`

### `SelectionDecision`

Serialized in `selection_decisions.parquet`. Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `comparison_class`
- `selector_mode`
- `kernel_id`
- `shape_scope`
- `selected_config_id`
- `ranked_config_ids`
- `pruned_config_ids`
- `candidates_considered`
- `benchmarks_requested`
- `profiles_requested`
- `decision_wall_clock_s`
- `rationale_summary`
- `decision_status`

`comparison_class` must be one of:

- `matched_budget`
- `oracle_only`
- `non_comparable`

Optional fields:

- `requested_selector_mode`
- score map
- confidence value
- calibration metadata

Primary key:

- `(run_id, strategy_id, kernel_id, shape_scope)`

### `ExperimentSpec`

Serialized in YAML. Required fields:

- `experiment_id`
- `kernels`
- `shapes`
- `selector_modes`
- `baselines`
- `budgets`
- `calibration_split`
- `held_out_split`
- `artifact_root`
- `seed`

Optional fields:

- `study_kind`
- `counter_set_id`
- `benchmark_settings`
- `profiling_settings`
- `execution_settings`
- `analysis_settings`
- `notes`
- `tags`

When present, `study_kind` should be one of:

- `smoke`
- `development`
- `reportable`

If omitted, `study_kind` defaults to `development`.

### `ExperimentResult`

`ExperimentResult` is the in-memory aggregate outcome of a run. Its serialized representation is `summary.json`, not a standalone typed table.

Required summary fields:

- `schema_version`
- `experiment_id`
- `run_id`
- `terminal_status`
- `strategies`
- `best_configs`
- `aggregate_metrics`
- `comparison_warnings`
- `reportability`
- `uncertainty_metrics`
- `artifact_locations`

## Artifact Lifecycle

1. Human-authored configs define kernels, counters, and experiments.
2. The orchestrator resolves configs into runtime objects.
3. Candidate generation writes `candidates.parquet`.
4. Signal collection writes `compile_signals.parquet`.
5. Benchmarking writes `runtime_measurements.parquet`.
6. Profiling writes `profile_measurements.parquet`.
7. Selector and baselines write `selection_decisions.parquet`.
8. Analysis writes `summary.json` and optional derived outputs under `logs/` or future analysis subdirectories.

## Nullability Rules

- Identifier fields are never null.
- Status fields are never null.
- Numeric metrics may be null only if the status is not `success`.
- Free-form notes may be null.
- Missing profiling counters must remain in `counter_map` as absent keys or null values with an explanatory status.

## Versioning Rules

- All persisted schemas start at version `1`.
- Backward-incompatible changes require a version bump.
- The manifest must declare the schema version for every artifact file.
- Readers must fail fast on unsupported major schema versions.

## Stable Contracts

- Artifact layout is fixed for v1.
- YAML, JSON, and Parquet are the only supported persisted formats in v1.
- `manifest.json` is the canonical index for a run.
- Failed and skipped records must be persisted, not discarded.

## Exploratory Areas

- Exact set of optional fields added for specific kernels
- Additional derived analysis artifacts beyond `summary.json`
- Compression and partitioning strategy if artifact volume grows
