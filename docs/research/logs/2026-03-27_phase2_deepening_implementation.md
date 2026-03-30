# Phase 2 Deepening Implementation

Purpose: record the implementation-side changes that prepare the next research execution
cycle after the completed `gpunode3` evidence block.

Date: March 27, 2026

## Motivation

The completed `H1` and `H4` wins, together with the corrected `H2` non-support, showed that
the current v1 implementation had two remaining ceilings:

- the tuner space was still too narrow to fully test the strengthened GEMM story
- the historical config generator could silently cap the raw search space before validation

Phase 2 therefore focuses on implementation changes that make the next experiments more
scientifically defensible rather than merely more numerous.

## Implemented Phase 2 Changes

### Candidate generation

- `SelectionBudget.max_candidates` is now treated as a hard admissibility limit after config validation
- candidate generation records both raw Cartesian counts and globally valid config counts
- runs now fail explicitly on overflow instead of silently truncating the raw config grid

### GEMM v2

- admitted `group_size_m` as a first new GEMM v2 knob
- allowed masked execution when `block_m` and `block_n` exceed the problem dimensions
- admitted `block_k` expansion to `{32, 64}`
- created `gemm_v2` config families and representative/aligned Phase 2 experiment specs
- added `v3_frontier_only` to isolate frontier construction from profile-aware reranking

### LayerNorm v2

- carried forward the corrected universal baseline (`block_size=4096`, `num_warps=4`, `num_stages=2`)
- admitted `rows_per_program`
- split new reportable work into `small_batch` and `large_batch`
- created `memory_activity_lite` to add one activity-aware signal to the memory-centric profile recipe

### Environment policy

- Phase 2 primary studies now treat `gpunode2` and `gpunode3` as one qualified homogeneous
  `RTX A6000` pool
- historical v1 studies remain identifiable as pinned or requalification runs, but new primary
  studies use the pool-level reportability target `rtx_a6000_pool`

## New Phase 2 Execution Surface

### Representative GEMM

- `configs/experiments/gemm_v2_reportable.yaml`
- `configs/studies/gemm_v2_baseline_mapping.yaml`
- `configs/campaigns/gemm_v2_baseline_mapping.yaml`

### GEMM ablation

- `configs/experiments/gemm_v2_ablation_parent.yaml`
- `configs/experiments/gemm_v2_ablation_frontier.yaml`
- `configs/experiments/gemm_v2_ablation_v3.yaml`
- `configs/studies/gemm_v2_selector_ablation.yaml`
- `configs/campaigns/gemm_v2_selector_ablation.yaml`

### LayerNorm regimes

- `configs/experiments/layernorm_v2_small_reportable.yaml`
- `configs/experiments/layernorm_v2_large_reportable.yaml`
- `configs/studies/layernorm_v2_small_regime.yaml`
- `configs/studies/layernorm_v2_large_regime.yaml`
- `configs/campaigns/layernorm_v2_regime_studies.yaml`

## Immediate Validation Requirements

- run local config-loader and contract tests
- run GPU-side `validate-counter-set` for `compute_lite` and `memory_activity_lite`
- run one end-to-end `run-experiment` on representative GEMM v2
- run one end-to-end `run-experiment` on both LayerNorm v2 regimes

## Expected Research Payoff

If the Phase 2 execution succeeds, the project should gain:

- a stronger representative GEMM result on a larger and more realistic search space
- a direct ablation explaining whether frontier construction or profile-aware reranking causes
  the `v3` improvement
- a regime-aware LayerNorm story that is more informative than the current pooled negative result
