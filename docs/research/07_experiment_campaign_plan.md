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

## Current Stage

As of March 27, 2026:

- the full `gpunode3` same-class A6000 requalification block has completed
- the broad `validation_rounds_g3_requal` campaign and both narrow follow-up studies (`h13_confirmation_g3`, `h2_followup_g3`) have completed
- the post-follow-up LayerNorm diagnostic profiling passes have completed
- the corrected `h2_followup_g3_baselinefix` rerun has completed
- the frontier-aware `h4_retry_g3` rerun has completed
- the full Phase 2 v2 deepening chain has completed:
  - `gemm_v2_baseline_mapping`
  - `gemm_v2_selector_ablation`
  - `layernorm_v2_regime_studies`
  - `gemm_v2_aligned_reference`
- `R0` is operationally satisfied for continued execution
- `R1` is materially stronger than before
- `R2` has repeated non-support on a corrected LayerNorm baseline
- `R3` now has mixed evidence:
  - the narrower representative GEMM retry supported the frontier-aware `v3_h4_targeted` selector
  - the expanded v2 GEMM space did not preserve that win

Current implication:

- the controlled Phase 2 deepening pass is complete
- the current work should focus on analysis, documentation, and a bounded decision about whether one additional corrective execution pass is scientifically justified
- any further execution should now be narrow and mechanism-driven, not another broad search-space expansion by default

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

## Current Round Status

| Round | Current State | Notes |
| --- | --- | --- |
| `R0` | Operationally complete | broad and narrow live campaigns, profiler validation, reportability checks, and chained study generation have all been exercised on both the original and same-class A6000 confirmation paths |
| `R1` | Strong and expanded-space reinforced | original validation, `gpunode3` confirmation, and the completed `gemm_v2_baseline_mapping` study all support the view that compile signals prune but do not rank representative GEMM well enough |
| `R2` | Regime-split negative or weak | the corrected pooled rerun remained unsupported; the Phase 2 split studies show only a marginal small-batch profiling gain and an outright large-batch regression under `memory_activity_lite` |
| `R3` | Mixed after expansion | the narrower representative GEMM retry supported `H4`, but the expanded v2 GEMM baseline mapping and selector ablation show that the current frontier-aware revision does not generalize cleanly to the larger space |
| `R4` | Active analysis and bounded corrective planning | the main next tasks are to preserve the Phase 2 evidence, align the docs and figure plan with it, and decide whether one narrow corrective execution pass is justified |

## Current Run Matrix

### Reportable studies

- `configs/experiments/gemm_reportable.yaml`
- `configs/experiments/gemm_aligned_reportable.yaml`
- `configs/experiments/layernorm_reportable.yaml`

### Same-class A6000 requalification studies

- `configs/experiments/gemm_reportable_g3_requal.yaml`
- `configs/experiments/gemm_aligned_reportable_g3_requal.yaml`
- `configs/experiments/layernorm_reportable_g3_requal.yaml`

### Corrected follow-up studies

- `configs/experiments/gemm_reportable_g3_h2followup.yaml`
- `configs/experiments/layernorm_reportable_g3_baselinefix.yaml`
- `configs/experiments/gemm_reportable_g3_h4parent.yaml`
- `configs/experiments/gemm_reportable_g3_v3h4.yaml`
- `configs/experiments/layernorm_diag_regimes_g3.yaml`

### Phase 2 v2 studies

- `configs/experiments/gemm_v2_reportable.yaml`
- `configs/experiments/gemm_v2_aligned_reportable.yaml`
- `configs/experiments/layernorm_v2_small_reportable.yaml`
- `configs/experiments/layernorm_v2_large_reportable.yaml`

### Development studies

- `configs/experiments/gemm_development.yaml`
- `configs/experiments/layernorm_development.yaml`

### Smoke studies

- `configs/experiments/gemm_smoke.yaml`
- `configs/experiments/layernorm_smoke.yaml`

### Cross-run study

