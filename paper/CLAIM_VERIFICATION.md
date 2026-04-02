# Claim Verification Notes

This note records the post-edit verification pass for the current manuscript.

## Verification Scope

Verified against:

- `docs/research/11_final_claim_inventory.md`
- `docs/research/08_evidence_registry.md`
- `docs/research/12_related_work_and_positioning.md`
- `docs/adr/ADR-001-single-host-single-gpu.md`
- `docs/adr/ADR-004-matched-budget-evaluation.md`
- `paper/DRAFT_CHECKLIST.md`
- `paper/appendix/extended_results.tex`
- dated execution-analysis logs under `docs/research/logs/`

Primary paper sections checked:

- `paper/sections/abstract.tex`
- `paper/sections/introduction.tex`
- `paper/sections/results.tex`
- `paper/sections/discussion.tex`
- `paper/sections/conclusion.tex`

## Main Outcome

The current manuscript stays within the locked paper-safe claim set.

The core claim structure is consistent across abstract, introduction, results, discussion, and conclusion:

- cheap compile-adjacent signals help with pruning more than ranking,
- aligned GEMM is supporting context rather than the truth source,
- LayerNorm is a bounded regime-split secondary result,
- revised selectors are a mixed transfer story rather than a universal success,
- `H5` remains the unsupported Phase 3 `split_k` result,
- and the final non-`split_k` mainline result is a bounded positive headline.

## Numeric Claims Checked

The following main-text numbers were checked against the evidence registry and dated logs:

- Phase 2 representative GEMM:
  - `naive_random_search = 1.0331`
  - `prune_rank = 0.8265`
  - `prune_rank_profiled = 0.8444`
- Phase 2 aligned GEMM:
  - `prune_rank = 0.8795`
  - `prune_rank_profiled = 0.8873`
  - `naive_random_search = 0.9951`
- Phase 2 LayerNorm:
  - `small_batch`: `1.0100` vs `1.0113`
  - `large_batch`: `1.0029` vs `0.9856`
- Phase 3 `split_k` result:
  - parent `prune_rank = 1.0324`
  - `naive_random_search = 1.0427`
  - `v4_transfer_safe_profiled = 0.1609`
  - ablation values `0.1622`, `0.1623`, and parent `0.9692`
- Final R6 mainline:
  - parent `prune_rank = 0.8101`
  - `naive_random_search = 1.0011`
  - `v5_mainline_profiled = 1.0286`
  - improvement over parent `0.2185`

## Checklist Status

Checked and satisfied in the current source:

- every main-text claim matches the final claim inventory or a weaker paraphrase
- `H5` is still written only as the unsupported Phase 3 `split_k` result
- `R6` is still written as a bounded improvement, not a universal win
- LayerNorm remains secondary and regime-split
- introduction, abstract, results, discussion, and conclusion now tell the same final story
- appendices remain chronology/provenance oriented rather than introducing new promoted claims

## Documentation Backbone Used For Verification

For this workspace snapshot, the paper backbone should be treated as:

- `docs/research/` for claims, interpretation, and experiment history,
- `docs/adr/` for fixed environment and evaluation decisions,
- and `docs/research/logs/` for the chronological execution record.

The artifact bundle paths referenced in older documentation are not the primary verification source in this checkout.

This verification pass is therefore grounded in:

- the claim ledger,
- the evidence registry,
- the related-work and paper-outline research docs,
- the relevant ADRs,
- appendix artifact mappings,
- and the dated analysis logs.

That is strong enough to verify that the manuscript stays consistent with the repo's documented evidence backbone.

## Paper Build Status

The paper compiles successfully with:

- `tectonic -X compile main.tex`

Current output:

- `paper/main.pdf`

Known remaining issue:

- the PDF still has many table and appendix line-breaking warnings (`Underfull` / `Overfull` boxes), but the build succeeds and the references now start on a new page.
