# gpunode3 Requalification And Follow-up Execution

Purpose: record the completed long `gpunode3` execution block, including the broad requalification batch, the focused `H1/H3` and `H2` follow-up studies, the LayerNorm diagnostic profiling passes, and the resulting next-step decisions.
Status: Log
Update Rule: append-only; do not rewrite past observations except to fix factual errors.
Feeds Paper Sections: none directly; this is chronological support material for the evidence registry and later paper synthesis.
Depends On: [../07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md), [../08_evidence_registry.md](../08_evidence_registry.md), [../09_opportunity_log.md](../09_opportunity_log.md)

## Environment

- node: `gpunode3`
- GPU: `NVIDIA RTX A6000`
- CUDA: `12.9`
- Nsight Compute: `2025.2.1`
- allocation: Slurm job `86379`
- execution mode: same-class A6000 requalification and follow-up, not automatic replacement for the original `gpunode2` reportable baseline

## Completed Execution Chain

### 1. Broad same-class requalification

- campaign: `validation_rounds_g3_requal`
- campaign run: `run_20260326T211132Z_0f6bd67a`
- location: `artifacts/campaigns/validation_rounds_g3_requal/run_20260326T211132Z_0f6bd67a`
- terminal status: `success`
- completed jobs: `15/15`
- failed jobs: `0`

Generated broad study outputs:

- study: `validation_phase_g3_requal`
- study run: `run_20260326T224438Z_672398c0`
- location: `artifacts/studies/validation_phase_g3_requal/run_20260326T224438Z_672398c0`

Broad batch-level hypothesis results:

- `H1`: supported
- `H2`: unsupported
- `H3`: supported
- `H4`: unsupported

### 2. Focused `H1/H3` confirmation

- campaign: `h13_confirmation_g3`
- campaign run: `run_20260326T224446Z_9657072e`
- location: `artifacts/campaigns/h13_confirmation_g3/run_20260326T224446Z_9657072e`
- terminal status: `success`
- completed jobs: `12/12`
- failed jobs: `0`

Generated focused study outputs:

- study: `h13_confirmation_g3`
- study run: `run_20260326T233133Z_7c560d98`
- location: `artifacts/studies/h13_confirmation_g3/run_20260326T233133Z_7c560d98`

Focused batch-level hypothesis results:

- `H1`: supported
- `H3`: unsupported by the pre-registered threshold, but the effect direction still matched the broader studies

### 3. Focused `H2` follow-up

- campaign: `h2_followup_g3`
- campaign run: `run_20260326T233138Z_3b4f22f2`
- location: `artifacts/campaigns/h2_followup_g3/run_20260326T233138Z_3b4f22f2`
- terminal status: `success`
- completed jobs: `12/12`
- failed jobs: `0`

Generated focused study outputs:

- study: `h2_followup_g3`
- study run: `run_20260327T001439Z_80ff8355`
- location: `artifacts/studies/h2_followup_g3/run_20260327T001439Z_80ff8355`

Focused batch-level hypothesis result:

- `H2`: unsupported

### 4. Post-follow-up LayerNorm diagnostics

Executed through the chained log:

- log: `artifacts/g3_postbroad_chain_20260326T224436Z.log`
- chain completed at: `2026-03-27T00:16:06Z`

Diagnostic experiment specs:

- `configs/experiments/layernorm_diag_all_calibration_g3.yaml`
- `configs/experiments/layernorm_diag_explicit_shapes_g3.yaml`

Both diagnostics completed successfully through the CLI `generate-configs`, `collect-signals`, and `profile` stages.

## High-Level Result Summary

### Hypothesis status after the completed `gpunode3` block

| Hypothesis | Broad g3 status | Focused g3 status | Working interpretation |
| --- | --- | --- | --- |
| `H1` | supported | supported | strengthened |
| `H2` | unsupported | unsupported | repeated non-support, but still not promotable as a strong negative because of a LayerNorm baseline confound |
| `H3` | supported | narrow follow-up missed support threshold but matched direction | strengthened directionally, not fully closed |
| `H4` | unsupported | not rerun as a new revision batch | still non-support, now with a clearer mechanism-level explanation |

### Strongest current result

The strongest current result is representative GEMM, not LayerNorm.

- The stable representative GEMM winner remains `cfg_ccbf6a0142ec`.
- The current selector family rarely reaches that family under the matched benchmark budget.
- This is now a repeatable finding across the broad and focused `gpunode3` GEMM runs.

### Most important evaluation constraint

