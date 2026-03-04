# Project Charter

## Purpose

`KernelTuner` exists to test whether bottleneck-aware guidance can improve Triton kernel configuration search without attempting to solve full autotuning or redesign Triton's compiler.

The project is intentionally substantial. It should produce an implemented system, a reproducible experiment pipeline, and a defensible empirical result even if the selector does not outperform naive baselines.

## Problem Statement

Triton makes GPU kernel development more accessible, but kernel performance still depends heavily on configuration decisions such as tile sizes, `num_warps`, and `num_stages`. Poor choices can waste search budget, reduce performance, and obscure which hardware bottlenecks actually matter for a workload.

Default settings and naive search are easy to apply, but they may spend budget on obviously weak candidates or ignore signals that could guide search more intelligently.

## Core Research Question

Can a bottleneck-aware configuration selector use resource signals and limited profiling data to guide Triton kernel configuration search better than default settings or equally budgeted naive tuning?

## Primary Hypothesis

Cheap signals such as register count, shared-memory usage, occupancy estimates, and a limited set of profiling counters can identify many poor configurations before exhaustive measurement.

## Why This Project Is Worth Doing

- It is implementation-heavy rather than purely observational.
- It is scoped enough for an academic term but still technically substantial.
- It allows both positive and negative results to be informative.
- It creates reusable infrastructure for benchmarking and analyzing Triton kernels.

## v1 Goals

1. Build a reproducible pipeline for Triton kernel configuration experiments on one NVIDIA GPU.
2. Implement a bottleneck-aware selector that can prune and rank candidate configurations.
3. Compare that selector against default and naive search baselines under matched budgets.
4. Produce analysis that explains both wins and failures.

## Non-Goals

- Redesigning Triton's compiler or scheduling internals.
- Claiming broad superiority over vendor libraries.
- Supporting multiple GPUs, heterogeneous clusters, or distributed execution in v1.
- Building a stable public framework with long-term backward compatibility guarantees.
- Solving autotuning for all Triton kernels.

## In Scope

- One Linux CUDA host with one NVIDIA GPU.
- One required primary kernel family: GEMM.
- Optional secondary kernels after the primary workflow is stable.
- Candidate generation over Triton configuration parameters.
- Compile-time signal collection.
- Selective hardware profiling on a calibration subset.
- Heuristic pruning and heuristic ranking in v1.
- Optional learned ranking as an extension, not a dependency.
- File-based experiment artifacts and offline analysis.

## Out of Scope

- Native Windows execution as a supported benchmark platform.
- Automatic multi-GPU scaling.
- Fully online autotuning inside a production training or inference service.
- Large-scale benchmarking across many machines or GPU architectures.
- Kernel source generation beyond what is needed for the selected Triton kernels.

## Success Criteria

Any of the following counts as a successful project outcome:

1. The selector finds faster configurations than naive baselines under the same search budget.
2. The selector reaches comparable performance with less search effort.
3. The experiment pipeline reveals that the chosen signals do not generalize or predict performance well, and that negative result is supported by reproducible evidence.

## Failure-Is-Still-Useful Rule

The project is not defined as successful only if the selector wins. It is also successful if:

- the implementation is complete,
- the evaluation is fair and reproducible,
- the negative result clearly explains the limitations of the proposed approach.

This rule is important because the point of the project is to try something ambitious enough to fail for real reasons, not to guarantee a positive outcome by narrowing the question until it becomes trivial.

## Fixed v1 Decisions

- Primary implementation language is Python.
- Runtime environment is a Linux CUDA host with one NVIDIA GPU.
- GEMM is mandatory for v1.
- Heuristic pruning and ranking are mandatory for v1.
- Learned ranking is optional.
- Artifacts are stored on disk using YAML, JSON, and Parquet.
- Comparisons must use matched or explicitly normalized search budgets.

## Exploratory Areas

- Which resource signals will actually be predictive.
- Which profiling counters will be most informative.
- The exact selector logic beyond the v1 pruning and ranking contract.
- Whether a simple learned ranker helps beyond heuristics.
- How well the approach transfers to secondary kernels.

## Deliverables

1. Documentation-first system design.
2. Experiment harness and analysis pipeline.
3. Bottleneck-aware selector implementation.
4. Baseline comparisons and final empirical report.

## Decision Rule for Scope Pressure

If time or tooling becomes limiting, depth on the primary GEMM case study wins over breadth. Secondary kernels, learned ranking, and richer search spaces may be cut before compromising the primary pipeline.
