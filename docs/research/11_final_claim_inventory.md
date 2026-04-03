# Final Claim Inventory

Purpose: lock the final paper-facing claim set to stable artifact sources and constrain wording so the final paper story stays consistent with the evidence.
Status: Backbone
Update Rule: update only when the final paper bundle or promoted claim set changes.
Feeds Paper Sections: Introduction, Results, Failure Analysis, Limitations, Conclusion
Depends On: [08_evidence_registry.md](08_evidence_registry.md), [10_paper_outline_and_figure_plan.md](10_paper_outline_and_figure_plan.md), `artifacts/analysis/final_paper_20260403/`

## Usage

This document is the final claim ledger for the paper-facing repo state.

- use only the wording recorded here or a weaker paraphrase
- cite only the artifact sources recorded here or stronger direct descendants in the same canonical bundle
- if a future draft needs a stronger claim than the wording below allows, treat that as a paper-scope issue rather than as permission to reinterpret the evidence

Current note:

- the `R7` budget-sweep and stability-extension configs exist, but on April 3, 2026 the A6000 pool (`gpunode2` / `gpunode3`) was administratively drained (`moving to DCA`), so no new promoted GPU evidence was added in this pass
- the canonical bundle for the hardened draft is therefore `artifacts/analysis/final_paper_20260403/`, which refreshes the paper package and figure sources without changing the promoted claim set

## Final Claim Set

| Claim ID | Class | Allowed Wording | Supporting Artifacts | Confidence | Caveat | Figure / Table |
| --- | --- | --- | --- | --- | --- | --- |
| `C-FINAL-HEADLINE` | Headline | A conservative `v5_mainline_profiled` selector yields a small but bounded representative GEMM improvement on the final non-`split_k` mainline under matched budget. | `artifacts/studies/gemm_final_baseline_mapping/run_20260330T014317Z_359c1904`; `artifacts/studies/gemm_final_selector_ablation/run_20260330T023529Z_7c800187`; `artifacts/analysis/final_paper_20260403/headline_result_summary.csv` | High | This is a bounded improvement rather than the strongest positive tier because the stricter positive-seed gate did not clear. Do not back-project this claim onto the archived Phase 3 `split_k` space. | `Figure 2`, `Figure 5`, `Table 4` |
| `C-FINAL-H1` | Supporting | Cheap compile-adjacent signals are useful for pruning but not sufficient for reliable representative GEMM ranking on realistic schedule surfaces. | `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989`; `artifacts/analysis/phase2_20260327/claim_table.csv`; `artifacts/analysis/final_paper_20260403/final_claim_table.csv` | High | The strongest final `H1` wording should rely on the Phase 2 expanded non-`split_k` surface, not on the later Phase 3 `split_k` negative-result batch. | `Figure 2`, `Figure 3`, `Table 4` |
| `C-FINAL-H2` | Supporting | LayerNorm is a regime-split secondary result: `small_batch` profiling is weak and noisy, while `large_batch` continues to favor compile-only ranking. | `artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba`; `artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d`; `artifacts/studies/layernorm_v2_small_microstudy/run_20260329T053448Z_7c6e5dc1`; `artifacts/studies/layernorm_v2_large_microstudy/run_20260329T053455Z_c4118a25` | Medium | Keep LayerNorm explanatory and bounded. Do not present it as a second major positive optimization story. | `Figure 4`, `Table 4` |
| `C-FINAL-H3` | Supporting | Aligned GEMM is useful as context, but it is not the truth source; it overstates selector quality relative to the representative GEMM workload program. | `artifacts/studies/gemm_v2_aligned_reference/run_20260327T190124Z_3a34cdc7`; `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989`; `artifacts/analysis/final_paper_20260403/figure_source_map.csv` | Medium | Write `H3` as evaluation-context support, not as the main headline finding. The optional R6 aligned refresh was intentionally skipped. | `Figure 3`, `Table 4` |
| `C-FINAL-H4` | Supporting | Revised selectors are a transfer story rather than a simple success story: a narrow-space frontier-aware revision worked, but later expanded-space evidence showed that the same revision family did not generalize cleanly. | `artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec`; `artifacts/studies/gemm_v3_selector_ablation/run_20260329T034953Z_e8b8ac98`; `artifacts/studies/gemm_final_selector_ablation/run_20260330T023529Z_7c800187`; `artifacts/analysis/final_paper_20260403/final_claim_table.csv` | High | Do not flatten this into “revisions always work” or “revisions always fail.” The defensible statement is mixed, transfer-limited evidence with a final guarded mainline recovery. | `Figure 5`, `Table 4` |
| `C-FINAL-H5` | Supporting | The transfer-safe `v4` corrective pass remained unsupported on the expanded `split_k` space. | `artifacts/studies/gemm_v3_baseline_mapping/run_20260329T010211Z_dfb53abb`; `artifacts/studies/gemm_v3_selector_ablation/run_20260329T034953Z_e8b8ac98`; `artifacts/analysis/phase3_20260329/claim_table.csv`; `artifacts/analysis/final_paper_20260403/final_claim_table.csv` | High | `H5` stays specific to the expanded Phase 3 `split_k` surface and must not absorb the later R6 non-`split_k` positive result. | `Figure 5`, `Table 4` |
| `C-FINAL-SPLITK` | Supporting | `split_k` is retired from the main GEMM reportable surface. | `artifacts/studies/gemm_v3_schedule_diag/run_20260328T212649Z_7755304a`; `artifacts/analysis/phase3_20260329/splitk_decision_table.csv` | High | This retires `split_k` from the final mainline surface only. It remains available as archived diagnostic code. | `Figure 5` |
| `C-FINAL-ROWS` | Supporting | `rows_per_program` is retired from the main LayerNorm surface. | `artifacts/studies/layernorm_v2_small_microstudy/run_20260329T053448Z_7c6e5dc1`; `artifacts/studies/layernorm_v2_large_microstudy/run_20260329T053455Z_c4118a25`; `artifacts/analysis/phase3_20260329/rows_per_program_decision_table.csv` | High | This retires `rows_per_program` from the final mainline surface only. It remains available as archived diagnostic code. | `Figure 4` |
| `C-FINAL-CLOSEOUT` | Supporting | No further selector-family growth is justified for the paper backbone. | `artifacts/studies/gemm_final_baseline_mapping/run_20260330T014317Z_359c1904`; `artifacts/studies/gemm_v3_baseline_mapping/run_20260329T010211Z_dfb53abb`; `artifacts/studies/gemm_v3_selector_ablation/run_20260329T034953Z_e8b8ac98`; `artifacts/analysis/final_paper_20260403/final_claim_table.csv` | High | This closes the current paper-facing research program. It does not claim that some future project could never justify a different selector family. | `Figure 2`, `Figure 5`, `Table 4` |

## Promotion Rule

Claims above are promotable because:

- the relevant campaigns and studies completed successfully
- the source artifacts are stable and repo-local
- the final paper bundle under `artifacts/analysis/final_paper_20260403/` has been regenerated
- the figure source map and evidence registry now agree on the promoted source set

Do not promote any claim that depends on:

- incomplete or superseded campaign roots
- `/tmp/.../phase3_raw`
- scratch-only raw experiment directories
- optional aligned-refresh or confirmation reruns that were intentionally skipped
