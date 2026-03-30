# Phase 2 Execution Analysis

Purpose: record the completed March 27, 2026 Phase 2 deepening analysis, tie every major claim to a stable artifact bundle, and state what the results do and do not justify next.
Status: Log
Update Rule: append-only; do not rewrite past observations except to fix factual errors.
Feeds Paper Sections: Results, Failure Analysis, Discussion, Limitations
Depends On: [../07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md), [../08_evidence_registry.md](../08_evidence_registry.md), [../09_opportunity_log.md](../09_opportunity_log.md), [../10_paper_outline_and_figure_plan.md](../10_paper_outline_and_figure_plan.md)

## Canonical Artifact Bundle

- repository commit: `3ec6e86`
- execution cycle log: `artifacts/phase2_deepening_cycle_20260327T155853Z.log`
- execution cycle status: `artifacts/phase2_deepening_cycle_20260327T155853Z.status`
- generated analysis bundle:
  - `artifacts/analysis/phase2_20260327/analysis_bundle_index.json`
  - `artifacts/analysis/phase2_20260327/phase2_analysis_summary.md`
  - `artifacts/analysis/phase2_20260327/campaign_integrity_summary.csv`
  - `artifacts/analysis/phase2_20260327/study_integrity_summary.csv`
  - `artifacts/analysis/phase2_20260327/strategy_mean_summary.csv`
  - `artifacts/analysis/phase2_20260327/selected_config_families.csv`
  - `artifacts/analysis/phase2_20260327/hypothesis_status_summary.csv`
  - `artifacts/analysis/phase2_20260327/claim_table.csv`

## Artifact Integrity

The completed Phase 2 chain is intact and internally consistent.

### Campaign completion

- `gemm_v2_baseline_mapping`: `6/6` jobs complete, `0` failures, terminal status `success`
- `gemm_v2_selector_ablation`: `18/18` jobs complete, `0` failures, terminal status `success`
- `layernorm_v2_regime_studies`: `12/12` jobs complete, `0` failures, terminal status `success`
- `gemm_v2_aligned_reference`: `6/6` jobs complete, `0` failures, terminal status `success`

### Study completion

- `gemm_v2_baseline_mapping`: `run_count=6`, `group_count=1`, complete
- `gemm_v2_selector_ablation`: `run_count=18`, `group_count=3`, complete
- `layernorm_v2_small_regime`: `run_count=6`, `group_count=1`, complete
- `layernorm_v2_large_regime`: `run_count=6`, `group_count=1`, complete
- `gemm_v2_aligned_reference`: `run_count=6`, `group_count=1`, complete

### Reportability and profiling integrity

- all Phase 2 study groups remained reportable
- `compute_lite` and `memory_activity_lite` remained accepted for the Phase 2 studies
- no Phase 2 campaign required a downgrade or partial study reconstruction

## Phase 2 Study Results

### 1. Representative GEMM v2 baseline mapping

Primary artifacts:

- study: `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989`
- summary: `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989/cross_run_summary.json`
- hypotheses: `artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989/hypothesis_results.csv`

Main quantitative result:

- `default_config`: `1.0000x`
- `naive_random_search`: `1.0331x`
- `prune_rank`: `0.8265x`
- `prune_rank_profiled`: `0.8444x`
- `prune_rank_revised`: `0.1458x`

Batch-level hypothesis results:

- `H1_phase2_gemm`: supported
- `H4_phase2_gemm`: unsupported

Mechanism-level interpretation:

- the expanded representative GEMM space preserves the original `H1` story
- compile-ranked selection still fails to reach the best accessible family on representative GEMM
- the strongest reachable family is now the balanced `128x128x64`, `group_size_m=1`, `num_stages=4`, `num_warps=4` config family represented by `cfg_695bff677bfb`
- `prune_rank` and `prune_rank_profiled` stay anchored to smaller `64x64x32` families such as `cfg_cb131d2039b7`
- the current `v3_h4_targeted` revision overcorrects and collapses onto the oversized masked `256x256x32`, `group_size_m=8`, `num_stages=4`, `num_warps=8` family `cfg_24d8f84f938f`

Current implication:

- the compile-frontier problem is still real
- the existing frontier-aware revision is not robust enough for the expanded space

### 2. Representative GEMM v2 selector ablation

Primary artifacts:

- study: `artifacts/studies/gemm_v2_selector_ablation/run_20260327T175823Z_376d6bbc`
- summary: `artifacts/studies/gemm_v2_selector_ablation/run_20260327T175823Z_376d6bbc/cross_run_summary.json`

Main quantitative result:

- parent `prune_rank`: `0.8362x`
- `v3_frontier_only`: `0.1432x`
- full `v3_h4_targeted`: `0.1439x`

Mechanism-level interpretation:

- the failure is already present in frontier construction
- the profile-aware second stage does not rescue the revision once the frontier locks onto the oversized `256x256x32` family
- both `v3_frontier_only` and full `v3_h4_targeted` converge on `cfg_24d8f84f938f`

Current implication:

- the positive `H4` result from the narrower v1 follow-up does not transfer cleanly to the expanded v2 space
- the next GEMM revision, if one is admitted later, must be mask-aware or shape-relative rather than simply more area-seeking

### 3. LayerNorm v2 small-batch regime

