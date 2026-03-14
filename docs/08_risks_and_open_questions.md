# Risks and Open Questions

## Purpose

This document records the main risks and unresolved questions for `KernelTuner` v1 without turning them into hidden implementation ambiguity.

## Technical Risks

### Profiling Overhead

Risk:

- Nsight Compute runs may be slow, fragile, or cumbersome to automate.

Impact:

- profiling budget becomes too expensive
- turnaround time slows enough to block selector iteration

Mitigation:

- restrict detailed profiling to the calibration subset
- use named counter sets rather than ad hoc per-run counter choices
- keep profiling optional for the first vertical slice

### Weak Signal Quality

Risk:

- cheap signals and selected counters may not predict performance well enough to support good ranking.

Impact:

- the selector may fail to beat naive baselines
- pruning may remove useful candidates

Mitigation:

- keep failure analysis explicit
- persist enough data to explain selector mistakes
- structure the selector so heuristics can be swapped without rewriting the pipeline

### Benchmark Noise

Risk:

- runtime variability on the host may swamp small differences between configurations.

Impact:

- unstable rankings
- weak or misleading conclusions

Mitigation:

- run on one controlled host
- use repeated timed runs and robust summary metrics
- record environment metadata in every manifest

### Cluster Heterogeneity

Risk:

- Slurm scheduling may place nominally similar jobs on different hosts or GPU variants, quietly undermining comparability.

Impact:

- benchmark drift that is misattributed to selector quality
- hidden environment confounds in reportable results

Mitigation:

- designate one authoritative host or homogeneous node class
- record Slurm metadata and GPU identity in every run
- mark mixed-environment runs as non-comparable

### Cache Contamination and Toolchain Drift

Risk:

- Triton compile caches, profiler intermediates, or dirty working trees may leak state across runs.

Impact:

- irreproducible compile signals
- confusing benchmark differences between nominally identical experiments

Mitigation:

- isolate cache roots on scratch storage
- record cache locations and git dirty state
- archive the working-tree diff for any non-clean reportable run

### Profiler Perturbation

Risk:

- Nsight Compute replay or instrumentation overhead may materially alter execution behavior relative to plain benchmark runs.

Impact:

- profile-derived conclusions may not align with real benchmark performance
- profiled timings may be mistaken for authoritative latency measurements

Mitigation:

- isolate profiling runs from benchmark runs
- record profiler settings and replay mode
- never treat profiler-collected timings as benchmark-harness replacements

### Search-Space Explosion

Risk:

- the candidate space may become too large to evaluate meaningfully under the available budget.

Impact:

- measurement cost grows faster than insight
- implementation effort shifts into search management rather than research evaluation

Mitigation:

- keep v1 candidate generation bounded
- enforce `SelectionBudget`
- expand the space only after the core path is working

### Scope Creep

Risk:

- adding extra kernels, extra models, or extra infrastructure too early will weaken the main result.

Impact:

- incomplete primary pipeline
- shallow analysis across too many features

Mitigation:

- follow the primary-kernel-first ADR
- use the roadmap cut order strictly

## Scientific Risks

### Negative Result Without Explanation

Risk:

- the selector loses, but the experiment data is too weak to say why.

Mitigation:

- require artifact completeness
- log selector rationale and pruning decisions
- include failure analysis in the reporting contract

### Overclaiming Generality

Risk:

- the project may be tempted to claim more than a single-host, mostly single-kernel study supports.

Mitigation:

- keep scope claims explicit
- separate within-host transfer claims from broader generalization

## Blocking Questions

The initial implementation milestone resolves most of the original blocking questions. The remaining open item is intentionally kept visible.

Resolved for the initial implementation milestone:

1. Authoritative benchmark machine: `gpunode2`
2. Primary-study GPU model: `NVIDIA RTX A6000` (`49140 MiB`)
3. Initial environment pins:
   - Python `3.12.3`
   - CUDA toolkit `12.9` at `/usr/local/cuda-12.9`
   - Nsight Compute `2025.2.1`
   - GCC `13.3.0`
   - `torch==2.10.0`
   - `triton==3.6.0`
   - `PyYAML==6.0.3`
   - `pandas==3.0.1`
   - `pyarrow==23.0.1`
   - `pytest==8.4.2`
4. Reportable Slurm policy: pin reportable runs to `--nodelist=gpunode2` and do not mix `gpunode2` with `gpunode3` within one comparative study

Still open:

1. What clock-control or thermal-control knobs are actually available on `gpunode2`, and should the project use them or remain on a record-only policy?

## Non-Blocking Open Questions

These may remain open while implementation starts:

1. Which exact profiling counter set will be most useful for GEMM?
2. Which secondary kernel family should be attempted after GEMM?
3. Whether a learned ranker is worth adding after heuristic ranking is stable.
4. Whether the small-space oracle is worth implementing for deeper analysis.

## Allowed Ambiguity

The following are intentionally exploratory and do not block v1 implementation:

- exact heuristic thresholds
- exact bottleneck features used after calibration
- exact secondary-kernel validation plan

## Stable Contracts

- Risks must stay visible in documentation rather than being rediscovered informally.
- Blocking and non-blocking questions must remain separated.
- Negative results are acceptable only if accompanied by a strong explanation path.
