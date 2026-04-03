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

As of March 29, 2026:

- the full `gpunode3` homogeneous-A6000 requalification block has completed
- the broad `validation_rounds_g3_requal` campaign and both narrow follow-up studies (`h13_confirmation_g3`, `h2_followup_g3`) have completed
- the post-follow-up LayerNorm diagnostic profiling passes have completed
- the corrected `h2_followup_g3_baselinefix` rerun has completed
- the frontier-aware `h4_retry_g3` rerun has completed
- the full Phase 2 v2 deepening chain has completed:
  - `gemm_v2_baseline_mapping`
  - `gemm_v2_selector_ablation`
  - `layernorm_v2_regime_studies`
  - `gemm_v2_aligned_reference`
- the bounded Phase 3 corrective implementation pass has completed:
  - transfer-safe selector revisions `v4_transfer_safe_frontier` and `v4_transfer_safe_profiled`
  - the GEMM v3 split-`k` search space
  - the diagnostic-only `compute_schedule_diag` counter set
  - the bounded LayerNorm microstudy surface
- the full bounded Phase 3 execution program has now completed end to end, including confirmation reruns for the main comparative studies
- `R0` is operationally satisfied for continued execution
- `R1` is materially stronger than before
- `R2` has repeated non-support on a corrected LayerNorm baseline
- `R3` now has mixed evidence:
  - the narrower representative GEMM retry supported the frontier-aware `v3_h4_targeted` selector
  - the expanded v2 GEMM space did not preserve that win
- `R5` is now complete:
  - `H5` is unsupported
  - `split_k` is retired from the main GEMM surface
  - `rows_per_program` is retired from the main LayerNorm surface
  - no bounded tie-break rerun is currently required
- `R6` is now complete:
  - the final paper-facing non-`split_k` GEMM mainline surface has been exercised
  - the final representative GEMM mapping and selector ablation both completed successfully
  - the aligned refresh was skipped by gate
  - the confirmation reruns were skipped by gate
  - the final paper bundle is now the promotion boundary for paper-facing claims

Current implication:

- the controlled Phase 2 deepening pass is complete
- the bounded Phase 3 corrective pass is complete
- the bounded R6 final-mainline lock is complete
- no further execution round is justified inside the current paper-facing program

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
| `R5` Bounded corrective transfer pass | test whether a transfer-safe frontier plus one new orthogonal schedule family can recover strong representative GEMM behavior without reopening the whole program | `R4` analysis isolated one concrete expanded-space mechanism worth correcting | representative GEMM v3 mapping, GEMM v3 selector ablation, GEMM schedule diagnostics, aligned GEMM v3 context, bounded LayerNorm microstudy | updated hypothesis status, frontier diagnostics, family-mismatch summaries, split-`k` keep/drop evidence | `H5` is answered and the project can either pivot back to synthesis or record a clean bounded failure | paper-ready mainline GEMM transfer claim or paper-ready bounded negative result |
| `R6` Final mainline consolidation and paper-evidence lock | freeze the final reportable surfaces, run one last bounded representative-GEMM push on the non-`split_k` mainline, and lock the final paper bundle | `R5` complete and keep/drop decisions recorded | final representative GEMM mapping, final selector ablation, conditional aligned-context refresh, final claim bundle generation | final claim inventory, final figure source map, headline result summary, final bundle index | either one stable final positive representative-GEMM headline is promoted or the narrative is locked as a bounded limitation with no further selector-family expansion | final paper-evidence package with stable repo-local sources |

## Current Round Status

| Round | Current State | Notes |
| --- | --- | --- |
| `R0` | Operationally complete | broad and narrow live campaigns, profiler validation, reportability checks, and chained study generation have all been exercised across the qualified homogeneous A6000 pool |
| `R1` | Strong and expanded-space reinforced | original validation, `gpunode3` confirmation, and the completed `gemm_v2_baseline_mapping` study all support the view that compile signals prune but do not rank representative GEMM well enough |
| `R2` | Regime-split negative or weak | the corrected pooled rerun remained unsupported; the Phase 2 split studies show only a marginal small-batch profiling gain and an outright large-batch regression under `memory_activity_lite` |
| `R3` | Mixed after expansion | the narrower representative GEMM retry supported `H4`, but the expanded v2 GEMM baseline mapping and selector ablation show that the current frontier-aware revision does not generalize cleanly to the larger space |
| `R4` | Complete | the Phase 2 evidence bundle, docs, and figure plan are aligned closely enough to support a bounded next execution pass |
| `R5` | Complete as a bounded negative-result and keep/drop round | the transfer-safe selector revisions, GEMM v3 split-`k` surface, schedule-diagnostic batch, aligned-context refresh, and LayerNorm microstudy all completed; `H5` is unsupported, `split_k` is retired from the main GEMM surface, and `rows_per_program` is retired from the main LayerNorm surface |
| `R6` | Complete as the final bounded mainline lock | `gemm_final_baseline_mapping` and `gemm_final_selector_ablation` both completed successfully; the optional aligned refresh and confirmation reruns were skipped by gate; the final promoted interpretation now lives in the final paper bundle and claim inventory |

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

