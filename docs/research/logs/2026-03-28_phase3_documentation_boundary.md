# 2026-03-28 Phase 3 Documentation Boundary

Purpose: record the current research-facing documentation freeze point after the bounded Phase 3 implementation pass and before any full Phase 3 evidence promotion.

## What This Boundary Includes

The research docs are currently intended to include:

- the original validation batch and its first `H1` through `H4` statuses
- the homogeneous-A6000 `gpunode3` requalification and focused follow-up execution block
- the corrected `H2` rerun and the successful narrow-space `H4` retry
- the completed Phase 2 v2 deepening studies and their analysis bundle
- the bounded Phase 3 transfer-safe implementation pass, including:
  - `H5`
  - `split_k`
  - `v4_transfer_safe_frontier`
  - `v4_transfer_safe_profiled`
  - `compute_schedule_diag`
  - the bounded LayerNorm microstudy surface

This means the research-facing interpretation is currently:

- `H1` strengthened
- `H2` regime-split weak or negative
- `H3` broadly supported and contextually reinforced
- `H4` mixed after expansion
- `H5` admitted but unevaluated

## What This Boundary Excludes

The docs intentionally do **not** yet promote partial or incomplete Phase 3 execution as settled evidence.

As of this boundary, completed-but-partial Phase 3 artifact families may exist under:

- `artifacts/campaigns/gemm_v3_baseline_mapping/`
- `artifacts/campaigns/gemm_v3_selector_ablation/`
- `artifacts/studies/gemm_v3_baseline_mapping/`
- `artifacts/studies/gemm_v3_selector_ablation/`

Those artifacts are useful operationally, but they are not yet treated as the project-level Phase 3 result because:

- the bounded R5 batch is not complete end to end
- `gemm_v3_schedule_diag` is still required for the intended mechanism explanation
- `gemm_v3_aligned_reference` is still required for the supporting `H3` context refresh
- `layernorm_v2_microstudy` is still required for the `rows_per_program` keep/drop decision

## Documentation Rule

Until the full bounded Phase 3 queue completes cleanly, the research-facing docs should:

- keep `H5` marked as unevaluated
- keep Phase 3 figures `F9` through `F12` marked pending
- treat `E-P3-READY` as the current top Phase 3 evidence row
- avoid promoting partial Phase 3 studies into the evidence registry or paper-outline claim set

## Why This Rule Exists

The project has already learned that partial execution can create misleading intermediate narratives:

- narrow-space success can fail to transfer when the search space expands
- pooled LayerNorm interpretation can obscure regime behavior
- completed individual campaigns are not enough if the planned explanatory and supporting studies are still missing

The boundary therefore preserves a cleaner research story:

- the project is ready for Phase 3 execution
- the implementation is complete enough to run
- but the research-facing interpretation still stops at implementation readiness until the full bounded execution pass is finished
