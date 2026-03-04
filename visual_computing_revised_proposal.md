# Bottleneck-Aware Configuration Selection for Triton Kernels

Giovanni Galea Curmi  
ganni@cs.toronto.edu  
Pedram Yazdinia  
yazdinip@cs.toronto.edu

## Overview

Triton makes it easier to write high-performance GPU kernels than hand-written CUDA for many workloads, especially tiled and fused kernels. However, performance still depends heavily on configuration choices such as tile sizes, `num_warps`, and `num_stages`. Poor choices can increase register pressure, reduce occupancy, or expose memory and synchronization bottlenecks, even when the kernel is functionally correct.

This project studies whether Triton kernel configuration can be improved through a bottleneck-aware selector. The goal is not to redesign Triton's compiler or fully solve autotuning. Instead, we aim to build and evaluate a substantive system that uses cheap resource signals together with limited profiling feedback to steer configuration search more intelligently than default settings or naive tuning.

An important part of the project is exploratory. At this stage, we do not know which signals, heuristics, or model structure will be most effective. That uncertainty is part of the research question rather than a flaw in the project. A useful outcome would be either:

1. an implemented selector that improves configuration quality or tuning efficiency, or
2. a clear empirical result showing that the proposed signals are not sufficient, along with analysis of why they fail.

The project is therefore intended to be substantial even if the final answer is negative.

## Core Research Question

Can a bottleneck-aware configuration selector use resource signals and limited profiling data to guide Triton kernel configuration search better than default settings or equally budgeted naive tuning?

## Hypothesis

We hypothesize that many poor Triton configurations can be identified without fully benchmarking every candidate, using signals such as register count, shared-memory usage, occupancy estimates, and a small number of hardware counters collected on a calibration subset.

We further hypothesize that a selector informed by likely bottlenecks will either:

1. find faster configurations under the same tuning budget, or
2. reach comparable performance with less search effort.

If this does not hold, the project will still produce a useful negative result about the limits of lightweight bottleneck-aware tuning in Triton.

## Scope

The scope is intentionally bounded, but not so narrow that the project becomes trivial.

1. **Hardware platform:** one NVIDIA GPU.
2. **Primary target:** one major Triton kernel family, most likely GEMM.
3. **Additional validation:** one or more secondary kernels if time permits, such as reduction, layer normalization, softmax, or attention-related kernels.
4. **Configuration space:** Triton scheduling parameters such as tile sizes, `num_warps`, `num_stages`, and related launch or blocking choices.

We do not aim to outperform highly optimized vendor libraries across the board. The goal is to test whether bottleneck-aware guidance can improve how Triton configurations are chosen within a realistic project-sized tuning setup.

## Methodology

The project will proceed in stages.

### 1. Build a benchmarking and analysis harness

For each kernel family we study, we will implement:

- Correctness checks
- A controlled runtime benchmarking setup
- A candidate configuration generator
- Logging for runtime, compile-time metadata, and selected profiling information

This harness is a core contribution because it provides the foundation for comparing configuration strategies reproducibly.

### 2. Collect cheap signals over a broad candidate set

For each candidate configuration, we will collect signals that are relatively cheap to obtain, such as:

- Runtime from controlled benchmarking
- Register usage
- Shared-memory usage
- Occupancy-related estimates
- Other compile-time or compile-adjacent metadata that Triton or the backend exposes

This stage gives us a broad view of the configuration landscape and helps identify clearly poor candidates.

### 3. Calibrate with selective profiling

For only a subset of configurations and input shapes, we will collect more detailed hardware profiling data, for example counters related to memory stalls, achieved occupancy, or execution efficiency.

The exact bottleneck signals used in the final selector will be determined after this calibration step. This is deliberate: part of the project is to discover which signals are most informative in practice on the chosen workload.

### 4. Implement a bottleneck-aware selector

Rather than committing to a single mechanism too early, we will build the selector in increasing levels of sophistication depending on what the data supports:

