# Implementation Roadmap

## Purpose

This document translates the proposal into a concrete implementation sequence for `KernelTuner` v1.

## Roadmap Principles

- Build the thinnest complete vertical slice first.
- Prioritize correctness, observability, and artifact quality over optimization.
- Finish the primary GEMM path before adding breadth.
- Cut optional work explicitly rather than allowing uncontrolled drift.

## Milestones

### Milestone 0: Project Bootstrap

Goal:

- establish repo structure, shared types, config layout, and basic CLI scaffolding

Deliverables:

- `src/kernel_tuner/` package skeleton
- config directory skeleton
- shared type definitions matching the data-model doc
- manifest writer and artifact-path utilities

Gate to exit:

- package layout exists
- typed config loading works
- a no-op experiment can write a valid manifest

### Milestone 1: Primary Kernel and Candidate Pipeline

Goal:

- make one kernel family executable end to end through config generation and correctness checking

Deliverables:

- GEMM kernel registration
- shape schema and canonical shape IDs
- candidate configuration generation with deterministic config IDs
- reference implementation and correctness validation path

Gate to exit:

- GEMM candidates can be generated reproducibly
- invalid configs are rejected with explicit reasons
- correctness checks run for at least one canonical shape

### Milestone 2: Measurement and Signal Pipeline

Goal:

- collect cheap signals and runtime data for the broad candidate set

Deliverables:

- benchmark harness with warmup and timed-run semantics
- compile-time signal collection
- runtime and compile artifact writing

Gate to exit:

- `candidates.parquet`, `compile_signals.parquet`, and `runtime_measurements.parquet` can be produced for one experiment
- failures are persisted explicitly
- benchmark statistics are reproducible enough for comparison work

### Milestone 3: Profiling and Selector

Goal:

- calibrate on a subset and implement bottleneck-aware pruning and ranking

Deliverables:

- selective profiling adapter
- named counter set support
- heuristic pruning policy
- heuristic ranking policy
- selection decision artifact writing

Gate to exit:

- profile measurements can be collected for a calibration subset
- selector consumes candidates, signals, and optional profiles through one stable interface
- baseline and selector decisions are both persisted

### Milestone 4: Comparison, Reporting, and Held-Out Evaluation

Goal:

- complete the comparison workflow and generate interpretable experiment outputs

Deliverables:

- matched-budget baseline strategies
- held-out evaluation path
- summary generation and analysis outputs
- negative-result reporting support

Gate to exit:

- one complete experiment run produces all required artifacts
- summary output compares selector and baselines under matched budgets
- held-out results are separated from calibration data

### Milestone 5: Extensions If Time Allows

Candidate extensions:

- secondary kernel family
- richer configuration space
- learned ranking component
- small-space oracle for deeper analysis

These are optional. None of them should delay Milestones 0 through 4.

## Dependency Graph

```text
shared types + config loading
    -> kernel registry
    -> config space generation
    -> result store

kernel registry + config space
    -> correctness harness
    -> compile signal collection
    -> benchmark harness

benchmark + signals + result store
    -> profiling adapter
    -> selector engine
    -> baseline strategies

selector + baselines + result store
    -> experiment orchestrator
    -> analysis and reporting
```

## Drop-If-Needed Rules

Cut in this order if schedule pressure increases:

1. learned ranker
2. secondary kernels
3. richer counter sets
4. richer configuration space
5. small-space oracle

Do not cut these items without changing project scope:

- GEMM primary path
- benchmark harness
- signal collection
- heuristic selector
- matched-budget baselines
- artifact persistence
- held-out evaluation

## Implementation Order by Module

1. `common/`
2. `storage/`
3. `cli/`
4. `kernels/`
5. `config_space/`
6. `benchmark/`
7. `signals/`
8. `profiling/`
9. `selector/`
10. `baselines/`
11. `experiments/`
12. `analysis/`

## Acceptance Criteria

The roadmap is considered executed when:

- the primary GEMM workflow runs end to end,
- all required artifacts are written,
- selector and baselines can be compared fairly,
- held-out evaluation is separate and explicit,
- the final report can describe either a positive or negative result.