- `configs/studies/validation_phase.yaml`
- `configs/studies/validation_phase_g3_requal.yaml`
- `configs/studies/h13_confirmation_g3.yaml`
- `configs/studies/h2_followup_g3.yaml`
- `configs/studies/h2_followup_g3_baselinefix.yaml`
- `configs/studies/h4_retry_g3.yaml`
- `configs/studies/gemm_v2_baseline_mapping.yaml`
- `configs/studies/gemm_v2_selector_ablation.yaml`
- `configs/studies/layernorm_v2_small_regime.yaml`
- `configs/studies/layernorm_v2_large_regime.yaml`
- `configs/studies/gemm_v2_aligned_reference.yaml`

### Current campaign entrypoint

- `configs/campaigns/validation_rounds.yaml`
- `configs/campaigns/validation_rounds_g3_requal.yaml`
- `configs/campaigns/h13_confirmation_g3.yaml`
- `configs/campaigns/h2_followup_g3.yaml`
- `configs/campaigns/h2_followup_g3_baselinefix.yaml`
- `configs/campaigns/h4_retry_g3.yaml`
- `configs/campaigns/gemm_v2_baseline_mapping.yaml`
- `configs/campaigns/gemm_v2_selector_ablation.yaml`
- `configs/campaigns/layernorm_v2_regime_studies.yaml`
- `configs/campaigns/gemm_v2_aligned_reference.yaml`

## Required Artifacts Per Round

| Round | Minimum Artifacts |
| --- | --- |
| `R0` | runtime repeatability data, counter availability, environment provenance summary |
| `R1` | held-out pairwise comparisons, signal-runtime correlations, first workload-class analysis |
| `R2` | matched-budget profiled comparisons, counter-set acceptance results, cross-kernel comparison |
| `R3` | opportunity catalog, revised-selector comparison, selected failure case studies |
| `R4` | final cross-run summary, final figure/table source map, final hypothesis status table |

## Immediate Analysis Queue

The immediate queue is no longer a new broad execution pass. It is a Phase 2 analysis and decision pass.

### Step 1: freeze the Phase 2 evidence bundle

- keep `artifacts/analysis/phase2_20260327/` as the canonical reusable summary of the completed Phase 2 chain
- keep the successful cycle log and status files alongside the bundle
- reference the canonical analysis log:
  - `docs/research/logs/2026-03-27_phase2_execution_analysis.md`

### Step 2: synchronize the living registries

- update the evidence registry with the completed v2 studies
- update the opportunity log with the expanded-space GEMM failure and the regime-split LayerNorm outcome
- update the paper outline and figure plan so the strongest sources point to the completed v2 studies, not only the earlier narrow-space follow-ups

### Step 3: decide whether another execution phase is justified

Only two follow-up directions remain well justified:

- one bounded corrective GEMM revision targeting the specific oversized masked-tile overcorrection seen in Phase 2
- one explanatory LayerNorm microstudy if the paper needs a stronger second-kernel mechanism section

Everything broader than those two options should currently be deferred.

## Long-Run Execution Discipline

Long execution should be treated as scientific data collection, not just cluster usage.

Required rules:

- run `validate-study` and `validate-counter-set` before any promotable campaign
- keep exploratory or branch-testing artifacts separate from promotable evidence roots
- do not mix heterogeneous GPU classes in one comparative study
- keep reportable runs inside the qualified `RTX A6000` pool
- update the evidence registry, opportunity log, and a dated log entry after each completed batch that changes interpretation
- archive or reproduce important evidence that currently lives only in expiring scratch storage before using it in final paper claims

## Exit-Gate Discipline

No round should be declared complete unless its exit gate is reflected in:

- the evidence registry,
- the opportunity log if applicable,
- and the paper outline/figure plan where the round unlocks a new figure or claim.

If a round fails its exit gate, the next action should be recorded as either:

- more measurement validation,
- narrower workload focus,
- or explicit de-scoping.
