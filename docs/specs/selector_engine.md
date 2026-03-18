# Module Spec: Selector Engine

## Purpose

Define the bottleneck-aware selector that prunes, ranks, and chooses Triton configurations under a matched search budget.

## Responsibilities

- consume candidates, compile signals, runtime measurements, and optional profile data
- apply pruning heuristics
- rank candidates deterministically under the configured selector mode
- request additional calibration measurements only through the orchestrator
- produce a selected configuration plus rationale and budget-consumption information

## Non-Responsibilities

- generating the candidate pool
- running benchmarks directly
- collecting profiler data directly
- producing final experiment reports

## Public Inputs and Outputs

Inputs:

- shared candidate pool for a `(kernel_id, shape_scope)` unit
- `CompileSignalRecord` rows
- calibration `RuntimeMeasurement` rows
- optional `ProfileMeasurement` rows
- `SelectionBudget`
- selector mode
- orchestrator-owned measurement request interface for additional calibration-time runtime or profile requests

Outputs:

- `SelectionDecision` with:
  - `run_id`
  - `strategy_id`
  - `comparison_class`
  - `selector_mode`
  - `kernel_id`
  - `shape_scope`
  - `selected_config_id`
  - `ranked_config_ids`
  - `pruned_config_ids`
  - budget-consumption fields
  - `rationale_summary`
  - `decision_status`
  - optional `score_map`
  - optional `confidence_value`
  - optional `calibration_metadata`

v1 selector modes:

- `prune_only`
- `prune_rank`
- `prune_rank_profiled`
- `prune_rank_revised`
- `learned_rank` as an optional extension

`prune_rank_revised` is the opportunity-guided revision lane. It is reserved for heuristic changes justified by completed evidence rather than ad hoc manual tuning.

## Internal Workflow

1. Validate that the candidate pool and budgets are internally consistent.
2. Remove invalid or unrunnable candidates.
3. Apply pruning heuristics based on compile signals and any hard thresholds.
4. Rank remaining candidates using the configured selector mode and whatever signal tiers are available for that mode.
5. If additional runtime or profile measurements are allowed, request them through the orchestrator and update the ranking state.
6. Downgrade deterministically if the requested mode cannot be supported with the available signals or budget.
7. Emit the final `SelectionDecision`, including requested mode, effective mode, and consumed budget.

## Persisted Artifacts Touched

- writes `selection_decisions.parquet` through the storage layer
- reads upstream runtime, compile-signal, and profile artifacts through typed interfaces

## Failure Modes and Fallback Behavior

- empty post-prune set: emit `decision_status=failed_no_candidates`
- missing required signal inputs: degrade to the highest valid selector mode below the requested mode and record the downgrade
- exhausted budget before ranking is stable: emit partial decision with explicit status
- malformed score outputs: fail the decision and keep upstream artifacts intact

## Logging and Observability Requirements

- log requested selector mode and actual selector mode used
- log prune counts by reason
- log any downgrade from profiled, revised, or learned mode to a simpler heuristic mode
- log final selected config and a concise rationale summary
- log benchmark and profile budget consumption

## Test Cases

- invalid candidates are pruned before ranking
- held-out data is never consumed during calibration
- budget exhaustion produces an explicit partial decision
- selector downgrade path is recorded when profile data is missing
- score and ranking outputs remain deterministic under a fixed seed
- selector requests additional measurements only through the orchestrator-owned interface
- revised selector logic is evaluated under unchanged budget semantics

## Extension Points

- richer bottleneck feature engineering
- learned scoring or ranking models
- uncertainty-aware candidate acquisition for extra benchmark budget

## Stable Contract vs Exploratory Areas

Stable contract:

- selector consumes the shared candidate pool
- pruning and ranking are mandatory behaviors in v1
- the decision output must include ranked configs, pruned configs, and rationale
- selector-side measurement access is mediated by the orchestrator
- selector revisions must preserve matched-budget semantics

Exploratory areas:

- exact heuristic thresholds
- exact calibration logic
- the exact contents of the revised heuristic batch
- whether learned ranking materially improves selection
