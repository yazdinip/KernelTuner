# Paper Outline And Figure Plan

Purpose: map the research docs and generated artifacts directly onto the eventual paper structure.
Status: Backbone
Update Rule: update whenever a required paper section, figure, or table changes.
Feeds Paper Sections: all sections directly
Depends On: [01_research_program.md](01_research_program.md), [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [08_evidence_registry.md](08_evidence_registry.md)

## Paper Outline

| Section | Purpose | Primary Source Docs | Primary Artifact Sources |
| --- | --- | --- | --- |
| Introduction | motivate bottleneck-aware Triton tuning and state the research question | `01_research_program.md`, `12_related_work_and_positioning.md`, proposal | manual prose plus final hypothesis summary |
| Related Work | position the project against autoscheduling, tensor-compiler autotuning, Triton-native tuning, external autotuners, and agentic CUDA optimization | `12_related_work_and_positioning.md` | reference shelf plus narrative synthesis |
| Background and Tuning Space | explain schedule-first tuning and knob families | `02_tuning_theory_and_knob_space.md`, `03_bottleneck_taxonomy.md`, `12_related_work_and_positioning.md` | knob-to-signal matrix, bottleneck taxonomy table |
| Method | describe the selector ladder, signal tiers, workload program, and matched-budget protocol | `04_signal_and_profiling_plan.md`, `05_workload_matrix_and_case_studies.md`, `06_hypotheses_and_ablation_plan.md` | protocol tables, workload tables, study configs |
| Experimental Setup | pin the environment, workloads, and evaluation rules | `05_workload_matrix_and_case_studies.md`, top-level protocol and environment docs | environment provenance, experiment configs |
| Results | answer `H1` through `H5` with cross-run evidence, including the completed Phase 3 bounded negative-result and the completed R6 final-mainline lock | `06_hypotheses_and_ablation_plan.md`, `08_evidence_registry.md`, `11_final_claim_inventory.md` | `cross_run_summary.json`, stability reports, held-out comparison tables, final bundle summaries |
| Failure Analysis and Opportunities | explain wins, misses, revised-selector behavior, and the keep/drop decisions that close the program | `03_bottleneck_taxonomy.md`, `09_opportunity_log.md`, `11_final_claim_inventory.md` | opportunity catalog, bottleneck signatures, case-study plots, final claim table |
| Limitations | state what the study does not claim | `01_research_program.md`, `08_evidence_registry.md` | hypothesis status table, unresolved-confounds summary |
| Conclusion | summarize what was learned about lightweight bottleneck-aware tuning | final evidence registry and paper draft | final hypothesis summary |

## Main-Text Tables

| Table ID | Table | Source |
| --- | --- | --- |
| `T1` | Research question, scope, and success criteria | `paper/tables/table_scope.tex`; `01_research_program.md` |
| `T2` | Final knob families and signal tiers | `paper/tables/table_knobs_signals.tex`; `02_tuning_theory_and_knob_space.md`; `04_signal_and_profiling_plan.md` |
| `T3` | Workload matrix by kernel family and class | `paper/tables/table_workloads.tex`; `05_workload_matrix_and_case_studies.md` |
| `T4` | Final hypothesis and claim summary | `paper/tables/table_claims.tex`; `11_final_claim_inventory.md`; `docs/research/evidence/final_paper_20260403/final_claim_table.csv` |
| `T5` | Related-work positioning table | `paper/tables/table_related_positioning.tex`; `12_related_work_and_positioning.md` |

## Main-Text Figures

| Figure ID | Figure | Claim It Supports | Source Study / Artifact |
| --- | --- | --- | --- |
| `F1` | conceptual pipeline schematic | the paper is about matched-budget evidence flow, not just final speedups | `docs/research/evidence/final_paper_20260403/figure1_pipeline_schematic.csv` |
| `F2` | representative GEMM budget-efficiency curve on the final non-`split_k` mainline | the final mainline result is bounded, positive, and should be read in a budgeted setting | `docs/research/evidence/final_paper_20260403/figure2_budget_curve.csv` |
| `F3` | aligned vs representative GEMM context comparison | aligned workloads can overstate selector quality relative to the representative GEMM truth source | `docs/research/evidence/final_paper_20260403/figure3_aligned_vs_representative.csv` |
| `F4` | LayerNorm regime split | profiling helps differently by LayerNorm regime and does not become a uniform cross-kernel win | `docs/research/evidence/final_paper_20260403/figure4_layernorm_regimes.csv` |
| `F5` | transfer/mainline two-panel figure | Phase 3 transfer failure is scientifically useful, and the final non-`split_k` mainline still admits a bounded recovery | `docs/research/evidence/final_paper_20260403/figure5_transfer_failure.csv`; `docs/research/evidence/final_paper_20260403/figure5_transfer_diagnostic.csv`; `docs/research/evidence/final_paper_20260403/figure5_mainline_ablation.csv` |

## Current Figure Readiness

| Figure ID | Current Readiness | Notes |
| --- | --- | --- |
| `F1` | Final | generated from the hardened final bundle and no longer hand-drawn in LaTeX |
| `F2` | Final | uses the canonical R6 point from `gemm_final_baseline_mapping` and is the final budget-efficiency figure for the current paper bundle |
| `F3` | Final | the Phase 2 aligned-context comparison remains the canonical aligned-versus-representative source |
| `F4` | Final | the Phase 2 regime studies remain the strongest LayerNorm regime-split figure source |
| `F5` | Final | the hardened draft combines Phase 3 transfer failure plus chosen-family note with the final mainline ablation into one two-panel figure |

Historical note:

- the hardened paper now uses a narrow five-figure set backed by generated PDFs under `paper/figures/generated/`
- the prepared R7 budget-sweep and stability studies were not executed on April 3, 2026 because both A6000 nodes were administratively drained (`moving to DCA`)
- those unexecuted studies are outside the current paper bundle and do not change the final figure set used by the paper

## Current Strongest Artifact Sources

- Representative GEMM final mainline headline:
  - `gemm_final_baseline_mapping` `run_20260330T014317Z_359c1904`
- Representative GEMM final selector ablation:
  - `gemm_final_selector_ablation` `run_20260330T023529Z_7c800187`
- Representative GEMM expanded-space baseline mapping:
  - `gemm_v2_baseline_mapping` `run_20260327T164637Z_0403b989`
- Representative GEMM selector ablation:
  - `gemm_v2_selector_ablation` `run_20260327T175823Z_376d6bbc`
- LayerNorm regime split:
  - `layernorm_v2_small_regime` `run_20260327T183157Z_53565cba`
  - `layernorm_v2_large_regime` `run_20260327T183158Z_37695a2d`
- Aligned GEMM v2 context:
  - `gemm_v2_aligned_reference` `run_20260327T190124Z_3a34cdc7`
- Narrow-space revised-selector success context:
  - `h4_retry_g3` `run_20260327T035659Z_10f9baec`
- Canonical summary bundle:
  - `docs/research/evidence/phase2_20260327_summary.md`
- Canonical Phase 3 summary bundle:
  - `docs/research/evidence/phase3_20260329_summary.md`
  - `docs/research/evidence/phase3_20260329/`
- Final paper-evidence bundle:
  - `docs/research/evidence/final_paper_20260403/`
- Representative GEMM Phase 3 canonical mapping:
  - `gemm_v3_baseline_mapping` `run_20260329T010211Z_dfb53abb`
- Representative GEMM Phase 3 canonical selector ablation:
  - `gemm_v3_selector_ablation` `run_20260329T034953Z_e8b8ac98`
- GEMM Phase 3 schedule diagnostic:
  - `gemm_v3_schedule_diag` `run_20260328T212649Z_7755304a`
- Aligned GEMM Phase 3 context:
  - `gemm_v3_aligned_reference` `run_20260329T045530Z_7086b0e7`
- LayerNorm Phase 3 canonical microstudies:
  - `layernorm_v2_small_microstudy` `run_20260329T053448Z_7c6e5dc1`
  - `layernorm_v2_large_microstudy` `run_20260329T053455Z_c4118a25`
- Full chronological execution record:
  - `docs/research/logs/2026-03-26_g3_requalification_and_followup_execution.md`
  - `docs/research/logs/2026-03-27_g3_followup_baselinefix_and_v3_retry.md`
  - `docs/research/logs/2026-03-27_phase2_execution_analysis.md`
  - `docs/research/logs/2026-03-29_phase3_execution_analysis.md`

## Current Writing-Ready Claims

- Cheap compile signals are useful for pruning but not sufficient for representative GEMM ranking, and that result survives the expanded v2 non-`split_k` space.
  - strongest source: `gemm_v2_baseline_mapping`
- Aligned GEMM still overstates selector quality relative to the representative workload.
  - strongest sources: `gemm_v2_baseline_mapping`, `gemm_v2_aligned_reference`, supported by the earlier broad studies
- LayerNorm should be written as a regime-aware mixed result, not a pooled profiling success.
  - strongest sources: `layernorm_v2_small_regime`, `layernorm_v2_large_regime`
- A frontier-aware revised selector can work on a narrower space, but the current rule does not transfer to the expanded v2 and v3 GEMM spaces cleanly.
  - strongest sources: `h4_retry_g3`, `gemm_v2_selector_ablation`, `gemm_v3_selector_ablation`
- The completed Phase 3 transfer-safe corrective pass is a bounded negative result: it does not recover near-random-search representative GEMM performance on the split-`k` space, and the additional schedule family should not stay in the mainline surface.
  - strongest sources: `gemm_v3_baseline_mapping`, `gemm_v3_selector_ablation`, `gemm_v3_schedule_diag`, `docs/research/evidence/phase3_20260329_summary.md`, `docs/research/evidence/phase3_20260329/`
- The completed `R6` final-mainline lock provides the strongest final headline: a guarded non-`split_k` mainline selector materially improves representative GEMM under the same budget and approaches random search.
  - strongest sources: `gemm_final_baseline_mapping`, `gemm_final_selector_ablation`, `docs/research/evidence/final_paper_20260403/`
- The completed Phase 3 LayerNorm microstudy is strong enough to retire `rows_per_program` from the main reportable LayerNorm surface.
  - strongest sources: `layernorm_v2_small_microstudy`, `layernorm_v2_large_microstudy`, `docs/research/evidence/phase3_20260329_summary.md`, `docs/research/evidence/phase3_20260329/`

## Final Analysis Position

The current synthesis phase is closed around the completed paper bundle. The remaining writing task is to keep the final paper aligned with the evidence already recorded. In practice that means:

- lock the final paper bundle to the completed Phase 2, Phase 3, and R6 evidence together,
- write the representative GEMM story around the bounded positive R6 mainline result,
- keep `H5` as a bounded negative result specific to the split-`k` Phase 3 surface,
- write the revised-selector result as a transfer-and-consolidation story rather than a universal success story,
- and keep LayerNorm as a regime-aware secondary story with the `rows_per_program` retirement decision already resolved.

## Figure Readiness Rules

A figure is ready for the paper only when:

- its source study is reportable or explicitly labeled diagnostic,
- the relevant hypothesis status is up to date,
- and the figure can be reproduced from recorded artifacts without manual hidden steps.

Current caution:

- the first validation batch is useful for planning and interpretation, but some artifacts still live in expiring scratch paths
- any figure included in the final paper should come from archived or rerun evidence with stable provenance
- the final Phase 3 figures should come from the canonical confirmation studies and the reusable Phase 3 analysis bundle, not from superseded partial attempts
- any final R6 figure must come from the tracked paper snapshot under `docs/research/evidence/final_paper_<date>/` and must not rely on superseded campaign roots

## What Counts As Unproductive Experimentation

An experiment is not helping the paper if it does not:

- move one hypothesis toward support, rejection, or inconclusive,
- create a new admitted opportunity entry,
- or fill a missing figure/table source.

If a planned run does none of those things, it should be deprioritized.
