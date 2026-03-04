# ADR-001: Single Host, Single GPU for v1

- Status: Accepted
- Date: 2026-03-03

## Context

The project is an 8-week research prototype with a strong emphasis on reproducible measurement. Supporting multiple hosts, multiple GPUs, or heterogeneous environments would add orchestration and comparability complexity that does not directly help answer the core research question.

## Decision

v1 will target one Linux CUDA host with one NVIDIA GPU as the authoritative execution environment for benchmarking and profiling.

## Consequences

- Environment setup is simpler and easier to reason about.
- Experiment noise is easier to control.
- Artifact schemas and orchestration do not need distributed execution concepts in v1.
- Claims of generality across hardware platforms will be limited.

## Rejected Alternatives

- Multi-GPU support in v1: rejected because it adds cost without helping the core question.
- Cross-host benchmarking: rejected because it complicates reproducibility and budget fairness.
- Native Windows benchmarking: rejected because Triton and profiling workflows are better supported on Linux.

## Revisit If

- The core pipeline is stable and additional hardware coverage becomes a project goal.
- Results on one GPU appear too workload-specific to support the intended analysis.
