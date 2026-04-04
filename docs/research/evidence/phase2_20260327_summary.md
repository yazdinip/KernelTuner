# Phase 2 Promoted Summary

Derived from the completed Phase 2 execution chain on March 27, 2026.

## Integrity

- `gemm_v2_baseline_mapping`: `6/6` jobs, `0` failures, `success`
- `gemm_v2_selector_ablation`: `18/18` jobs, `0` failures, `success`
- `layernorm_v2_regime_studies`: `12/12` jobs, `0` failures, `success`
- `gemm_v2_aligned_reference`: `6/6` jobs, `0` failures, `success`

## Promoted Findings

- `H1` is supported on the expanded non-`split_k` representative GEMM surface.
  - `naive_random_search`: `1.0331` geomean speedup vs default
  - `prune_rank`: `0.8265`
  - `prune_rank_profiled`: `0.8444`
  - takeaway: cheap compile-adjacent signals prune better than they rank

- The widened `v3` revision does not generalize on the expanded Phase 2 space.
  - `prune_rank_revised(v3_h4_targeted)`: `0.1458`
  - takeaway: the narrow-space frontier-aware win does not carry over automatically

- `H3` remains contextually supported.
  - representative GEMM `prune_rank`: `0.8265`
  - aligned GEMM `prune_rank`: `0.8795`
  - representative GEMM `prune_rank_profiled`: `0.8444`
  - aligned GEMM `prune_rank_profiled`: `0.8873`
  - takeaway: aligned workloads flatter the selector

- LayerNorm remains regime-split and secondary.
  - `small_batch`: `prune_rank=1.0100`, `prune_rank_profiled=1.0113`
  - `large_batch`: `prune_rank=1.0029`, `prune_rank_profiled=0.9856`
  - takeaway: profiling is weak/noisy in `small_batch` and regresses in `large_batch`

## Role In The Final Paper

Phase 2 provides the strongest expanded-space support for:

- cheap compile-adjacent pruning as a real but limited tool
- aligned GEMM as context rather than truth source
- LayerNorm as a bounded regime-split explanation rather than a second headline
