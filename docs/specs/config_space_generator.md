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
- optional experiment-level candidate caps

Outputs:

- `CandidateConfig` records with required fields:
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

## Internal Workflow

1. Read the parameter ranges from `KernelSpec.config_parameters`.
2. Produce the Cartesian product of allowed parameter values.
3. Apply hard validation rules such as required divisibility or kernel-specific constraints.
4. Apply shape-aware filtering rules.
5. Canonicalize field ordering and generate deterministic `config_id` values.
6. Deduplicate normalized configs.
7. Emit the shared candidate set for downstream modules.

## Persisted Artifacts Touched

- writes `candidates.parquet` through the storage layer

## Failure Modes and Fallback Behavior

- empty candidate space after validation: fail the experiment scope explicitly
- malformed parameter specification: fail fast
- duplicate configs after normalization: deduplicate and record deduplication count
- invalid shape-specific config: mark `is_valid=false` with a validation note

## Logging and Observability Requirements

- log total generated candidate count before and after filtering
- log how many configs were invalidated by each hard constraint
- log candidate pool size passed downstream after any budget-based truncation

## Test Cases

- deterministic `config_id` generation
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

Exploratory areas:

- exact candidate down-selection policy when the raw space is too large
- additional family-specific filtering rules discovered during implementation
