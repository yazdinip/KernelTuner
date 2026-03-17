# Data Model and Artifacts

## Purpose

This document defines the v1 persisted artifacts, schema contracts, identifier rules, and serialization choices for `KernelTuner`.

The authoritative runtime schema is implemented in `src/kernel_tuner/common/schema.py`. This document must match that code-level contract.

## Storage Principles

- Human-authored configuration is stored as YAML.
- Run metadata and summaries are stored as JSON and YAML.
- Tabular experiment artifacts are stored as Parquet or CSV, depending on the artifact role.
- Plot outputs are stored as PNG.
- Every run writes into its own immutable run directory.
- Missing values are represented explicitly; failed records are not dropped.
- Persisted schemas are versioned.

## Active Schema Version

- Current schema version: `2`

`schema_version` is embedded in typed records and in the manifest artifact index. Readers should fail fast on unsupported major schema versions.

## Artifact Root Layout

### Run-level layout

Required core files are always present for a completed run. Derived analysis artifacts are present when the upstream data needed to produce them exists and the analysis path emits them.

```text
artifacts/<experiment_id>/<run_id>/
  manifest.json
  experiment_spec.yaml
  candidates.parquet
  compile_signals.parquet
  runtime_measurements.parquet
  profile_measurements.parquet
  selection_decisions.parquet
  counter_availability.parquet
  bottleneck_signatures.parquet
  budget_usage.csv
  held_out_pairwise.csv
  held_out_per_shape.csv
  signal_runtime_correlations.csv
  counter_availability_report.csv
  opportunity_catalog.csv
  heuristic_candidates.yaml
  strategy_speedups.png
  summary.json
  logs/
```

### Study-level layout

`manifest.json` and `cross_run_summary.json` are the core study outputs. Additional CSV or PNG files are present when the comparison path emits non-empty derived outputs.

```text
artifacts/studies/<study_id>/<run_id>/
  manifest.json
  study_strategy_metrics.csv
  stability_report.csv
  hypothesis_results.csv
  opportunity_catalog.csv
  comparison_primary_metric.png
  cross_run_summary.json
  logs/
```

## Canonical Manifest

`manifest.json` is the canonical index for a run or study-comparison output. It includes:

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

When execution does not happen under Slurm, `slurm` is present as `null`.

`artifact_files` indexes each written artifact with:

- `logical_name`
- `relative_path`
- `schema_version`
- `row_count` when applicable
- `content_hash`

## Required Provenance

### `environment`

The manifest `environment` object must capture enough state to reconstruct or audit the run:

- `hostname`
- `os_name`
- `os_version`
- `python_version`
- `gpu_name`
- `gpu_uuid`
- `nvidia_driver_version`
- `cuda_runtime_version`
- `pytorch_version`
- `triton_version`
- `ncu_version`
- `cuda_visible_devices`
- `git_commit`
- `git_branch`
- `git_dirty`
- `cache_roots`

### `invocation`

The manifest `invocation` object captures:

- top-level command
- resolved experiment config path when applicable
- resolved kernel config path when applicable
- resolved counter config path when applicable
- resolved study config path when applicable
- active seed when applicable

### `slurm`

The manifest `slurm` object is required when Slurm is used and should capture:

- `job_id`
- `array_task_id`
- `partition`
- `node_name`
- `gres`
- `cpus_per_task`
- `mem`

Recommended additional provenance:

- `pip_freeze_ref`
- `working_tree_diff_ref`
- explicit cache roots
- clock policy or persistence-mode note

## Identifier Rules

- `experiment_id`: stable identifier for a human-authored experiment config
- `run_id`: unique execution instance identifier
- `kernel_id`: stable kernel registry identifier
- `shape_id`: canonical identifier derived from kernel family and normalized dimensions
- `config_id`: canonical identifier derived from a normalized configuration record
- `strategy_id`: identifier for selector or baseline strategy
- `study_id`: stable identifier for a multi-run comparison config

IDs must be deterministic where they are derived from normalized input data.

## Serialization Matrix