Aligned GEMM remains useful as a reference workload, but it is materially more flattering than the representative GEMM matrix and should not be treated as the primary truth source for tuner quality.

## Detailed GEMM Findings

### Stable winner family

Across the completed `gpunode3` GEMM batches:

- `naive_random_search` repeatedly selected `cfg_ccbf6a0142ec`
- that family won consistently enough to become the most important reference point for the current GEMM story

The key practical meaning is:

- the current selector is not mostly losing because it cannot choose among nearly identical finalists
- it is mostly losing because the correct config family is not reliably admitted into the benchmarked frontier

### Current selector behavior

The current compile-ranked selector family repeatedly converged on smaller asymmetric tile families such as:

- `cfg_72eefb2e03cf`
- `cfg_bbbcabc7810a`
- and, less often, `cfg_69cc70c0f246` or `cfg_14169369ef57`

Observed pattern:

- `prune_rank`, `prune_rank_profiled`, and `prune_rank_revised` are often stable in the wrong region
- `prune_rank_profiled` sometimes improves small local choices inside the frontier, but it does not solve the broader frontier-construction problem
- the current `v2_validation` revision changes late-stage ranking behavior more than early frontier construction

### Workload-class behavior

Representative GEMM remains the more difficult and more meaningful matrix.

- `edge_nondivisible`: current selector family is clearly weaker than the stable random-search winner
- `m_dominant`: current selector family sometimes reaches near-baseline or slightly better behavior, but still trails the stable random-search winner materially
- `n_dominant`: current selectors are closer to baseline but still below the stable random-search winner
- `square_compute`: current selectors are near baseline or below, while the stable random-search winner remains clearly better

Aligned GEMM continues to look better overall:

- `prune_rank_revised` can look acceptable or slightly positive on aligned GEMM
- that improvement does not transfer cleanly to the representative matrix

## Detailed LayerNorm Findings

### Focused `H2` follow-up result

The `H2` follow-up again did not support the idea that matched-budget profiling helped more on LayerNorm than on GEMM.

However, the current LayerNorm result is not ready for hard promotion as a negative result because the workload/baseline contract still has a real confound:

- the declared kernel default in `configs/kernels/layernorm.yaml` is `block_size=1024`
- the representative LayerNorm workload includes `hidden=4096`
- the resulting study summary therefore shows `null` primary metrics for the `large_batch` LayerNorm group in the cross-run summary

Practical meaning:

- the current LayerNorm result is informative
- but it is not yet clean enough to close `H2` strongly

### Diagnostic profiling result

The post-follow-up LayerNorm diagnostics made the signal story much clearer.

On `hidden=4096`:

- `rows=2048` behaved like a bandwidth-heavy case
  - DRAM throughput near `91%`
  - lower long-scoreboard stall than the small-batch case
- `rows=128` behaved more like a latency-sensitive case
  - much lower throughput, around `35%`
  - higher long-scoreboard stall

Interpretation:

- the current representative LayerNorm workload is not one single memory-bound regime
- the current `memory_lite` signal recipe is likely too coarse to drive one clean ranking rule across both workload classes

## What The Current Results Mean For The Tuner

### Current selector weakness

The main current GEMM weakness is now clearly:

- frontier construction, not only late reranking

This matters because:

- profiling cannot rescue a winner that never enters the profiled prefix
- another profile-only revision would likely repeat the same mistake as `v2_validation`

### Current LayerNorm weakness

The main current LayerNorm weakness is now twofold:

- the baseline contract is partially invalid on the representative workload
- even after that is fixed, the workload likely needs workload-class-aware interpretation or a slightly richer signal set

### Current study-wide conclusion

The project now has a strong research-platform result and at least one strong tuner result:

- the platform can execute and compare broad and narrow live campaigns successfully
- representative GEMM already yields a clear paper-grade insight about the limits of compile-only frontier construction

The weaker part of the story is still LayerNorm:

- useful
- instructive
- but not yet promotable as a clean profiling success or clean profiling failure

## Immediate Next Actions

The next rerun cycle should be:

1. repair the LayerNorm default baseline so the representative workload is fully valid
2. create one frontier-aware `v3` GEMM selector revision that attacks the frontier-construction miss directly
3. run a stricter stratified LayerNorm diagnostic microstudy
4. rerun the narrow reportable studies after steps 1 and 2

Those next actions are recorded more concisely in:

- [../07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md)
- [../08_evidence_registry.md](../08_evidence_registry.md)
- [../09_opportunity_log.md](../09_opportunity_log.md)
