# Module Spec: Config Space Generator

## Purpose

Define how candidate Triton configurations are generated, validated, deduplicated, and filtered before selection begins.

## Responsibilities

- expand `KernelSpec.config_parameters` into candidate configs
- enforce hard validation constraints
- generate deterministic `config_id` values
- support shape-aware filtering
- produce one shared candidate pool per `(kernel_id, shape_id)` scope

## Non-Responsibilities

- runtime benchmarking
- compile signal extraction
- selector ranking logic
- profile collection

## Public Inputs and Outputs

Inputs:

- `KernelSpec`
- `ProblemShape`
- `ExperimentSpec`

Outputs:

- `CandidateConfig` records with required fields:
  - `schema_version`
  - `experiment_id`
  - `kernel_id`
  - `shape_id`
  - `config_id`
  - `config`
  - `is_valid`
  - `validation_notes`
  - optional `generation_provenance`

## Internal Workflow

1. Read the parameter ranges from `KernelSpec.config_parameters`.
2. Produce the Cartesian product of allowed parameter values.
3. Apply hard validation rules such as required divisibility or kernel-specific constraints.
4. Canonicalize field ordering and generate deterministic `config_id` values.
5. Apply experiment-level `max_candidates` truncation deterministically on config IDs before shape expansion.
6. Apply shape-aware validation rules per `(shape, config)` pair.
7. Deduplicate normalized configs.
8. Emit the shared candidate set for downstream modules.

## Persisted Artifacts Touched

- writes `candidates.parquet` through the storage layer

## Failure Modes and Fallback Behavior

- empty candidate space after validation: fail the experiment scope explicitly
- malformed parameter specification: fail fast
- raw Cartesian space larger than `max_candidates`: truncate deterministically and record that provenance
- duplicate configs after normalization: deduplicate and record deduplication count
- invalid shape-specific config: mark `is_valid=false` with a validation note

## Logging and Observability Requirements

- log total generated candidate count before and after filtering
- log whether deterministic `max_candidates` truncation occurred
- log how many configs were invalidated by each hard constraint
- log candidate pool size passed downstream after any budget-based truncation

## Test Cases

- deterministic `config_id` generation
- deterministic `max_candidates` truncation behavior
- shape-aware filtering rejects invalid tile choices
- duplicate normalized configs are removed
- empty post-filter candidate sets fail clearly
- candidate pool remains identical across strategies for the same experiment scope

## Extension Points

- family-specific hard constraints
- stratified candidate down-selection when the raw space exceeds `max_candidates`
- richer provenance metadata for generated candidates

## Stable Contract vs Exploratory Areas

Stable contract:

- `config_id` must be deterministic
- hard validation occurs before selector and baseline logic
- downstream modules consume the same shared candidate pool
- candidate rows persist a generic `config` map rather than family-specific columns

Exploratory areas:

- exact truncation policy when the raw space is too large beyond the current canonical-order cut
- additional family-specific filtering rules discovered during implementation
