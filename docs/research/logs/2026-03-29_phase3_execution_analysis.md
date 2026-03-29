# 2026-03-29 Phase 3 Execution Analysis

Purpose: freeze the canonical Phase 3 evidence set, record the replication set, and promote the completed bounded R5 interpretation into the research layer.

## Summary

The bounded Phase 3 execution program is complete and scientifically interpretable.

Main outcomes:

- `H5` is `unsupported`.
- `H1` remains strong overall, but Phase 3 only reinforces it qualitatively rather than as a new threshold-clearing support batch.
- `H3` remains historically supported, but Phase 3 does not strengthen it.
- `H4` is now more clearly a transfer-limited story rather than a simple revised-selector success.
- `split_k` should be retired from the main GEMM reportable surface.
- `rows_per_program` should be retired from the main LayerNorm reportable surface.
- no explicit Phase 3 rerun gate was triggered.

## Canonical Phase 3 Evidence Set

Primary studies used for project-level Phase 3 interpretation:

- `gemm_v3_baseline_mapping`: `run_20260329T010211Z_dfb53abb`
- `gemm_v3_selector_ablation`: `run_20260329T034953Z_e8b8ac98`
- `gemm_v3_schedule_diag`: `run_20260328T212649Z_7755304a`
- `gemm_v3_aligned_reference`: `run_20260329T045530Z_7086b0e7`
- `layernorm_v2_small_microstudy`: `run_20260329T053448Z_7c6e5dc1`
- `layernorm_v2_large_microstudy`: `run_20260329T053455Z_c4118a25`

Canonical reusable artifact bundle:

- `artifacts/analysis/phase3_20260329/`

Why this set is canonical:

- these are the latest completed confirmation studies for the bounded Phase 3 program
- they were produced after the Phase 3 remainder wave completed cleanly
- they match the current homogeneous `RTX A6000` pool policy
- they are accompanied by the reusable integrity and claim bundle under `artifacts/analysis/phase3_20260329/`

## Replication Evidence Set

Earlier main Phase 3 studies retained as replication or consistency evidence:

- `gemm_v3_baseline_mapping`: `run_20260328T010058Z_7226d3f1`
- `gemm_v3_selector_ablation`: `run_20260328T034306Z_5055e181`
- `gemm_v3_aligned_reference`: `run_20260328T223319Z_7cada93b`
- `layernorm_v2_small_microstudy`: `run_20260328T231251Z_29646063`
- `layernorm_v2_large_microstudy`: `run_20260328T231256Z_847b98a5`

Use these runs to assess consistency, not as the headline rows for new claims.

## Artifact Integrity

The canonical Phase 3 bundle confirms:

- all canonical and replication campaigns reached `terminal_status=success`
- all promoted canonical studies have `cross_run_summary.json`
- the diagnostic-only schedule study is complete under the diagnostic contract rather than the held-out reportable contract
- no incomplete Phase 3 campaign roots are part of the promoted evidence set

Source:

- `artifacts/analysis/phase3_20260329/campaign_integrity_summary.csv`
- `artifacts/analysis/phase3_20260329/study_integrity_summary.csv`
- `artifacts/analysis/phase3_20260329/canonical_artifact_map.csv`

## Scientific Interpretation

### H5

`H5` is `unsupported`.

Canonical representative GEMM v3 evidence:

- `v4_transfer_safe_profiled`: `0.1609x` vs default
- parent `prune_rank`: `1.0324x` vs default
- `naive_random_search`: `1.0427x` vs default

This is far from the pre-registered success rule, not a near-threshold miss.

Source:

- `artifacts/studies/gemm_v3_baseline_mapping/run_20260329T010211Z_dfb53abb/hypothesis_results.csv`
- `artifacts/analysis/phase3_20260329/claim_table.csv`

### H5 failure mode

The transfer-safe corrective pass did not fail because profiling was absent. It failed because both frontier-only and profiled-v4 collapsed to the wrong family on the expanded representative GEMM space.

Canonical ablation evidence:

- parent `prune_rank`: `0.9692x` vs default
- `v4_transfer_safe_frontier`: `0.1622x` vs default
- `v4_transfer_safe_profiled`: `0.1623x` vs default

Source:

- `artifacts/studies/gemm_v3_selector_ablation/run_20260329T034953Z_e8b8ac98/cross_run_summary.json`
- `artifacts/analysis/phase3_20260329/claim_table.csv`

### H3 context

Phase 3 did not strengthen the earlier aligned-vs-representative story.

Canonical `prune_rank` means:

- representative GEMM v3: `1.0324x`
- aligned GEMM v3: `1.0158x`

This does not overturn the broader earlier `H3` evidence, but it does mean Phase 3 should not be written as another clean aligned-overstates-representative confirmation.

### LayerNorm

LayerNorm remains a bounded explanatory thread.

Canonical microstudy evidence:

- `small_batch`
  - `prune_rank`: `0.9721x`
  - `prune_rank_profiled`: `1.0013x`
- `large_batch`
  - `prune_rank`: `1.0149x`
  - `prune_rank_profiled`: `0.9971x`

Interpretation:

- `small_batch` is weak and noisy
- `large_batch` favors compile-only ranking
- the project should not reopen a major LayerNorm optimization direction on this evidence

### Keep / drop decisions

`split_k`

- diagnostic frontier rows show non-unit `split_k` as reachable
- canonical chosen and best-scored families remain `split_k=1`
- decision: retire `split_k` from the main GEMM reportable surface

`rows_per_program`

- non-unit values appear only in weak or regressing LayerNorm paths
- no robust selector-level gain depends on the knob
- decision: retire `rows_per_program` from the main LayerNorm reportable surface

## Rerun Gate Evaluation

Gate A: main vs confirmation contradiction

- not triggered
- `H5` stayed unsupported in both the earlier main run and the canonical confirmation run
- `H1_phase3_gemm` changed batch label from `supported` to `unsupported`, but the claim direction did not flip

Gate B: unstable `H5`

- not triggered
- the canonical result is far from the success threshold

Gate C: schedule-family ambiguity

- not triggered
- `split_k` appears only as a dominated frontier alternative and never survives into chosen or best-scored canonical GEMM families

Gate D: LayerNorm keep/drop ambiguity

- not triggered
- `rows_per_program` is weak enough to retire without a tie-break rerun

Result:

- no bounded 12-hour A6000 rerun is required by the explicit Phase 3 gates

## Documentation Promotion Decision

The research backbone should now state:

- `H5` is evaluated and `unsupported`
- Phase 3 is promoted, not pending
- `split_k` is retired from the main GEMM surface
- `rows_per_program` is retired from the main LayerNorm surface
- the next phase is synthesis and writing support, not another exploratory expansion