Primary artifacts:

- study: `artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba`
- summary: `artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba/cross_run_summary.json`
- hypotheses: `artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba/hypothesis_results.csv`

Main quantitative result:

- `default_config`: `1.0000x`
- `naive_random_search`: `1.0005x`
- `prune_rank`: `1.0100x`
- `prune_rank_profiled`: `1.0113x`
- `prune_rank_revised`: `1.0080x`

Batch-level hypothesis result:

- `H2_small_regime`: unsupported

Interpretation:

- profiling helps slightly on `small_batch`, but the gain over compile-only ranking is only `0.0014`
- the `memory_activity_lite` split clarified that the small-batch story is weakly positive rather than strongly negative
- the selected configs still keep `rows_per_program=1`, so the new knob did not become an active tuning lever in this batch

### 4. LayerNorm v2 large-batch regime

Primary artifacts:

- study: `artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d`
- summary: `artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d/cross_run_summary.json`
- hypotheses: `artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d/hypothesis_results.csv`

Main quantitative result:

- `default_config`: `1.0000x`
- `naive_random_search`: `0.9980x`
- `prune_rank`: `1.0029x`
- `prune_rank_profiled`: `0.9856x`
- `prune_rank_revised`: `0.9964x`

Batch-level hypothesis result:

- `H2_large_regime`: unsupported

Interpretation:

- the regime split exposes a stronger negative result than the pooled LayerNorm analysis did
- on `large_batch`, compile-only ranking is better than the profiled strategy under the current `memory_activity_lite` recipe and selector logic
- the profiled and revised strategies often shift toward the `num_stages=4`, `num_warps=4` family `cfg_e1cb8d966203`, but that does not improve the held-out result

### 5. Aligned GEMM v2 reference

Primary artifacts:

- study: `artifacts/studies/gemm_v2_aligned_reference/run_20260327T190124Z_3a34cdc7`
- summary: `artifacts/studies/gemm_v2_aligned_reference/run_20260327T190124Z_3a34cdc7/cross_run_summary.json`

Main quantitative result:

- `default_config`: `1.0000x`
- `naive_random_search`: `0.9951x`
- `prune_rank`: `0.8795x`
- `prune_rank_profiled`: `0.8873x`
- `prune_rank_revised`: `0.1702x`

Interpretation:

- aligned GEMM remains more flattering than representative GEMM for the compile-ranked selectors
- the contextual `H3` story survives the expanded-space rerun even though it was not re-pre-registered as a separate Phase 2 hypothesis
- `naive_random_search` no longer outperforms the default on aligned GEMM, which further supports the view that aligned GEMM is the easier workload

## Claim-Strength Decisions

### Strong enough to promote now

- `H1` is stronger after Phase 2 than it was before Phase 2
  - the expanded representative GEMM study preserved the core “pruning helps but ranking is weak” result
- the aligned-versus-representative workload contrast remains valid context
  - aligned GEMM still makes the selector ladder look better than representative GEMM
- the pooled LayerNorm story should no longer be used as the primary interpretation
  - the regime split is now the right way to write the LayerNorm result

### No longer safe to promote without qualification

- the earlier narrow-space `H4` success should not be promoted as a general revised-selector win
  - the expanded v2 baseline mapping and the ablation both show that `v3_h4_targeted` does not generalize to the larger GEMM space
- the current LayerNorm profiling recipe should not be written as a general profiling success story
  - `small_batch` is only marginally positive
  - `large_batch` is negative

### Best current paper-safe reading

- cheap compile-derived signals are valuable for pruning but remain insufficient for final representative GEMM ranking, even on the expanded space
- a naive frontier-aware revision can help on a narrower space, but it can also fail catastrophically when the search space grows and masked oversized tiles are admissible
- LayerNorm should now be presented as a regime-aware mixed or negative result, not as one pooled “profiling helps a bit” story

## Documentation And Writing Implications

The completed Phase 2 bundle is sufficient to support:

- a stronger representative GEMM results section
- a clearer aligned-versus-representative workload discussion
- a more rigorous failure-analysis section built around the v2 ablation
- a regime-aware LayerNorm limitations or secondary-results section

The completed Phase 2 bundle does **not** justify:

- treating `v3_h4_targeted` as the final tuner revision
- claiming that profiling currently improves LayerNorm more than GEMM
- claiming that the new LayerNorm knobs are already contributing useful search diversity, because the selected configs stayed at `rows_per_program=1`

## Bounded Next-Step Options

If another execution phase is admitted later, it should be narrow and mechanism-driven.

Most defensible next options:

1. A mask-aware GEMM frontier correction.
   - target the specific Phase 2 failure mode where `v3` overweights oversized masked tiles
   - likely interventions are a shape-relative tile-fit term, a masked-oversize penalty, or both

2. A small LayerNorm explanatory microstudy only if the paper needs a stronger second-kernel section.
   - the main question would be why `large_batch` profiling regresses under `memory_activity_lite`
   - this should be explanatory, not a new broad optimizer-growth phase

Least justified next options:

- adding another broad selector family immediately
- expanding to new kernels before the current Phase 2 findings are written up
- continuing to tune LayerNorm broadly without first identifying one concrete mechanism for the `large_batch` regression
