# Paper Section Index

This file maps the extended manuscript to the current final bundle, canonical artifacts, claim IDs, and figure/table labels used in the hardened draft.

The condensed manuscript in [main_condensed.tex](/u/yazdinip/KernelTuner/paper/main_condensed.tex) uses the same claim set and the same canonical bundle, but compresses the argument into the course-required structure.

Canonical bundle:
- `artifacts/analysis/final_paper_20260403/`

| Manuscript Section | Primary Source Docs | Primary Artifacts | Claim IDs | Figures / Tables |
| --- | --- | --- | --- | --- |
| Abstract | `docs/research/01_research_program.md`, `docs/research/11_final_claim_inventory.md` | `artifacts/analysis/final_paper_20260403/final_bundle_summary.md` | `C-FINAL-HEADLINE`, `C-FINAL-H2`, `C-FINAL-H5` | none |
| Introduction | `docs/research/01_research_program.md`, `docs/research/11_final_claim_inventory.md`, `docs/research/12_related_work_and_positioning.md` | `artifacts/analysis/final_paper_20260403/final_claim_table.csv` | `C-FINAL-HEADLINE`, `C-FINAL-H1`, `C-FINAL-H4`, `C-FINAL-CLOSEOUT` | `tab:scope` |
| Background and Problem Setting | `docs/research/02_tuning_theory_and_knob_space.md`, `docs/research/03_bottleneck_taxonomy.md`, `docs/research/05_workload_matrix_and_case_studies.md`, `docs/research/12_related_work_and_positioning.md` | `artifacts/analysis/final_paper_20260403/figure1_pipeline_schematic.csv` | `C-FINAL-H1`, `C-FINAL-H3` | Figure `fig:pipeline`, `tab:knobs`, `tab:workloads` |
| \system Design | `docs/research/04_signal_and_profiling_plan.md`, `docs/research/06_hypotheses_and_ablation_plan.md` | final configs plus `artifacts/analysis/final_paper_20260403/figure1_pipeline_schematic.csv` | `C-FINAL-SPLITK`, `C-FINAL-ROWS` | Figure `fig:pipeline`, `tab:knobs` |
| Experimental Methodology | `docs/research/05_workload_matrix_and_case_studies.md`, `docs/research/07_experiment_campaign_plan.md`, `docs/research/08_evidence_registry.md` | `artifacts/analysis/final_paper_20260403/canonical_artifact_map.csv` | all final claims indirectly | `tab:scope`, `tab:claims` |
| Results: pruning and workload realism | `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | `gemm_v2_baseline_mapping`, `gemm_v2_aligned_reference`, `artifacts/analysis/final_paper_20260403/figure3_aligned_vs_representative.csv` | `C-FINAL-H1`, `C-FINAL-H3` | Figure `fig:aligned-context`, Figure `fig:mainline-headline` |
| Results: regime-dependent profiling | `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | `layernorm_v2_small_regime`, `layernorm_v2_large_regime`, Phase 3 microstudies | `C-FINAL-H2`, `C-FINAL-ROWS` | Figure `fig:layernorm-regimes`, `tab:claims` |
| Results: transfer failure and retirements | `docs/research/08_evidence_registry.md`, `docs/research/09_opportunity_log.md`, `docs/research/11_final_claim_inventory.md` | `h4_retry_g3`, `gemm_v3_baseline_mapping`, `gemm_v3_selector_ablation`, `gemm_v3_schedule_diag` | `C-FINAL-H4`, `C-FINAL-H5`, `C-FINAL-SPLITK` | Figure `fig:transfer-mainline`, `tab:claims` |
| Results: bounded mainline recovery | `docs/research/11_final_claim_inventory.md`, `docs/research/logs/2026-03-30_r6_final_synthesis_and_evidence_lock.md` | `gemm_final_baseline_mapping`, `gemm_final_selector_ablation`, `artifacts/analysis/final_paper_20260403/figure2_budget_curve.csv` | `C-FINAL-HEADLINE`, `C-FINAL-CLOSEOUT` | Figure `fig:mainline-headline`, Figure `fig:transfer-mainline`, `tab:claims` |
| Discussion / Limitations | `docs/research/01_research_program.md`, `docs/research/08_evidence_registry.md`, `docs/research/11_final_claim_inventory.md` | `artifacts/analysis/final_paper_20260403/final_bundle_summary.md` | all final claims | none |
| Related Work | `docs/research/12_related_work_and_positioning.md` plus bibliography | bibliography | framing only | `tab:related-positioning` |
| Appendix | dated logs and final bundle | `artifacts/analysis/final_paper_20260403/`, `artifacts/analysis/phase2_20260327/`, `artifacts/analysis/phase3_20260329/` | all final claims | `tab:rounds`, `tab:artifactmap` |
