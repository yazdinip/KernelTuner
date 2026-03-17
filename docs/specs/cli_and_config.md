# Module Spec: CLI and Config

## Purpose

Define the v1 command surface, config file locations, config schemas, and the mapping from CLI entrypoints to internal modules.

## Responsibilities

- expose the supported `ktune` command set
- load YAML config files into typed schema objects
- validate CLI arguments and config references
- dispatch execution to the correct internal module or orchestrator path
- present consistent exit behavior and user-facing errors

## Non-Responsibilities

- benchmark measurement logic
- candidate generation logic
- selector logic
- direct artifact persistence beyond invoking the storage layer through other modules

## Public Inputs and Outputs

### Commands

- `ktune validate-kernel --kernel configs/kernels/<kernel_id>.yaml`
- `ktune generate-configs --experiment configs/experiments/<experiment_id>.yaml`
- `ktune benchmark --experiment configs/experiments/<experiment_id>.yaml`
- `ktune collect-signals --experiment configs/experiments/<experiment_id>.yaml`
- `ktune profile --experiment configs/experiments/<experiment_id>.yaml`
- `ktune select --experiment configs/experiments/<experiment_id>.yaml`
- `ktune run-experiment --experiment configs/experiments/<experiment_id>.yaml`
- `ktune summarize --run artifacts/<experiment_id>/<run_id>/`
- `ktune compare-runs --spec configs/studies/<study_id>.yaml`

Internal-only command:

- `ktune _profile-once <payload>`

### Config locations

- `configs/kernels/<kernel_id>.yaml`
- `configs/experiments/<experiment_id>.yaml`
- `configs/counters/<counter_set_id>.yaml`
- `configs/studies/<study_id>.yaml`

### Kernel config schema

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

- `default_config`
- `correctness_policy`
- `tags`
- `notes`

Current v1 kernel families:

- `gemm`
- `layernorm`

### Experiment config schema

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
- v1 experiments must specify exactly one kernel

Allowed `study_kind` values:

- `smoke`
- `development`
- `reportable`

If omitted, `study_kind` defaults to `development`.

### Shape encoding

`ProblemShape` records are generic and dimension-driven.

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

Legacy convenience fields such as `m`, `n`, `k`, `rows`, and `hidden` may still appear in YAML; they are normalized into `dimensions` by the typed loader.

### Benchmark settings

Supported fields:

- `warmup_iterations`
- `timed_iterations`
- `timing_backend`
- `reuse_inputs`
- `store_raw_samples`

### Profiling settings

Supported fields:

- `replay_mode`
- `kernel_name_regex`
- `timeout_s`
- `cooldown_s`

### Execution settings

Supported fields:

- `cache_root`
- `scratch_root`
- `isolate_triton_cache`
- `expected_gpu_name`
- `expected_node_name`
- `expected_partition`
- `cuda_home`

Pinned reportable baseline values:

- `expected_partition: gpunodes`
- `expected_node_name: gpunode2`
- `expected_gpu_name: NVIDIA RTX A6000`
- `cuda_home: /usr/local/cuda-12.9`

### Analysis settings

Supported fields:

- `enable_small_space_oracle`
- `reportability_target`
- `confidence_interval_method`
- `workload_id`
- `comparison_tags`

### Counter set config schema

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

### Study config schema

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

Each `HypothesisSpec` entry supports:

- `hypothesis_id`
- `description`
- `comparison_pair`
- `notes`

Each `RunGroupSpec` entry supports:

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

## Internal Workflow

1. Parse CLI arguments.
2. Resolve config paths and validate they exist.
3. Load YAML into typed config objects.
4. Validate schema and cross-reference integrity, including counter-set references, reportability-sensitive settings, and study filters.
5. Dispatch to the relevant module or orchestrator.
6. Return success or propagate failure clearly.

## Persisted Artifacts Touched

- reads kernel, experiment, counter, and study YAML files
- `run-experiment` and `summarize` indirectly cause run-level artifact reads and writes
- `compare-runs` indirectly reads completed run artifacts and writes study-level artifacts

## Failure Modes and Fallback Behavior

- missing config file: fail with a path-specific error
- invalid YAML: fail with schema validation details
- unknown kernel or counter set reference: fail
- unsupported command/config combination: fail
- downstream module failure: propagate failure status and preserve stderr context

## Logging and Observability Requirements

- log resolved config paths
- log command name and top-level arguments
- log run ID or study run ID when one is created or loaded
- avoid hiding downstream stack traces during local development

## Test Cases

- valid kernel config passes `validate-kernel`
- missing required fields fail validation
- `run-experiment` rejects invalid held-out splits for reportable studies
- experiment configs with multiple kernels fail validation
- command dispatch reaches the correct module with typed config objects
- `summarize` rejects a run directory missing `manifest.json`
- `compare-runs` rejects invalid study configs and can load valid ones

## Extension Points

- additional CLI commands for diagnostics
- alternate config formats if later justified
- richer per-command overrides once the base config workflow is stable

## Stable Contract vs Exploratory Areas

Stable contract:

- command names listed above
- config file locations listed above
- single-kernel experiment constraint in v1
- required fields for kernel, experiment, counter, and study configs

Exploratory areas:

- optional command flags beyond the required surface
- richer output formatting for CLI summaries
- additional study-level filters or grouping controls
