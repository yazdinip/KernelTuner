# 2026-03-30 R6 Final Synthesis And Evidence Lock

Purpose: record the final promoted artifact set, the `R6` gate outcomes, and the final project-level narrative used by the paper-facing backbone docs.
Status: Final synthesis log
Related Backbone Docs:
- [06_hypotheses_and_ablation_plan.md](../06_hypotheses_and_ablation_plan.md)
- [07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md)
- [08_evidence_registry.md](../08_evidence_registry.md)
- [10_paper_outline_and_figure_plan.md](../10_paper_outline_and_figure_plan.md)
- [11_final_claim_inventory.md](../11_final_claim_inventory.md)

## Canonical Promoted Artifact Set

The final paper-facing artifact set is pinned to:

- `artifacts/studies/gemm_final_baseline_mapping/run_20260330T014317Z_359c1904`
- `artifacts/studies/gemm_final_selector_ablation/run_20260330T023529Z_7c800187`
- `artifacts/studies/gemm_v3_schedule_diag/run_20260328T212649Z_7755304a`
- `artifacts/studies/gemm_v2_aligned_reference/run_20260327T190124Z_3a34cdc7`
- `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989`
- `artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba`
- `artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d`
- `artifacts/studies/layernorm_v2_small_microstudy/run_20260329T053448Z_7c6e5dc1`
- `artifacts/studies/layernorm_v2_large_microstudy/run_20260329T053455Z_c4118a25`
- `artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec`
- `artifacts/analysis/phase2_20260327/`
- `artifacts/analysis/phase3_20260329/`
- `artifacts/analysis/final_paper_20260330/`

## R6 Gate Outcomes

The bounded final-mainline program completed cleanly:

- representative GEMM final mapping: completed
- final selector ablation: completed
- aligned refresh: skipped by gate
- confirmation reruns: skipped by gate

Interpretation:

- the guarded `v5_mainline_profiled` selector materially improved the final representative GEMM mainline result
- the result was strong enough to promote as the final mainline headline
- the stricter positive-seed gate did not clear, so the bundle records the result as a bounded improvement rather than the strongest promotion tier

## Explicit Exclusions

The final paper-facing package intentionally excludes:

- incomplete or superseded campaign roots from any round
- optional `R6` aligned-refresh or confirmation rerun roots that were never meant to exist after the gate decision
- moved noncanonical Phase 3 raw experiment roots under `/tmp/.../phase3_raw`

Those raw Phase 3 roots remain archival provenance only and must not be used as promoted figure or claim sources.

## Final Promotion Decisions

- promote the final representative GEMM headline from `gemm_final_baseline_mapping`
- promote the final revised-selector mechanism figure from `gemm_final_selector_ablation`
- keep aligned-context evidence on the stronger Phase 2 paired source
- keep the LayerNorm regime figure on the stronger Phase 2 split studies
- keep the chosen-family vs best-family diagnostic on the Phase 3 schedule-diagnostic study
- keep `H5` explicitly unsupported and specific to the expanded `split_k` Phase 3 surface
- retire `split_k` from the main GEMM surface
- retire `rows_per_program` from the main LayerNorm surface
- close the current paper-facing research program without another selector-family expansion

## Final Narrative Summary

The final paper-facing story is now:

- cheap compile-adjacent signals are valuable for pruning but not sufficient for representative GEMM ranking
- aligned GEMM is still useful as context, but it is not the truth source
- LayerNorm remains a regime-split secondary result rather than a major positive profiling story
- revised selectors are a transfer story: narrow wins can fail on expanded spaces
- the expanded `split_k` corrective pass is a bounded negative result that produced a principled keep/drop decision
- the final conservative non-`split_k` mainline lock yields the strongest representative GEMM result in the project

This closes the research program in a paper-ready state: one coherent evidence package, one constrained claim inventory, one narrow figure set, and no remaining justification for another exploratory selector round.