1. **Pruning heuristic:** reject obviously bad configurations using resource and occupancy signals.
2. **Ranking heuristic:** prioritize surviving configurations based on suspected bottlenecks.
3. **Optional learned component:** if the data is sufficient, use a simple predictive model to score or rank candidates.

This staged design keeps the project flexible while still ensuring that a substantial system is implemented.

### 5. Compare against baselines under matched budgets

We will compare the selector against:

1. **Default or simple Triton configuration:** a fixed configuration or minimal hand-written heuristic.
2. **Naive search:** random search, grid search, or another simple strategy over the same configuration space.
3. **Optional small-space oracle:** for restricted subsets, full search may be used offline to understand how close each strategy gets to the best available configuration.

The key principle is that comparisons should be made under comparable measurement budgets wherever possible.

## Evaluation

Evaluation will focus on both configuration quality and tuning efficiency.

Primary outcomes:

- End-to-end kernel runtime of the chosen configuration
- Performance achieved within a fixed search budget
- Search cost required to reach a strong configuration

Secondary outcomes:

- Whether selected configurations correlate with improved hardware behavior
- Whether the selector transfers across multiple input shapes
- Whether any learned or hand-crafted bottleneck signal remains useful beyond the calibration subset

Success for the project does not require a universal improvement. Strong outcomes include:

1. the selector consistently choosing better configurations than naive baselines,
2. the selector reducing search cost while maintaining similar performance, or
3. a clear negative result showing that the proposed signals do not generalize well.

## Expected Contributions

This project is expected to produce:

1. A reproducible benchmark and analysis setup for Triton kernel configuration experiments.
2. An implemented bottleneck-aware selector for choosing or ranking Triton configurations.
3. An empirical comparison between bottleneck-aware selection and simple tuning baselines.
4. An analysis of which signals appear useful, misleading, or insufficient when tuning Triton kernels.

## Feasibility and Timeline

The project is feasible in 8 weeks because it can succeed at multiple levels. A useful outcome does not depend on every ambitious component landing.

1. **Weeks 1-2:** implement the initial kernel or kernels, correctness checks, benchmarking harness, and candidate configuration generation.
2. **Weeks 3-4:** gather runtime and cheap resource signals across a broad candidate set; establish baseline behavior.
3. **Weeks 5-6:** run selective profiling, identify promising bottleneck signals, and implement pruning and ranking strategies.
4. **Weeks 7-8:** evaluate on held-out shapes and additional kernels if possible; analyze successes, failures, and limitations; prepare the report and presentation.

The project can scale based on what we learn:

- If the selector works well early, we can validate on more kernels or richer configuration spaces.
- If profiling is more difficult than expected, we can still complete a strong study using cheaper signals plus a smaller calibration subset.
- If secondary kernels add too much overhead, we will prioritize depth on the main kernel family rather than spreading the work too thin.

## Risk Management

The main risks are:

1. **Profiling overhead:** detailed counter collection may be slow or awkward to automate.  
   Mitigation: restrict detailed profiling to a calibration subset and use cheaper signals elsewhere.

2. **Weak signal quality:** the selected resource or bottleneck signals may not predict performance well.  
   Mitigation: treat this as part of the research outcome and compare multiple heuristic levels rather than relying on a single fixed rule from the start.

3. **Implementation overhead across multiple kernels:** extending to several kernel families may reduce time available for analysis.  
   Mitigation: prioritize one strong primary case study and add secondary kernels only once the main pipeline is stable.

4. **Search-space size:** the configuration space may become too large for systematic evaluation.  
   Mitigation: begin with a manageable space, then expand only if the harness and selector are working reliably.

## Summary

This project aims to build a meaningful bottleneck-aware tuning system for Triton kernels, not merely to profile kernels or report benchmark numbers. The project is intentionally exploratory: we want to test whether lightweight signals and limited profiling can guide configuration search in a useful way, and we consider both positive and negative results to be valuable. This makes the project ambitious enough to be substantial, while still scoped enough to complete in one academic term.
