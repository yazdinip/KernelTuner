# Paper Section Index

This file maps manuscript sections to the source docs, canonical artifacts, claim IDs, and figure/table IDs used in the first draft.

| Manuscript Section | Primary Source Docs | Primary Supporting Sources | Claim IDs | Figures / Tables |
| --- | --- | --- | --- | --- |
| Abstract | `docs/research/01_research_program.md`, `docs/research/11_final_claim_inventory.md` | evidence registry plus final synthesis log | `C-FINAL-HEADLINE`, `C-FINAL-H2`, `C-FINAL-H5` | none |
| Introduction | `docs/research/01_research_program.md`, `docs/research/11_final_claim_inventory.md`, `docs/research/12_related_work_and_positioning.md` | final claim inventory and ADR-backed scope decisions | `C-FINAL-HEADLINE`, `C-FINAL-H1`, `C-FINAL-H4`, `C-FINAL-CLOSEOUT` | `T1` |
| Background and Problem Setting | `docs/research/02_tuning_theory_and_knob_space.md`, `docs/research/03_bottleneck_taxonomy.md`, `docs/research/05_workload_matrix_and_case_studies.md`, `docs/research/12_related_work_and_positioning.md` | research backbone docs and workload program | `C-FINAL-H1`, `C-FINAL-H3` | `T2`, `T3`, Figure 1 |
| Related Work | `docs/research/12_related_work_and_positioning.md` plus bibliography | literature positioning doc and bibliography | none directly | `T8` indirectly |
| KernelTuner Design | `docs/research/04_signal_and_profiling_plan.md`, `docs/research/06_hypotheses_and_ablation_plan.md` | research plan plus ADR decisions on scope and evaluation | `C-FINAL-SPLITK`, `C-FINAL-ROWS` | Figure 1, `T2` |
| Experimental Methodology | `docs/research/05_workload_matrix_and_case_studies.md`, `docs/research/07_experiment_campaign_plan.md`, `docs/research/08_evidence_registry.md`, `docs/adr/ADR-004-matched-budget-evaluation.md` | methodology and evaluation docs | all final claims indirectly | `T1`, `T3` |
| Results 6.1 | `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | `gemm_v2_baseline_mapping`, `gemm_v2_aligned_reference` | `C-FINAL-H1`, `C-FINAL-H3` | Figure 3, `T4` |
| Results 6.2 | `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | `layernorm_v2_small_regime`, `layernorm_v2_large_regime`, Phase 3 microstudy rows | `C-FINAL-H2`, `C-FINAL-ROWS` | Figure 4, `T4` |
| Results 6.3 | `docs/research/08_evidence_registry.md`, `docs/research/09_opportunity_log.md`, `docs/research/11_final_claim_inventory.md` | `h4_retry_g3`, `gemm_v3_baseline_mapping`, `gemm_v3_selector_ablation`, `gemm_v3_schedule_diag` | `C-FINAL-H4`, `C-FINAL-H5`, `C-FINAL-SPLITK` | Figure 5, `T4` |
| Results 6.4 | `docs/research/11_final_claim_inventory.md`, `docs/research/logs/2026-03-30_r6_final_synthesis_and_evidence_lock.md` | `gemm_final_baseline_mapping`, `gemm_final_selector_ablation` | `C-FINAL-HEADLINE`, `C-FINAL-CLOSEOUT` | Figure 2, Figure 5, `T4` |
| Discussion / Limitations | `docs/research/01_research_program.md`, `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | claim ledger, evidence registry, and ADR-backed limits | all final claims | none |
| Appendix | dated logs, research docs, and ADRs | `docs/research/logs/`, `docs/research/`, `docs/adr/` | all final claims | appendix-only tables |