### Phase 3 corrective studies

- `configs/experiments/gemm_v3_reportable.yaml`
- `configs/experiments/gemm_v3_ablation_parent.yaml`
- `configs/experiments/gemm_v3_ablation_frontier.yaml`
- `configs/experiments/gemm_v3_ablation_profiled.yaml`
- `configs/experiments/gemm_v3_schedule_diag.yaml`
- `configs/experiments/gemm_v3_aligned_reportable.yaml`
- `configs/experiments/layernorm_v2_small_microstudy.yaml`
- `configs/experiments/layernorm_v2_large_microstudy.yaml`

### R6 final-mainline studies

- `configs/experiments/gemm_final_reportable.yaml`
- `configs/experiments/gemm_final_ablation_parent.yaml`
- `configs/experiments/gemm_final_ablation_frontier.yaml`
- `configs/experiments/gemm_final_ablation_profiled.yaml`
- `configs/experiments/gemm_final_aligned_reportable.yaml`

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
- `configs/studies/gemm_v3_baseline_mapping.yaml`
- `configs/studies/gemm_v3_selector_ablation.yaml`
- `configs/studies/gemm_v3_schedule_diag.yaml`
- `configs/studies/gemm_v3_aligned_reference.yaml`
- `configs/studies/layernorm_v2_small_microstudy.yaml`
- `configs/studies/layernorm_v2_large_microstudy.yaml`
- `configs/studies/gemm_final_baseline_mapping.yaml`
- `configs/studies/gemm_final_selector_ablation.yaml`
- `configs/studies/gemm_final_aligned_reference.yaml`

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
- `configs/campaigns/gemm_v3_baseline_mapping.yaml`
- `configs/campaigns/gemm_v3_selector_ablation.yaml`
- `configs/campaigns/gemm_v3_schedule_diag.yaml`
- `configs/campaigns/gemm_v3_aligned_reference.yaml`
- `configs/campaigns/layernorm_v2_microstudy.yaml`
- `configs/campaigns/gemm_final_baseline_mapping.yaml`
- `configs/campaigns/gemm_final_selector_ablation.yaml`
- `configs/campaigns/gemm_final_aligned_reference.yaml`

## Required Artifacts Per Round

| Round | Minimum Artifacts |
| --- | --- |
| `R0` | runtime repeatability data, counter availability, environment provenance summary |
| `R1` | held-out pairwise comparisons, signal-runtime correlations, first workload-class analysis |
| `R2` | matched-budget profiled comparisons, counter-set acceptance results, cross-kernel comparison |
| `R3` | opportunity catalog, revised-selector comparison, selected failure case studies |
| `R4` | final cross-run summary, final figure/table source map, final hypothesis status table |
| `R5` | representative GEMM v3 comparison, selector ablation, schedule diagnostics, aligned-context refresh, bounded LayerNorm microstudy |
| `R6` | final representative GEMM comparison, final selector ablation, conditional aligned-context refresh, final claim inventory, final paper bundle |

## Immediate Work Queue

The immediate queue is now documentation, figure extraction, and handoff rather than additional execution.

### Step 1: keep the final promoted evidence set stable

- use `artifacts/analysis/final_paper_20260403/` as the current final bundle boundary
- keep the canonical R6 studies pinned to:
  - `gemm_final_baseline_mapping` `run_20260330T014317Z_359c1904`
  - `gemm_final_selector_ablation` `run_20260330T023529Z_7c800187`
- keep the prepared R7 configs and launcher unpromoted until the A6000 pool becomes available again

### Step 2: write only from promoted sources

- use Phase 2 for aligned-context and LayerNorm regime figures
- use Phase 3 for split-`k` and family-mismatch diagnostics
- use R6 for the final representative GEMM headline and final ablation

### Step 3: do not reopen execution by default

- the aligned refresh was intentionally skipped by gate
- the confirmation reruns were intentionally skipped by gate
- no further selector-family expansion or new execution round is justified unless a paper-facing provenance gap appears later

### Step 5: promote the completed R5 and R6 interpretation into the research layer

- append a dated Phase 3 execution-analysis log
- append a dated R6 execution-analysis log
- update the evidence registry and opportunity log
- update the figure plan and paper outline
- record that `H5` is unsupported
- record that `split_k` and `rows_per_program` are retired from the mainline surfaces
- record the final mainline headline decision

### Step 6: rerun only if an explicit credibility gate is later hit

- no bounded rerun is currently required
- any future rerun must be justified by a concrete contradiction, near-threshold instability, or unresolved keep/drop ambiguity
- as of April 3, 2026, the prepared R7 budget-sweep and stability package is blocked by an administrative A6000 drain (`gpunode2` / `gpunode3` moving to DCA), not by a scientific gate failure

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
