# Module Spec: CLI and Config

## Purpose

Define the v1 command surface, config file locations, config schemas, and the mapping from CLI entrypoints to internal modules.

## Responsibilities

- expose the supported `ktune` command set
- load YAML config files
- validate CLI arguments and config references
- dispatch execution to the correct internal module or orchestrator path
- present consistent exit codes and user-facing error messages

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

### Config locations

- `configs/kernels/<kernel_id>.yaml`
- `configs/experiments/<experiment_id>.yaml`
- `configs/counters/<counter_set_id>.yaml`

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
- `benchmark_settings`
- `profiling_settings`
- `execution_settings`
- `analysis_settings`
- `notes`
- `tags`

Allowed `study_kind` values:

- `smoke`
- `development`
- `reportable`

If omitted, `study_kind` should default to `development`.

Recommended `benchmark_settings` fields:

- `warmup_iterations`
- `timed_iterations`
- `timing_backend`
- `reuse_inputs`
- `store_raw_samples`

Recommended `profiling_settings` fields:

- `replay_mode`
- `kernel_name_regex`
- `timeout_s`
- `cooldown_s`

Recommended `execution_settings` fields:

- `cache_root`
- `scratch_root`
- `isolate_triton_cache`
- `expected_gpu_name`
- `expected_node_name`
- `expected_partition`
- `cuda_home`

For the current repo baseline, the expected initial values are:

- `expected_partition: gpunodes`
- `expected_node_name: gpunode2`
- `expected_gpu_name: NVIDIA RTX A6000`
- `cuda_home: /usr/local/cuda-12.9`

Recommended `analysis_settings` fields:

- `enable_small_space_oracle`
- `reportability_target`
- `confidence_interval_method`

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
- `notes`

## Internal Workflow

1. Parse CLI arguments.
2. Resolve config paths and validate they exist.
3. Load YAML into typed config objects.
4. Validate schema and cross-reference integrity, including reportability-sensitive settings such as held-out splits and counter set references.
5. Dispatch to the relevant module or the orchestrator.
6. Return a success or failure exit code.

## Persisted Artifacts Touched

- reads kernel, experiment, and counter YAML files
- `run-experiment` and `summarize` indirectly cause artifact reads and writes through the orchestrator, storage, and analysis modules

## Failure Modes and Fallback Behavior

- missing config file: exit non-zero with path-specific error
- invalid YAML: exit non-zero with schema validation error
- unknown kernel or counter set reference: exit non-zero
- unsupported command combination: exit non-zero
- downstream module failure: propagate failure status and preserve stderr context

## Logging and Observability Requirements

- log resolved config paths
- log command name and top-level arguments
- log run ID when one is created or loaded
- avoid hiding downstream stack traces during local development

## Test Cases

- valid kernel config passes `validate-kernel`
- missing required fields fail validation
- `run-experiment` rejects missing counter set references
- reportable studies reject missing or degenerate held-out configuration
- command dispatch reaches the correct module with typed config objects
- `summarize` rejects a run directory missing `manifest.json`

## Extension Points

- additional CLI commands for diagnostics
- alternate config formats if later justified
- richer per-command overrides once the base config workflow is stable

## Stable Contract vs Exploratory Areas

Stable contract:

- command names listed above
- config file locations listed above
- required fields for kernel, experiment, and counter configs

Exploratory areas:

- optional command flags beyond the required surface
- richer output formatting for CLI summaries
