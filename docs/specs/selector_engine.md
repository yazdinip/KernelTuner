# Module Spec: Selector Engine

## Purpose

Define the bottleneck-aware selector that prunes, ranks, and chooses Triton configurations under a matched search budget.

## Responsibilities

- consume candidates, compile signals, runtime measurements, and optional profile data
- apply pruning heuristics
- calibrate bottleneck-aware ranking logic on calibration data
- produce a ranked candidate list and selected configuration
- emit rationale and budget-consumption information

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

Outputs:

- `SelectionDecision` with:
  - `run_id`
  - `strategy_id`
  - `selector_mode`
  - `kernel_id`
  - `shape_scope`
  - `selected_config_id`
  - `ranked_config_ids`
  - `pruned_config_ids`
  - `rationale_summary`
  - `decision_status`
  - optional score map
  - optional confidence value

v1 selector modes:

- `prune_only`
- `prune_rank`
- `prune_rank_profiled`
- `learned_rank` as an optional extension

## Internal Workflow

1. Validate that the candidate pool and budgets are internally consistent.
2. Remove invalid or un-runnable candidates.
3. Apply pruning heuristics based on compile signals and any hard thresholds.
4. If calibration data exists, estimate which bottleneck features matter most for the current scope.
5. Rank remaining candidates using the configured selector mode.
6. If additional runtime measurements are allowed, request them through the orchestrator and update the ranking state.
7. Emit the final `SelectionDecision`.

## Persisted Artifacts Touched

- writes `selection_decisions.parquet` through the storage layer
- reads upstream runtime, compile-signal, and profile artifacts through typed interfaces

## Failure Modes and Fallback Behavior

- empty post-prune set: emit `decision_status=failed_no_candidates`
- missing required signal inputs: degrade to the highest valid selector mode below the requested mode and record the downgrade
- exhausted budget before final ranking is stable: emit partial decision with explicit status
- malformed score outputs: fail the decision and keep upstream artifacts intact

## Logging and Observability Requirements

- log requested selector mode and actual selector mode used
- log prune counts by reason
- log any downgrade from profiled or learned mode to a simpler heuristic mode
- log final selected config and a concise rationale summary

## Test Cases

- invalid candidates are pruned before ranking
- held-out data is never consumed during calibration
- budget exhaustion produces an explicit partial decision
- selector downgrade path is recorded when profile data is missing
- score or ranking outputs remain deterministic under a fixed seed

## Extension Points

- richer bottleneck feature engineering
- learned scoring or ranking models
- uncertainty-aware candidate acquisition for extra benchmark budget

## Stable Contract vs Exploratory Areas

Stable contract:

- selector consumes the shared candidate pool
- pruning and ranking are mandatory behaviors in v1
- the decision output must include ranked configs, pruned configs, and rationale

Exploratory areas:

- exact heuristic thresholds
- exact calibration logic
- whether learned ranking materially improves selection
