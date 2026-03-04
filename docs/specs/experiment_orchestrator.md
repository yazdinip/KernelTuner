# Module Spec: Experiment Orchestrator

## Purpose

Define the end-to-end controller that executes experiments, enforces phase boundaries, manages run IDs, and coordinates artifact writing.

## Responsibilities

- load and validate `ExperimentSpec`
- create and manage the `run_id`
- coordinate module execution across experiment phases
- enforce calibration and held-out separation
- enforce budget accounting
- trigger artifact writes through the storage layer

## Non-Responsibilities

- implementing kernel logic
- implementing selector heuristics
- parsing profiler outputs
- generating plots directly

## Public Inputs and Outputs

Inputs:

- `ExperimentSpec`
- resolved kernel configs
- optional CLI overrides that do not violate the experiment spec

Outputs:

- complete run artifact directory
- terminal experiment status
- typed handles to in-memory `ExperimentResult` for the analysis layer

## Internal Workflow

1. Load `ExperimentSpec`.
2. Resolve one or more `KernelSpec` entries.
3. Generate candidate configs for each shape.
4. Run compile-time signal collection for the broad candidate set.
5. Benchmark or sample benchmark candidates under the experiment budget.
6. Run selective profiling on the calibration subset only.
7. Fit or calibrate selector logic if needed.
8. Apply selector and baselines under matched budgets.
9. Evaluate on held-out shapes.
10. Write artifacts and summary outputs.
11. Generate analysis tables and plots.

## Run Lifecycle

1. create run directory and initial manifest
2. resolve kernels and shapes
3. partition calibration and held-out scopes
4. execute candidate generation
5. execute measurement and profiling phases
6. execute selection and baseline phases
7. execute held-out evaluation
8. finalize artifacts and summary outputs
9. mark terminal status in the manifest

## Checkpoint Behavior

- v1 supports phase-level checkpointing through persisted artifacts
- v1 does not require automatic resume from arbitrary mid-phase failure
- a rerun may reuse prior artifacts only if the manifest and schema versions match exactly and the experiment explicitly allows reuse

## Persisted Artifacts Touched

- all run artifacts listed in `docs/05_data_model_and_artifacts.md`

## Failure Modes and Fallback Behavior

- one candidate failure must not terminate the whole run
- one kernel-scope failure may terminate only that scope if the experiment is configured to continue
- manifest finalization must happen even for partial failure
- unrecoverable schema or environment mismatch should fail the run early and clearly

## Logging and Observability Requirements

- log run creation, run ID, experiment ID, and active seed
- log phase boundaries and durations
- log per-scope failure counts
- log whether the run completed fully or partially

## Test Cases

- orchestrator writes a valid manifest before heavy work begins
- held-out data is not consumed during calibration
- partial failures still produce complete artifact metadata
- rerun with the same seed produces the same split assignment

## Extension Points

- resume support beyond phase-level checkpoints
- multi-experiment sweeps driven from one command
- richer retry policies per phase

## Stable Contract vs Exploratory Areas

Stable contract:

- the workflow above is fixed for v1
- calibration and held-out separation is enforced centrally
- storage writes are coordinated through the orchestrator and storage layer

Exploratory areas:

- exact retry policy between phases
- whether artifact reuse is enabled by default in later versions
