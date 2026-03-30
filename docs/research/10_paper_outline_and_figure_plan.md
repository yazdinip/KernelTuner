# Paper Outline And Figure Plan

Purpose: map the research docs and generated artifacts directly onto the eventual paper structure.
Status: Backbone
Update Rule: update whenever a required paper section, figure, or table changes.
Feeds Paper Sections: all sections directly
Depends On: [01_research_program.md](01_research_program.md), [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [08_evidence_registry.md](08_evidence_registry.md)

## Paper Outline

| Section | Purpose | Primary Source Docs | Primary Artifact Sources |
| --- | --- | --- | --- |
| Introduction | motivate bottleneck-aware Triton tuning and state the research question | `01_research_program.md`, proposal | manual prose plus final hypothesis summary |
| Background and Tuning Space | explain schedule-first tuning and knob families | `02_tuning_theory_and_knob_space.md`, `03_bottleneck_taxonomy.md` | knob-to-signal matrix, bottleneck taxonomy table |
| Method | describe the selector ladder, signal tiers, workload program, and matched-budget protocol | `04_signal_and_profiling_plan.md`, `05_workload_matrix_and_case_studies.md`, `06_hypotheses_and_ablation_plan.md` | protocol tables, workload tables, study configs |
| Experimental Setup | pin the environment, workloads, and evaluation rules | `05_workload_matrix_and_case_studies.md`, top-level protocol and environment docs | environment provenance, experiment configs |
| Results | answer `H1` through `H5` with cross-run evidence, including the completed Phase 3 bounded negative-result and the completed R6 final-mainline lock | `06_hypotheses_and_ablation_plan.md`, `08_evidence_registry.md`, `11_final_claim_inventory.md` | `cross_run_summary.json`, stability reports, held-out comparison tables, final bundle summaries |
| Failure Analysis and Opportunities | explain wins, misses, revised-selector behavior, and the keep/drop decisions that close the program | `03_bottleneck_taxonomy.md`, `09_opportunity_log.md`, `11_final_claim_inventory.md` | opportunity catalog, bottleneck signatures, case-study plots, final claim table |
| Limitations | state what the study does not claim | `01_research_program.md`, `08_evidence_registry.md` | hypothesis status table, unresolved-confounds summary |
| Conclusion | summarize what was learned about lightweight bottleneck-aware tuning | final evidence registry and paper draft | final hypothesis summary |

## Required Tables

| Table ID | Table | Source |
| --- | --- | --- |
| `T1` | Research question, scope, and success criteria | `01_research_program.md` |
| `T2` | Knob families and expected physical effects | `02_tuning_theory_and_knob_space.md` |
| `T3` | Bottleneck taxonomy | `03_bottleneck_taxonomy.md` |
| `T4` | Signal tiers and counter sets | `04_signal_and_profiling_plan.md` |
| `T5` | Workload matrix by kernel family and class | `05_workload_matrix_and_case_studies.md` |
| `T6` | Selector ladder and hypothesis mapping | `06_hypotheses_and_ablation_plan.md` |
| `T7` | Final hypothesis status summary | `08_evidence_registry.md` and final cross-run summary |

## Required Figures

| Figure ID | Figure | Claim It Supports | Source Study / Artifact |
| --- | --- | --- | --- |
| `F1` | strategy speedup by workload class on the final representative GEMM mainline | the final non-`split_k` mainline selector yields the strongest representative GEMM result in the project | `gemm_final_baseline_mapping` |
| `F2` | aligned vs representative GEMM context comparison | aligned workloads can overstate selector quality relative to the representative GEMM truth source | `gemm_v2_aligned_reference` vs `gemm_v2_baseline_mapping` |
| `F3` | LayerNorm regime split: `small_batch` vs `large_batch` profiling outcomes | profiling helps differently by LayerNorm regime and not uniformly by kernel family | `layernorm_v2_small_regime` and `layernorm_v2_large_regime` |
| `F4` | repeated-run stability by strategy | results are or are not stable enough for strong claims | stability reports from repeatability mode |
| `F5` | counter availability by counter set | reportable vs diagnostic profiling evidence is clearly separated | counter-availability reports |
| `F6` | signal-to-runtime correlation overview | some cheap signals are informative and others are weak | correlation artifacts from GEMM and LayerNorm runs |
| `F7` | revised-selector transfer and final-mainline ablation | measured failure analysis can motivate a better heuristic, but the final headline must survive the conservative non-`split_k` mainline lock | `gemm_final_selector_ablation` |
| `F8` | bottleneck or opportunity distribution across workload classes | failure modes are structured rather than random | bottleneck signatures and opportunity catalog |
| `F9` | retired | absorbed into the final narrative rather than promoted as a standalone figure | use `H5` text plus `F11` if needed |
| `F10` | retired | absorbed into `F7` and the failure-analysis text | no standalone promotion |
| `F11` | chosen-family vs best-family frontier diagnostic | the selector either learns the right schedule family or systematically misses it for interpretable reasons | `gemm_v3_schedule_diag` plus study-level frontier diagnostics |
| `F12` | retired | the `rows_per_program` keep/drop decision now lives in text and the final claim inventory rather than as a standalone figure | no standalone promotion |

## Current Figure Readiness

| Figure ID | Current Readiness | Notes |
| --- | --- | --- |
| `F1` | Final | the completed `gemm_final_baseline_mapping` study is now the canonical representative GEMM headline source |
| `F2` | Final | the Phase 2 aligned-context comparison is the canonical aligned-versus-representative figure because the optional R6 aligned refresh was skipped by gate |
| `F3` | Final | the completed `layernorm_v2_small_regime` and `layernorm_v2_large_regime` studies remain the strongest LayerNorm regime-split figure source |
| `F4` | Provisionally backed | repeatability and robustness evidence now exists in both the original validation block and the completed v2 studies; final paper usage should rely on archived artifact paths |
| `F5` | Provisionally backed | Tier 1 counter-set acceptance has live evidence on the current A6000 stack, including `memory_activity_lite` |
| `F6` | Provisionally backed | correlation artifacts still need interpretation and pruning, but the v2 studies now give a cleaner set of candidate figure sources |
| `F7` | Final | the completed `gemm_final_selector_ablation` study is the canonical revised-selector mechanism figure |
| `F8` | Strongly provisionally backed | bottleneck-signature, opportunity, and diagnostic artifacts now include the completed v2 studies and the reusable Phase 2 analysis bundle |
| `F9` | Retired | the split-`k` negative result stays in text and the evidence registry rather than the narrow final figure set |
| `F10` | Retired | the Phase 3 transfer-ablation is now supporting text for `H5`, not a standalone final figure |
| `F11` | Strongly backed as a diagnostic failure-analysis figure | the completed schedule-diagnostic batch plus the analysis bundle now expose chosen-family vs best-family mismatch and dominated non-unit `split_k` frontier rows |
| `F12` | Retired | the completed Phase 3 LayerNorm microstudy now feeds the final claim inventory directly instead of staying as a standalone final figure |

R6 note:

- `F1` and `F7` are now promoted from the completed bounded final-mainline studies.
- `F2` intentionally remains on the stronger Phase 2 aligned-context source because the optional R6 aligned refresh was skipped by gate.
- the final figure set is intentionally narrow: `F1`, `F2`, `F3`, `F7`, and `F11`.

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
  - `artifacts/analysis/phase2_20260327/`
- Canonical Phase 3 summary bundle:
  - `artifacts/analysis/phase3_20260329/`
- Final paper-evidence bundle:
  - `artifacts/analysis/final_paper_20260330/`
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
  - strongest sources: `gemm_v3_baseline_mapping`, `gemm_v3_selector_ablation`, `gemm_v3_schedule_diag`, `artifacts/analysis/phase3_20260329/`
- The completed `R6` final-mainline lock provides the strongest final headline: a guarded non-`split_k` mainline selector materially improves representative GEMM under the same budget and approaches random search.
  - strongest sources: `gemm_final_baseline_mapping`, `gemm_final_selector_ablation`, `artifacts/analysis/final_paper_20260330/`
- The completed Phase 3 LayerNorm microstudy is strong enough to retire `rows_per_program` from the main reportable LayerNorm surface.
  - strongest sources: `layernorm_v2_small_microstudy`, `layernorm_v2_large_microstudy`, `artifacts/analysis/phase3_20260329/`

## Current Analysis Goal

The current synthesis phase should no longer decide whether to run more experiments. It should:

- lock the final paper bundle to the completed Phase 2, Phase 3, and R6 evidence together,
- write the representative GEMM story around the bounded positive R6 mainline result,
- keep `H5` as a bounded negative result specific to the split-`k` Phase 3 surface,
- write the revised-selector result as a transfer-and-consolidation story rather than a universal success story,
- and keep LayerNorm as a regime-aware secondary story with the `rows_per_program` keep/drop decision already resolved.

## Figure Readiness Rules

A figure is ready for the paper only when:

- its source study is reportable or explicitly labeled diagnostic,
- the relevant hypothesis status is up to date,
- and the figure can be reproduced from recorded artifacts without manual hidden steps.

Current caution:

- the first validation batch is useful for planning and interpretation, but some artifacts still live in expiring scratch paths
- any figure promoted into the final paper should come from archived or rerun evidence with stable provenance
- the promoted Phase 3 figures should come from the canonical confirmation studies and the reusable Phase 3 analysis bundle, not from superseded partial attempts
- any promoted R6 figure must come from the final paper bundle under `artifacts/analysis/final_paper_<date>/` and must not rely on superseded campaign roots

## What Counts As Unproductive Experimentation

An experiment is not helping the paper if it does not:

- move one hypothesis toward support, rejection, or inconclusive,
- create a new admitted opportunity entry,
- or fill a missing figure/table source.

If a planned run does none of those things, it should be deprioritized.
