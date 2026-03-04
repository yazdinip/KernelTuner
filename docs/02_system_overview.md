# System Overview

## Purpose

This document defines the high-level architecture for the `KernelTuner` v1 research prototype. It is the authoritative overview of module boundaries, end-to-end workflow, data flow, and external dependencies.

## System Goal

The system takes a kernel specification and a set of experiment settings, generates candidate Triton configurations, gathers cheap and selective expensive signals, applies a bottleneck-aware selector and baseline strategies under matched budgets, and writes reproducible artifacts for analysis.

## End-to-End Workflow

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
| kernels     | --> | config_space     | --> | signal_collection|
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
                       +---------------+
                       | analysis      |
                       +---------------+
```

## Planned Package Layout

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
| `config_space/` | Generate and validate candidate configs | `KernelSpec`, `ProblemShape`, budget hints | `CandidateConfig` rows |
| `benchmark/` | Correctness checks and runtime measurement | Kernel callable, shapes, configs | `RuntimeMeasurement` rows |
| `signals/` | Collect compile-time and compile-adjacent signals | Kernel, shape, config | `CompileSignalRecord` rows |
| `profiling/` | Collect selective hardware counter data | Profile requests, counter sets | `ProfileMeasurement` rows |
| `selector/` | Prune, rank, and choose configs | Candidates, signals, budget, profile data | `SelectionDecision` |
| `baselines/` | Run default and naive strategy comparisons | Candidates, measurements, budget | Baseline decision outputs |
| `experiments/` | Drive end-to-end runs and phase transitions | `ExperimentSpec` | Complete run state |
| `storage/` | Persist manifests, tables, and summaries | Typed records | Files in `artifacts/` |
| `analysis/` | Aggregate results and produce reports | Persisted artifacts | `summary.json`, plots, tables |
| `cli/` | Command surface for running the system | CLI args, YAML configs | Invocations of internal modules |
| `common/` | Shared types, IDs, logging, and utilities | Internal use | Shared contracts |

## Control Flow

1. The CLI resolves an experiment config and hands it to the orchestrator.
2. The orchestrator resolves kernels and shapes, then asks `config_space/` for candidate configurations.
3. `signals/` collects cheap signals over the broad candidate set.
4. `benchmark/` measures candidate runtime according to the benchmark protocol.
5. `profiling/` collects hardware counters only on the calibration subset within the profile budget.
6. `selector/` calibrates if needed, then prunes and ranks candidates under the experiment budget.
7. `baselines/` run comparator strategies over the same candidate pool.
8. `storage/` writes all run artifacts and the manifest.
9. `analysis/` consumes the stored artifacts to produce summaries, tables, and plots.

## Artifact Flow

```text
ExperimentSpec YAML
  -> candidate config table
  -> compile signal table
  -> runtime measurement table
  -> profile measurement table
  -> selection decision table
  -> summary JSON and analysis outputs
```

The storage layer is append-by-run, not append-by-record. Each run produces a complete artifact directory rooted at `artifacts/<experiment_id>/<run_id>/`.

## External Dependencies

- Python runtime
- Triton for kernel authoring and execution
- PyTorch for tensor allocation and host-side integration
- NVIDIA CUDA runtime and driver
- Nsight Compute CLI for hardware counter collection
- YAML parser, JSON support, and Parquet tooling
- Numeric and dataframe libraries for analysis

## Stable Contracts

- The package layout in this document is fixed for v1.
- The end-to-end workflow above is fixed for v1.
- Artifact writing happens through `storage/`, not ad hoc file writes scattered across modules.
- All selector and baseline comparisons must use the same candidate pool and the same budget semantics.

## Exploratory Areas

- The exact pruning heuristics.
- The exact ranking logic.
- The exact counter set used during calibration.
- Whether learned ranking is worth adding after the heuristic path is working.
