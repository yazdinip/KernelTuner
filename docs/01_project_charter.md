# Project Charter

## Purpose

`KernelTuner` exists to test whether bottleneck-aware guidance can improve Triton kernel configuration search without attempting to solve full autotuning or redesign Triton's compiler.

The project should produce three things together:

- a real experiment platform,
- a reproducible measurement and artifact pipeline,
- and a defensible empirical result, even if the selector does not outperform naive baselines.

## Problem Statement

Triton makes GPU kernel development more accessible, but kernel performance still depends heavily on configuration decisions such as tile sizes, `num_warps`, `num_stages`, and kernel-family-specific schedule knobs. Poor choices waste search budget, reduce performance, and make it hard to tell which hardware bottlenecks actually matter.

Default settings and naive search are easy to apply, but they may spend budget on clearly weak candidates or ignore signals that could guide search more intelligently.

## Core Research Question

Can a bottleneck-aware configuration selector use resource signals and limited profiling data to guide Triton kernel configuration search better than default settings or equally budgeted naive tuning?

## Primary Hypothesis

Cheap signals such as register count, shared-memory usage, occupancy estimates, and a limited set of profiling counters can eliminate many poor configurations and sometimes improve matched-budget configuration selection over default and naive baselines.

## Why This Project Is Worth Doing

- It is implementation-heavy rather than purely observational.
- It is scoped enough for an academic term but still technically substantial.
- It allows both positive and negative results to be informative.
- It creates reusable infrastructure for benchmarking and analyzing Triton kernels.
- It can produce a mechanism-level story about why a selector wins, loses, or fails to generalize.

## v1 Goals

1. Build a reproducible pipeline for Triton configuration experiments on one NVIDIA GPU.
2. Implement a bottleneck-aware selector that can prune, rank, and compare candidates under matched budgets.
3. Compare that selector against default and naive search baselines.
4. Produce run-level and study-level analysis that explain both wins and failures.
5. Establish a research backbone that can justify subsequent tuner revisions with explicit evidence.

## Non-Goals

- Redesigning Triton's compiler or scheduling internals.
- Claiming broad superiority over vendor libraries.
- Supporting multiple GPUs, heterogeneous clusters, or distributed execution in v1.
- Building a stable public framework with long-term backward compatibility guarantees.
- Solving autotuning for all Triton kernels.

## In Scope

- One Linux CUDA host with one NVIDIA GPU.
- One required primary kernel family: GEMM.
- One validation kernel family: LayerNorm.
- Candidate generation over Triton configuration parameters.
- Compile-time signal collection.
- Selective hardware profiling on a calibration subset.
- Heuristic pruning and heuristic ranking in v1.
- Opportunity-guided heuristic revision once evidence exists.
- File-based experiment artifacts and offline analysis.
- Cross-run study comparison and research evidence tracking.

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
3. The experiment pipeline reveals that the chosen signals do not generalize or predict performance well, and that negative result is supported by reproducible evidence and mechanism-level analysis.

## Failure-Is-Still-Useful Rule

The project is not defined as successful only if the selector wins. It is also successful if:

- the implementation is complete enough to run fair studies,
- the evaluation is reproducible,
- and the negative result explains the limitations of the proposed approach coherently.

This rule matters because the point of the project is to try something ambitious enough to fail for real reasons, not to guarantee a positive outcome by narrowing the question until it becomes trivial.

## Fixed v1 Decisions

- Primary implementation language is Python.
- Runtime environment is a Linux CUDA host with one NVIDIA GPU.
- GEMM is the primary case study.
- LayerNorm is the validation contrast kernel.
- Heuristic pruning and ranking are mandatory for v1.
- Learned ranking is optional and deferred.
- Artifacts are stored on disk using YAML, JSON, CSV, PNG, and Parquet.
- Comparisons must use matched or explicitly normalized search budgets.

## Exploratory Areas

- Which resource signals are actually predictive.
- Which profiling counters are sufficiently available and informative.
- The exact selector logic beyond the stable v1 pruning and ranking contract.
- Whether an opportunity-guided heuristic revision helps reliably.
- How well the approach transfers from GEMM to LayerNorm.

## Deliverables

1. Stable implementation and protocol docs.
2. Research backbone docs and evidence registries.
3. Experiment harness and analysis pipeline.
4. Bottleneck-aware selector implementation.
5. Baseline comparisons and final empirical report.

## Decision Rule for Scope Pressure

If time or tooling becomes limiting, depth on the primary GEMM case study wins over breadth. Further kernels, learned ranking, richer search spaces, and deeper profiler sets may be cut before compromising the primary comparative story.
