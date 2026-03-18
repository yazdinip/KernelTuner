# Module Spec: Baseline Strategies

## Purpose

Define the comparator strategies used to evaluate the bottleneck-aware selector fairly.

## Responsibilities

- implement default-configuration baseline behavior
- implement naive search behavior over the shared candidate pool
- optionally implement a small-space oracle for analysis
- consume the same budget object semantics as the selector

## Non-Responsibilities

- candidate generation
- compile signal extraction
- profiling tool execution
- final report assembly

## Public Inputs and Outputs

Inputs:

- shared candidate pool
- optional runtime measurements
- `SelectionBudget`
- baseline mode
- orchestrator-owned measurement request interface for calibration-time runtime requests

Outputs:

- `SelectionDecision` records using the same output shape as the selector, including comparison class and budget-consumption fields

v1 baseline modes:

- `default_config`
- `naive_random_search`
- `naive_grid_search`
- `small_space_oracle` as an optional offline analysis mode

## Internal Workflow

### Default Configuration Baseline

1. Resolve the kernel's declared default config if present.
2. Fail explicitly if no declared default config exists in the kernel spec or if the default config is absent from the candidate pool.
3. Emit a baseline decision without adaptive search.

### Naive Search Baseline

1. Consume the same shared candidate pool as the selector.
2. Traverse candidates using the chosen naive strategy.
3. Request runtime measurements only through the orchestrator-owned interface and only within `max_benchmarks`.
4. Pick the best measured config under the baseline's rules.
5. Emit a `SelectionDecision`.

### Optional Small-Space Oracle

1. Operate only on restricted candidate spaces.
2. Exhaustively evaluate all valid candidates for analysis.
3. Mark the result as an oracle-only comparison, not a matched-budget baseline.

Current implementation note:

- `small_space_oracle` remains a declared extension point, but it is not implemented in the current baseline and therefore returns an explicit unsupported decision.

## Persisted Artifacts Touched

- writes baseline `SelectionDecision` records into `selection_decisions.parquet`
- reads runtime measurements and candidates through typed interfaces

## Failure Modes and Fallback Behavior

- missing default config: fail the `default_config` baseline explicitly
- default config absent from the generated candidate pool: fail explicitly
- empty candidate pool: emit explicit failure decision
- budget exhaustion: emit best-found decision with explicit status

## Logging and Observability Requirements

- log baseline mode and candidate counts
- log measurement counts consumed by naive search
- log when the optional oracle path is used and why it is not budget-comparable
- log the emitted `comparison_class`

## Test Cases

- default baseline consumes no adaptive search budget
- naive baselines use the same candidate pool and `SelectionBudget` semantics as the selector
- oracle path is marked as offline analysis only
- empty candidate pool produces a failure decision rather than a crash
- runtime measurements for baselines are requested only through the orchestrator-owned interface

## Extension Points

- additional simple baselines
- deterministic stratified random baselines
- budget sweeps for analysis

## Stable Contract vs Exploratory Areas

Stable contract:

- baselines emit the same `SelectionDecision` shape as the selector
- naive baselines operate under matched budget semantics
- oracle mode is optional and not treated as budget-comparable
- oracle or development-only outputs must be marked explicitly in the decision record

Exploratory areas:

- which naive search variant becomes the default comparator
- whether more than one naive baseline is worth keeping in v1
