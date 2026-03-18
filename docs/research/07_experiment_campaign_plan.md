# Experiment Campaign Plan

Purpose: define the sequence of research rounds and the evidence gates that control movement from one round to the next.
Status: Backbone
Update Rule: update when the experiment sequence or round exit gates change materially.
Feeds Paper Sections: Method, Experimental Setup, Results
Depends On: [../06_implementation_roadmap.md](../06_implementation_roadmap.md), [../07_test_strategy.md](../07_test_strategy.md), [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [08_evidence_registry.md](08_evidence_registry.md)

## Campaign Principles

- Run the smallest study that can answer the current question.
- Do not revise the selector before the previous round has produced interpretable evidence.
- Keep reportable and diagnostic studies separate.
- Promote ideas only after they survive repeated evidence.

## Repeatability And Robustness Modes

Two execution modes should be used across the campaign:

- **Repeatability mode:** three repeated runs with the same seed on the same host allocation policy
- **Robustness mode:** the same study under seeds `7`, `19`, and `43`

Repeatability isolates measurement noise. Robustness isolates search-order sensitivity.

## Research Rounds

| Round | Purpose | Entry Criteria | Required Runs | Expected Artifacts | Exit Gate | Paper Claim Unlocked |
| --- | --- | --- | --- | --- | --- | --- |
| `R0` Measurement validity | prove that the measurement and profiler surfaces are stable enough for research claims | end-to-end pipeline exists on the pinned host | repeated `gemm_smoke`, `gemm_reportable`, and counter-availability validation; LayerNorm smoke for profiling path sanity | stability report, counter-availability report, updated evidence registry | runtime noise is characterized and Tier 1 counter sets are either accepted or explicitly downgraded | "the study is methodologically trustworthy" |
| `R1` Cheap-signal baseline mapping | determine what cheap signals can and cannot do before profiling | `R0` passed | `gemm_aligned_reportable` and `gemm_reportable` in repeatability and robustness modes with `prune_only` and `prune_rank` | held-out speedup tables, workload-class breakdown, signal-runtime correlation, first opportunity entries | at least one workload class is identified where cheap-signal ranking is weak, unstable, or clearly workload-specific | `H1` and `H3` become answerable |
| `R2` Limited-profile tuning | test whether matched-budget profiling improves selection quality and where | `R1` produced at least one concrete failure mode or uncertainty | profiled GEMM and LayerNorm reportable studies using `compute_lite` and `memory_lite` | counter-availability report, profiled-selector comparison, cross-kernel comparison plots | profiling value is characterized for both kernel families and the Tier 1 sets remain acceptable | `H2` becomes answerable |
| `R3` Opportunity-guided refinement | test one revised selector batch motivated by real evidence | `R2` produced at least one stable opportunity entry | revised-selector runs on reportable GEMM and LayerNorm under unchanged budget | revised-vs-current comparison, opportunity catalog update, case-study plots | revised selector either demonstrates a real gain or produces a clear negative result | `H4` becomes answerable |
| `R4` Transfer and limits | consolidate the strongest and weakest cases and document the study boundaries | `R3` complete | selected diagnostic follow-ups, confirmation reruns, final study comparisons | final hypothesis status, final figure bundle, limitations write-up | all paper figures and tables have artifact sources and no unresolved gating confound remains | final paper assembly |

## Current Run Matrix

### Reportable studies

- `configs/experiments/gemm_reportable.yaml`
- `configs/experiments/gemm_aligned_reportable.yaml`
- `configs/experiments/layernorm_reportable.yaml`

### Development studies

- `configs/experiments/gemm_development.yaml`
- `configs/experiments/layernorm_development.yaml`

### Smoke studies

- `configs/experiments/gemm_smoke.yaml`
- `configs/experiments/layernorm_smoke.yaml`

### Cross-run study

- `configs/studies/validation_phase.yaml`

## Required Artifacts Per Round

| Round | Minimum Artifacts |
| --- | --- |
| `R0` | runtime repeatability data, counter availability, environment provenance summary |
| `R1` | held-out pairwise comparisons, signal-runtime correlations, first workload-class analysis |
| `R2` | matched-budget profiled comparisons, counter-set acceptance results, cross-kernel comparison |
| `R3` | opportunity catalog, revised-selector comparison, selected failure case studies |
| `R4` | final cross-run summary, final figure/table source map, final hypothesis status table |

## Exit-Gate Discipline

No round should be declared complete unless its exit gate is reflected in:

- the evidence registry,
- the opportunity log if applicable,
- and the paper outline/figure plan where the round unlocks a new figure or claim.

If a round fails its exit gate, the next action should be recorded as either:

- more measurement validation,
- narrower workload focus,
- or explicit de-scoping.