| Type | Serialized | Primary Location |
| --- | --- | --- |
| `KernelSpec` | Yes | `configs/kernels/<kernel_id>.yaml` |
| `ProblemShape` | Yes | embedded in `experiment_spec.yaml` |
| `CounterSetSpec` | Yes | `configs/counters/<counter_set_id>.yaml` |
| `ExperimentSpec` | Yes | `configs/experiments/<experiment_id>.yaml` and copied to `experiment_spec.yaml` |
| `StudySpec` | Yes | `configs/studies/<study_id>.yaml` |
| `CandidateConfig` | Yes | `candidates.parquet` |
| `CompileSignalRecord` | Yes | `compile_signals.parquet` |
| `RuntimeMeasurement` | Yes | `runtime_measurements.parquet` |
| `ProfileMeasurement` | Yes | `profile_measurements.parquet` |
| `SelectionDecision` | Yes | `selection_decisions.parquet` |
| `CounterAvailabilityRecord` | Derived and persisted | `counter_availability.parquet` |
| `BottleneckSignatureRecord` | Derived and persisted | `bottleneck_signatures.parquet` |
| `ExperimentResult` | Derived and persisted | `summary.json` |
| cross-run summary payload | Derived and persisted | `cross_run_summary.json` |

## Stable Public Types

### `KernelSpec`

Serialized as YAML.

Required fields:

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

Serialized inside `ExperimentSpec`.

Required fields:

- `shape_id`
- `dimensions`

Optional fields:

- `dtype`
- `layout`
- `batch_group`
- `workload_class`
- `metadata`
- `notes`

Normalization rule:

- legacy inline fields such as `m`, `n`, `k`, `rows`, and `hidden` are accepted at load time, but they are normalized into `dimensions` by the typed schema.

### `CounterSetSpec`

Serialized as YAML.

Required fields:

- `counter_set_id`
- `description`
- `tool`
- `counters`

Optional fields:

- `kernel_family_filters`
- `ncu_args`
- `replay_mode`
- `kernel_name_regex`
- `target_processes`
- `diagnostic_only`
- `minimum_availability`
- `notes`

### `ExperimentSpec`

Serialized as YAML.

Required fields:

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
- `selector_version`
- `budget_id`
- `benchmark_settings`
- `profiling_settings`
- `execution_settings`
- `analysis_settings`
- `notes`
- `tags`

Validation rules:

- `calibration_split + held_out_split == 1.0`
- reportable studies require non-zero calibration and held-out splits
- v1 experiments specify exactly one kernel
- `budgets.seed` defaults to `seed`
- `budget_id` is derived automatically when omitted

### `CandidateConfig`

Serialized in `candidates.parquet`.

Required fields:

- `schema_version`
- `experiment_id`
- `kernel_id`
- `shape_id`
- `config_id`
- `config`
- `is_valid`
- `validation_notes`

Optional fields:

- `generation_provenance`

Uniqueness key:

- `(experiment_id, kernel_id, shape_id, config_id)`

### `CompileSignalRecord`

Serialized in `compile_signals.parquet`.

Required fields:

- `schema_version`
- `run_id`
- `kernel_id`
- `shape_id`
- `config_id`
- `compile_status`
- `compile_success`

Optional fields:

- `register_count`
- `shared_memory_bytes`
- `occupancy_estimate`
- `signal_backend`
- `occupancy_method`
- `notes`

Uniqueness key:

- `(run_id, kernel_id, shape_id, config_id)`

### `RuntimeMeasurement`

Serialized in `runtime_measurements.parquet`.

Required fields:

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

- `raw_sample_ref`
- `timing_backend`
- `measurement_order_index`
- `error_message`
- `attempt_index`

Uniqueness key:

- `(run_id, strategy_id, measurement_phase, kernel_id, shape_id, config_id, attempt_index)`

### `ProfileMeasurement`

Serialized in `profile_measurements.parquet`.

Required fields:

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

- `profiler_stdout_ref`
- `profiler_stderr_ref`
- `notes`

Uniqueness key:

- `(run_id, strategy_id, kernel_id, shape_id, config_id, counter_set_id)`

### `SelectionDecision`

Serialized in `selection_decisions.parquet`.

Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `comparison_class`
- `selector_mode`
- `kernel_id`
- `shape_scope`
- `rationale_summary`
- `decision_status`

Common populated fields:

- `selected_config_id`
- `ranked_config_ids`
- `pruned_config_ids`
- `candidates_considered`
- `benchmarks_requested`
- `profiles_requested`
- `decision_wall_clock_s`
- `requested_selector_mode`
- `score_map`
- `confidence_value`
- `calibration_metadata`

Allowed `comparison_class` values:

- `matched_budget`
- `oracle_only`
- `non_comparable`

Uniqueness key:

- `(run_id, strategy_id, kernel_id, shape_scope)`

### `CounterAvailabilityRecord`

Derived and serialized in `counter_availability.parquet`.

Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `counter_set_id`
- `counter_name`
- `populated_rows`
- `total_rows`
- `non_null_fraction`
- `acceptable`

### `BottleneckSignatureRecord`

