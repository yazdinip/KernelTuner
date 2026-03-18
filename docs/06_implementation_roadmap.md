# Implementation Roadmap

## Purpose

This document translates the proposal into a concrete implementation sequence for `KernelTuner` v1 and records how far the implementation has progressed.

## Roadmap Principles

- Build the thinnest complete vertical slice first.
- Prioritize correctness, observability, and artifact quality over optimization.
- Finish the primary GEMM path before adding breadth.
- Cut optional work explicitly rather than allowing uncontrolled drift.
- Once the foundation exists, shift effort from feature growth to research validation.

## Current Status Snapshot

As of the current implementation state:

- Milestones 0 through 4 are substantially implemented.
- The repo has a working `ktune` CLI, GPU execution path, artifact store, selector and baseline ladder, and run-level reporting.
- Cross-run comparison, counter-availability reporting, opportunity mining, and LayerNorm support are now part of the codebase.
- The active project phase is no longer basic implementation. It is research validation and refinement, as described in [`docs/research/07_experiment_campaign_plan.md`](research/07_experiment_campaign_plan.md).

This roadmap therefore has two jobs:

1. preserve the logic of how the implementation was built,
2. make clear that the remaining work is mostly about evidence, stability, and scientifically justified tuner refinement.

## Milestones

### Milestone 0: Project Bootstrap

Goal:

- establish repo structure, shared types, config layout, and basic CLI scaffolding

Deliverables:

- `src/kernel_tuner/` package skeleton
- config directory skeleton
- shared type definitions matching the data-model doc
- manifest writer and artifact-path utilities
- environment provenance capture and host qualification checks
- Slurm dry-run workflow validation for the designated cluster path

Status:

- implemented

Gate to exit:

- package layout exists
- typed config loading works
- a no-op experiment can write a valid manifest with environment provenance

### Milestone 1: Primary Kernel and Candidate Pipeline

Goal:

- make one kernel family executable end to end through config generation and correctness checking

Deliverables:

- GEMM kernel registration
- shape schema and canonical shape IDs
- candidate configuration generation with deterministic config IDs
- reference implementation and correctness validation path

Status:

- implemented, then extended with LayerNorm as a validation kernel family

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
- explicit timing-backend recording and raw-sample references when enabled

Status:

- implemented

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
- profiler metadata capture including tool version and replay settings

Status:

- implemented

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
- comparability and reportability flags in summaries
- uncertainty estimates for aggregate held-out results

Status:

- implemented

Gate to exit:

- one complete experiment run produces all required artifacts
- summary output compares selector and baselines under matched budgets
- held-out results are separated from calibration data

### Milestone 5: Research Validation and Opportunity-Guided Refinement

Goal:

- turn the implemented system into a defensible research instrument and use evidence to justify tuner revisions

Deliverables:

- repeated reportable runs on the pinned baseline
- study-level comparison via `StudySpec` and `ktune compare-runs`
- counter-availability reporting for named counter sets
- workload-class-aware comparisons across GEMM and LayerNorm
- opportunity logs and heuristic-candidate proposals
- one evidence-backed selector revision batch evaluated under unchanged budgets

Status:

- active

Gate to exit:

- repeated runs are stable enough for matched-budget claims
- cross-run comparisons can mark hypotheses as supported, unsupported, or inconclusive
- at least one selector revision is justified by observed failure modes rather than ad hoc tuning

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
    -> study comparison
```

## Drop-If-Needed Rules

Cut in this order if schedule pressure increases:

1. learned ranker
2. additional kernel families beyond GEMM and LayerNorm
3. richer counter sets beyond the accepted reportable tiers
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
- research evidence tracking

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

The implementation roadmap is considered executed when:

- the primary GEMM workflow runs end to end,
- all required artifacts are written,
- selector and baselines can be compared fairly,
- held-out evaluation is separate and explicit,
- run-level and study-level reporting are in place,
- and the remaining work is research validation rather than missing core infrastructure.
