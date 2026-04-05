# Final Paper Evidence Bundle

## Headline Decision

- decision: `bounded_mainline_improvement`
- winner revision: `v5_mainline_profiled`
- winner mean speedup vs default: `1.0286`
- parent mean speedup vs default: `0.8101`
- random mean speedup vs default: `1.0011`
- winner delta vs parent: `0.2185`
- winner gap to random: `-0.0276`
- additional budget-sweep points in this bundle: `None`
- additional loss-budget points in this bundle: `None`
- additional stability seeds in this bundle: `None`

This bundle is complete for the current paper claim set. A prepared extension package was not executed after the qualified A6000 pool was administratively drained, so it remains outside the present final bundle rather than a missing dependency inside it.

## Final Claim Set

- `C-FINAL-HEADLINE` `bounded_mainline_improvement` `headline`: A conservative v5_mainline_profiled selector yields a small but bounded representative GEMM improvement on the final non-split_k mainline under matched budget.
- `C-FINAL-H1` `supported` `supporting`: Cheap compile-adjacent signals are useful for pruning but not sufficient for reliable representative GEMM ranking on realistic schedule surfaces.
- `C-FINAL-H2` `bounded_mixed` `supporting`: LayerNorm is a regime-split secondary result: small_batch profiling is weak and noisy, while large_batch continues to favor compile-only ranking.
- `C-FINAL-H3` `contextual_support` `supporting`: Aligned GEMM is useful as context, but it is not the truth source; it overstates selector quality relative to the representative GEMM workload program.
- `C-FINAL-H4` `mixed_transfer_limited` `supporting`: Revised selectors are a transfer story rather than a simple success story: a narrow-space frontier-aware revision worked, but later expanded-space evidence showed that the same revision family did not generalize cleanly.
- `C-FINAL-H5` `unsupported` `supporting`: The transfer-safe v4 corrective pass remained unsupported on the expanded split_k space.
- `C-FINAL-SPLITK` `retire` `supporting`: split_k is retired from the main GEMM reportable surface.
- `C-FINAL-ROWS` `retire` `supporting`: rows_per_program is retired from the main LayerNorm surface.
- `C-FINAL-CLOSEOUT` `closed` `supporting`: No further selector-family growth is justified for the paper backbone.

## Figure Sources

- `F1`: design and methodology docs -> `docs/research/evidence/final_paper_20260403/figure1_pipeline_schematic.csv`
- `F2`: gemm_final_baseline_mapping -> `docs/research/evidence/final_paper_20260403/figure2_budget_curve.csv`
- `F3`: gemm_v2_aligned_reference + gemm_v2_baseline_mapping -> `docs/research/evidence/final_paper_20260403/figure3_aligned_vs_representative.csv`
- `F4`: layernorm_v2_small_regime + layernorm_v2_large_regime -> `docs/research/evidence/final_paper_20260403/figure4_layernorm_regimes.csv`
- `F5A`: gemm_v3_selector_ablation + gemm_v3_schedule_diag -> `docs/research/evidence/final_paper_20260403/figure5_transfer_failure.csv`
- `F5B`: gemm_final_selector_ablation -> `docs/research/evidence/final_paper_20260403/figure5_mainline_ablation.csv`
