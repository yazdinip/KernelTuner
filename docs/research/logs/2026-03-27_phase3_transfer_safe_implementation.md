# 2026-03-27 Phase 3 Transfer-Safe Implementation

Purpose: record the bounded Phase 3 corrective implementation pass that prepares the next GEMM-first execution cycle after the completed Phase 2 analysis.

## Why This Phase Was Admitted

The completed Phase 2 evidence bundle established three things:

- representative GEMM remains the main scientific story
- the current frontier-aware `v3` revision did not transfer cleanly once the search space expanded
- the most specific remaining GEMM opportunity is a shape-relative, transfer-safe frontier correction rather than another profile-only reranker

That justified one bounded new top-level hypothesis:

- `H5`: a shape-relative, transfer-safe frontier policy can recover near-random-search representative GEMM performance on the expanded schedule space under the same matched budget, even after admitting `split_k`

This implementation pass prepares the code and config surface needed to evaluate `H5` without reopening the research program broadly.

## Implemented Surface

### Selector and diagnostics

- added `v4_transfer_safe_frontier`
- added `v4_transfer_safe_profiled`
- added shape-relative frontier features:
  - `tile_fit_ratio_m`
  - `tile_fit_ratio_n`
  - `masked_overcoverage_ratio`
  - `aspect_match_score`
  - `moderated_tile_area`
  - `group_size_m_centered`
- extended per-run reporting and cross-run comparison with:
  - frontier diagnostics
  - chosen-family vs best-family summaries
  - family mismatch aggregation

### GEMM kernel space

- added the Phase 3 GEMM kernel family `gemm_v3`
- admitted exactly one new GEMM schedule family:
  - `split_k: [1, 2, 4]`
- implemented correctness-safe split-`k` accumulation with explicit divisibility validation
- kept the existing Phase 2 tile/work knobs:
  - `block_m`
  - `block_n`
  - `block_k`
  - `group_size_m`
  - `num_warps`
  - `num_stages`

### Profiling

- kept `compute_lite` as the main reportable GEMM counter set
- added diagnostic-only `compute_schedule_diag` for GEMM mechanism work
- kept LayerNorm on `memory_activity_lite`

### LayerNorm follow-up

- admitted one bounded LayerNorm microstudy surface:
  - `layernorm_v2_small_microstudy`
  - `layernorm_v2_large_microstudy`
- preserved the corrected Phase 2 baseline
- kept the goal narrow:
  - decide whether `rows_per_program` is a real regime lever or dead weight

### Execution surface

Added the Phase 3 studies and campaigns:

- `gemm_v3_baseline_mapping`
- `gemm_v3_selector_ablation`
- `gemm_v3_schedule_diag`
- `gemm_v3_aligned_reference`
- `layernorm_v2_microstudy`

Added execution helper:

- `scripts/run_phase3_cycle.sh`

## Validation Completed

Local validation completed during this implementation pass:

- `python3 -m compileall src tests`
- targeted unit/config/reporting suite:
  - `30 passed`
- targeted GEMM integration suite:
  - `1 passed, 2 skipped`
- CLI-level study validation:
  - `gemm_v3_baseline_mapping`
  - `gemm_v3_selector_ablation`
  - `layernorm_v2_small_microstudy`
- CLI-level campaign materialization:
  - `gemm_v3_baseline_mapping`
  - `layernorm_v2_microstudy`

Important implementation correction:

- the original Phase 3 transfer-safe frontier test exposed that the first overcoverage metric only penalized tiles larger than the full shape
- this was corrected to use whole-shape tiled overcoverage, which better captures masked-edge waste and matches the intended frontier behavior

## Intended Execution Order

The next GPU block should run the Phase 3 program in this order:

1. `gemm_v3_baseline_mapping`
2. `gemm_v3_selector_ablation`
3. `gemm_v3_schedule_diag`
4. `gemm_v3_aligned_reference`
5. `layernorm_v2_microstudy`

Interpretation rules:

- GEMM remains the primary story
- `H5` is answered from the representative GEMM v3 studies
- aligned GEMM remains supporting context only
- LayerNorm remains bounded explanatory work only

## Phase Boundary

This implementation pass does not itself create new comparative evidence.

It should be read as:

- Phase 2 analysis complete
- Phase 3 bounded corrective execution prepared
- the project remains within the same homogeneous `RTX A6000` pool policy for `gpunode2` and `gpunode3`
- any later partial Phase 3 execution artifacts should remain outside the research-facing backbone docs until the full bounded R5 batch completes
