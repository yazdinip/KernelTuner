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

These must be resolved before or during early implementation:

1. Which Linux CUDA host will be the authoritative benchmark machine?
2. Which GPU model will be used for the primary study?
3. Which Triton and PyTorch versions will be pinned for the initial environment bootstrap?

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
