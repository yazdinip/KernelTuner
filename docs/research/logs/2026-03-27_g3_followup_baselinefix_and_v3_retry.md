# gpunode3 Follow-up Baseline Fix And Frontier-Aware Retry

Purpose: record the corrected March 27, 2026 follow-up cycle on `gpunode3`, including the resolved LayerNorm baseline confound, the corrected `H2` rerun, the regime diagnostic microstudy, and the successful frontier-aware `H4` retry.
Status: Log
Update Rule: append-only; do not rewrite past observations except to fix factual errors.
Feeds Paper Sections: none directly; this is chronological support material for the evidence registry and paper-figure sourcing.
Depends On: [../07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md), [../08_evidence_registry.md](../08_evidence_registry.md), [../09_opportunity_log.md](../09_opportunity_log.md), [../10_paper_outline_and_figure_plan.md](../10_paper_outline_and_figure_plan.md)

## Environment And Execution Root

- node: `gpunode3`
- GPU: `NVIDIA RTX A6000`
- CUDA: `12.9`
- Nsight Compute: `2025.2.1`
- allocation: Slurm job `86379`
- frozen execution snapshot: `/u/yazdinip/KernelTuner_followup_20260327T020517Z`
- launcher script: `scripts/run_g3_followup_cycle.sh`
- execution mode at run time: same-hardware A6000 corrective follow-up

Later policy note:

- the current repo policy treats `gpunode2` and `gpunode3` as one homogeneous `RTX A6000` pool
- the `gpunode3` wording below is retained as execution provenance, not as an active limitation on using these results in the current project phase

## Completed Follow-up Chain

### 1. LayerNorm regime diagnostic microstudy

- experiment: `layernorm_diag_regimes_g3`
- run: `run_20260327T020730Z_e2949d63`
- location: `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/layernorm_diag_regimes_g3/run_20260327T020730Z_e2949d63`
- terminal status: `success`

Selected-config summary:

- `prune_rank`: `cfg_3b0923297f97`
- `prune_rank_profiled`: `cfg_3b0923297f97`
- `prune_rank_revised`: `cfg_3b0923297f97`
- `default_config`: `cfg_64f96da0f961`
- `naive_grid_search`: `cfg_64f96da0f961`

Working interpretation:

- the regime-diagnostic kernel space was cleanly executable on the live A6000 stack
- the microstudy preserved the earlier conclusion that LayerNorm should be interpreted as at least two regimes rather than one uniform memory-bound case

### 2. Corrected `H2` rerun with a valid LayerNorm default baseline

- campaign: `h2_followup_g3_baselinefix`
- campaign run: `run_20260327T021158Z_de62eb5e`
- location: `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/campaigns/h2_followup_g3_baselinefix/run_20260327T021158Z_de62eb5e`
- terminal status: `success`
- completed jobs: `12/12`
- failed jobs: `0`

Generated study outputs:

- study: `h2_followup_g3_baselinefix`
- study run: `run_20260327T025533Z_0d0e6750`
- location: `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h2_followup_g3_baselinefix/run_20260327T025533Z_0d0e6750`

Batch-level hypothesis result:

- `H2`: unsupported

Evidence string from the automated study result:

- LayerNorm `prune_rank_profiled` vs `prune_rank`: `1.0430` vs `1.0337`, observed delta `0.0093`
- GEMM `prune_rank_profiled` vs `prune_rank`: `0.9785` vs `0.9826`, observed delta `-0.0041`

Working interpretation:

- the LayerNorm default-baseline confound was removed successfully
- profiling still helped LayerNorm only slightly under the current matched budget
- the corrected result is now a much stronger negative-result candidate for the current `memory_lite` plus selector recipe

### 3. Frontier-aware `H4` retry

- campaign: `h4_retry_g3`
- campaign run: `run_20260327T025541Z_2f0e9a5e`
- location: `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/campaigns/h4_retry_g3/run_20260327T025541Z_2f0e9a5e`
- terminal status: `success`
- completed jobs: `12/12`
- failed jobs: `0`

Generated study outputs:

- study: `h4_retry_g3`
- study run: `run_20260327T035659Z_10f9baec`
- location: `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec`

Batch-level hypothesis result:

- `H4`: supported

Evidence string from the automated study result:

- frontier-aware `prune_rank_revised`: `1.0996`
- parent `prune_rank`: `0.9666`
- observed delta: `0.1331`

Working interpretation:

- the most important representative GEMM weakness really was frontier construction
- the new `v3_h4_targeted` revision succeeded because it changed which configs entered the benchmarked frontier before profiling
- this is currently the clearest tuner-forward win in the project

## Summary Of What Changed Because Of This Follow-up Cycle

### LayerNorm

- the baseline-validity problem is no longer an active blocker
- `H2` still remained unsupported after the fix
- the current matched-budget LayerNorm profiling story is therefore weaker than originally expected, and should currently be written as either a careful negative result or a regime-dependent limitation

### GEMM

- the `H4` retry validated the earlier mechanism diagnosis
- the successful revision did not require more profiling complexity or a larger benchmark budget
- it required a better compile-frontier construction rule for representative GEMM

## Strongest Artifacts From This Cycle

- corrected `H2` study summary:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h2_followup_g3_baselinefix/run_20260327T025533Z_0d0e6750/cross_run_summary.json`
- corrected `H2` hypothesis table:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h2_followup_g3_baselinefix/run_20260327T025533Z_0d0e6750/hypothesis_results.csv`
- supported `H4` study summary:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec/cross_run_summary.json`
- supported `H4` hypothesis table:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec/hypothesis_results.csv`
- supported `H4` stability report:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec/stability_report.csv`
- supported `H4` evidence bundle:
  - `/u/yazdinip/KernelTuner_followup_20260327T020517Z/artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec/evidence_bundle.json`

## What This Log Unlocks For Writing

- The project now has one corrected negative result path:
  - LayerNorm profiling under the current budget and `memory_lite` recipe did not produce the intended cross-kernel advantage, even after fixing the default baseline.
- The project now has one clear positive revised-selector path:
  - a frontier-aware GEMM revision materially improved held-out performance under unchanged budget.
- The strongest write-up direction is no longer “can the profiler help at all?”
  - it is “what can cheap signals do, where do they fail, and how can an opportunity-guided frontier revision repair the main representative GEMM miss?”

## Next Actions After This Follow-up Cycle

1. Archive the strongest `gpunode3` artifacts into a stable location that is clearly referenced from the research docs.
2. Decide whether to:
   - rerun the strongest claims on `gpunode2`, or
   - formally promote `gpunode2` and `gpunode3` as one homogeneous `RTX A6000` pool.
3. Generate paper-facing figures from:
   - `validation_phase_g3_requal`
   - `h13_confirmation_g3`
   - `h2_followup_g3_baselinefix`
   - `h4_retry_g3`
4. Defer any broad new tuner growth until the writing phase exposes a concrete evidence gap.