Derived and serialized in `bottleneck_signatures.parquet`.

Required fields:

- `schema_version`
- `run_id`
- `strategy_id`
- `kernel_id`
- `shape_id`
- `config_id`
- `occupancy_bucket`
- `tensor_util_bucket`
- `memory_pressure_bucket`
- `scoreboard_bucket`
- `shared_conflict_bucket`
- `compile_feasibility_bucket`
- `selected_by_strategy`
- `held_out_outcome`

Optional fields:

- `workload_class`
- `regret_to_best_measured`
- `opportunity_tags`

### `HypothesisSpec`

Serialized inside `StudySpec`.

Fields:

- `hypothesis_id`
- `description`
- `comparison_pair`
- `notes`

### `RunGroupSpec`

Serialized inside `StudySpec`.

Fields:

- `group_id`
- `experiment_ids`
- `run_dirs`
- `include_latest_runs`
- `kernel_family`
- `workload_class`
- `selector_version`
- `counter_set_id`
- `budget_id`
- `notes`

### `StudySpec`

Serialized as YAML.

Required fields:

- `study_id`
- `hypotheses`
- `run_groups`

Optional fields:

- `group_by`
- `primary_metric`
- `secondary_metrics`
- `reportability_filter`
- `environment_filter`
- `comparison_rules`
- `output_root`

### `ExperimentResult`

Derived and serialized in `summary.json`.

Required top-level fields:

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

## Run-Level Artifact Catalog

| File | Role |
| --- | --- |
| `manifest.json` | canonical run index and provenance |
| `experiment_spec.yaml` | frozen copy of the effective experiment config |
| `candidates.parquet` | candidate config table |
| `compile_signals.parquet` | broad compile-time signal table |
| `runtime_measurements.parquet` | calibration and held-out measurement table |
| `profile_measurements.parquet` | selective profiler outputs |
| `selection_decisions.parquet` | selector and baseline decisions |
| `counter_availability.parquet` | derived per-counter non-null availability records when profiling data exists |
| `bottleneck_signatures.parquet` | derived bottleneck labels and opportunity tags when analysis can construct them |
| `budget_usage.csv` | compact per-strategy budget summary when decisions exist |
| `held_out_pairwise.csv` | held-out aggregate comparison table when held-out measurements exist |
| `held_out_per_shape.csv` | held-out per-shape comparison table when held-out measurements exist |
| `signal_runtime_correlations.csv` | cheap-signal correlation summary when calibration data exists |
| `counter_availability_report.csv` | human-readable counter availability summary when profiling data exists |
| `opportunity_catalog.csv` | ranked tuning-opportunity summary when opportunities are detected |
| `heuristic_candidates.yaml` | proposed heuristic revisions derived from opportunities |
| `strategy_speedups.png` | held-out strategy speedup plot when comparison data exists |
| `summary.json` | canonical serialized run summary |

## Study-Level Artifact Catalog

| File | Role |
| --- | --- |
| `manifest.json` | canonical study-run index and provenance |
| `study_strategy_metrics.csv` | normalized per-run, per-strategy comparison table when grouped runs are available |
| `stability_report.csv` | cross-run stability and selection agreement summary when grouped runs are available |
| `hypothesis_results.csv` | supported / unsupported / inconclusive decisions when hypothesis evaluation runs |
| `opportunity_catalog.csv` | aggregated opportunity counts across grouped runs when opportunities exist |
| `comparison_primary_metric.png` | compact primary-metric comparison plot when the plotted metric is available |
| `cross_run_summary.json` | canonical serialized study summary |

## Parquet Encoding Notes

The storage layer serializes nested dict and list fields in Parquet-backed records as JSON strings. Consumers must decode fields such as:

- `CandidateConfig.config`
- `ProfileMeasurement.counter_map`
- `ProfileMeasurement.profiler_metadata`
- `SelectionDecision.score_map`
- `SelectionDecision.calibration_metadata`
- list-valued decision fields

The analysis layer already performs this decoding when it loads persisted tables.

## Stable Contracts

- `manifest.json` is the canonical index for both run and study outputs.
- Schema version `2` is the active contract for the current implementation.
- Failed, skipped, and partial records are persisted explicitly.
- Study-level comparison outputs are first-class artifacts, not ad hoc notebook outputs.
- Derived artifacts must still be indexed in the manifest like core artifacts.

## Exploratory Areas

- Additional derived artifacts beyond the current run-level and study-level outputs
- Whether future schema versions split large JSON-like columns into more normalized tables
- Whether compression or partitioning policy should change for larger studies
