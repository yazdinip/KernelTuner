# System Overview

## Purpose

This document defines the high-level architecture for the `KernelTuner` v1 research prototype. It is the authoritative overview of module boundaries, end-to-end workflow, data flow, and external dependencies.

## System Goal

The system takes one kernel specification and one experiment configuration, generates candidate Triton schedules, gathers cheap and selective expensive signals, applies selector and baseline strategies under matched budgets, and writes reproducible artifacts for run-level and study-level analysis.

## End-to-End Workflow

1. Load `ExperimentSpec`.
2. Resolve exactly one `KernelSpec` for the experiment.
3. Partition shapes into calibration and held-out scopes.
4. Generate candidate configs for each shape.
5. Run compile-time signal collection for the shared candidate set.
6. Let selector and baseline strategies request calibration-time runtime measurements through the orchestrator under one shared `SelectionBudget`.
7. Run selective profiling only for approved calibration requests and only within the profile budget.
8. Apply selector and baselines under matched budgets.
9. Evaluate final chosen configurations on held-out shapes with the same benchmark protocol.
10. Optionally run analysis-only exhaustive or oracle measurements after strategy decisions, marking those outputs as non-comparable or oracle-only.
11. Write artifacts and run-level summary outputs.
12. Generate derived tables, plots, counter-availability reports, and opportunity records.
13. Optionally aggregate multiple completed runs through a `StudySpec` and `ktune compare-runs`.

## Architecture Diagram

```text
configs/experiments/*.yaml
            |
            v
  +------------------------+
  | experiment_orchestrator|
  +------------------------+
     |          |         |
     |          |         v
     |          |   +------------+
     |          +-> | baselines  |
     |              +------------+
     v
+------------+     +------------------+     +------------------+
| kernels    | --> | config_space     | --> | signal_collection|
+------------+     +------------------+     +------------------+
      |                       |                         |
      |                       v                         v
      |                +--------------+         +---------------+
      +--------------> | benchmark    | <-----> | profiling     |
                       +--------------+         +---------------+
                               |
                               v
                       +---------------+
                       | selector      |
                       +---------------+
                               |
                               v
                       +---------------+
                       | storage       |
                       +---------------+
                               |
                               v
                       +---------------+        +------------------+
                       | analysis      | -----> | compare-runs     |
                       +---------------+        +------------------+
```

## Package Layout

```text
src/kernel_tuner/
  kernels/
  config_space/
  benchmark/
  signals/
  profiling/
  selector/
  baselines/
  experiments/
  storage/
  analysis/
  cli/
  common/
```

## Module Map

| Package | Responsibility | Primary Inputs | Primary Outputs |
| --- | --- | --- | --- |
| `kernels/` | Register kernels and validate kernel metadata | `KernelSpec`, kernel configs | Resolved kernel objects |
| `config_space/` | Generate and validate candidate configs | `KernelSpec`, `ProblemShape` | `CandidateConfig` rows |
| `benchmark/` | Correctness checks and runtime measurement | Kernel callable, shapes, configs | `RuntimeMeasurement` rows |
| `signals/` | Collect compile-time and compile-adjacent signals | Kernel, shape, config | `CompileSignalRecord` rows |
| `profiling/` | Collect selective hardware counter data | Profile requests, counter sets | `ProfileMeasurement` rows |
| `selector/` | Prune, rank, and choose configs | Candidates, signals, budget, profile data | `SelectionDecision` |
| `baselines/` | Run default and naive strategy comparisons | Candidates, measurements, budget | Baseline decision outputs |
| `experiments/` | Drive end-to-end runs and phase transitions | `ExperimentSpec` | Complete run state |
| `storage/` | Persist manifests, tables, and derived artifacts | Typed records | Files in `artifacts/` |
| `analysis/` | Generate run-level and study-level reports | Persisted artifacts, `StudySpec` | `summary.json`, cross-run summaries, plots, tables |
| `cli/` | Command surface for running the system | CLI args, YAML configs | Invocations of internal modules |
| `common/` | Shared types, IDs, logging, provenance, and utilities | Internal use | Shared contracts |

## Control Flow

1. The CLI resolves a kernel, experiment, or study config and dispatches to the corresponding module.
2. The orchestrator resolves one kernel and its shapes, then asks `config_space/` for candidate configurations.
3. `signals/` collects cheap signals over the broad candidate set.
4. `benchmark/` measures runtime only through orchestrator-issued requests; selector and baseline modules do not invoke it directly.
5. `profiling/` collects hardware counters only through orchestrator-issued requests on the calibration subset and within the profile budget.
6. `selector/` prunes and ranks candidates under the experiment budget.
7. `baselines/` run comparator strategies over the same candidate pool and the same orchestrator-mediated measurement interface.
8. `storage/` writes all run artifacts and the manifest.
9. `analysis/` consumes stored artifacts to produce run-level summaries and derived outputs.
10. `analysis/comparison` optionally consumes multiple finished runs to produce study-level comparisons.

## Artifact Flow

```text
ExperimentSpec YAML
  -> candidate config table
  -> compile signal table
  -> runtime measurement table
  -> profile measurement table
  -> selection decision table
  -> run-level summary and derived outputs
  -> study-level comparison outputs
```

Each run produces a complete artifact directory rooted at `artifacts/<experiment_id>/<run_id>/`. Study-level comparisons produce a separate directory rooted at `artifacts/studies/<study_id>/<run_id>/`.

## External Dependencies

- Python runtime
- Triton for kernel authoring and execution
- PyTorch for tensor allocation and host-side integration
- NVIDIA CUDA runtime and driver
- Nsight Compute CLI for hardware counter collection
- YAML, JSON, CSV, and Parquet tooling
- plotting support for summary figures

## Stable Contracts

- Experiments are single-kernel in v1.
- The end-to-end workflow above is fixed for v1.
- Artifact writing happens through `storage/`, not ad hoc file writes scattered across modules.
- All selector and baseline comparisons must use the same candidate pool and the same budget semantics.
- Selection-time runtime and profile measurements are brokered centrally by the orchestrator.
- Any exhaustive or oracle-style measurement used only for analysis must be explicit and marked as non-comparable in downstream reporting.

## Exploratory Areas

- The exact pruning heuristics.
- The exact ranking logic.
- The exact counter sets used during calibration.
- The exact opportunity-mining logic.
- Whether learned ranking is worth adding after the heuristic path is well understood.
