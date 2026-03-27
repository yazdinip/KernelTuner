# Evidence Registry

Purpose: maintain a structured ledger of what evidence currently exists, what it means, and how much confidence the project should place in it.
Status: Living Registry
Update Rule: update after each completed experiment batch that materially affects interpretation.
Feeds Paper Sections: Results, Discussion, Limitations
Depends On: [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [07_experiment_campaign_plan.md](07_experiment_campaign_plan.md), [10_paper_outline_and_figure_plan.md](10_paper_outline_and_figure_plan.md)

## Registry Rules

- Keep entries concise and cumulative.
- One row should correspond to one coherent body of evidence, not one observation.
- Distinguish clearly between:
  - evidence that exists,
  - interpretation that follows from it,
- and unresolved confounds that still limit the claim.

Current environment policy:

- as of March 27, 2026, `gpunode2` and `gpunode3` are treated as one qualified homogeneous
  `RTX A6000` pool for new primary studies
- historical rows below may still mention earlier `gpunode3` caveats because those were the
  project policy at the time the batches were first recorded

## Current Evidence State

| Evidence ID | Round / Hypothesis | Experiment Config Or Study | Environment | Current Interpretation | Confidence | Unresolved Confounds | Reportable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `E-R0-VAL1` | `R0` measurement validity | `validation_rounds` campaign `run_20260322T234810Z_884986d3`; `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` / `NVIDIA RTX A6000` / CUDA 12.9 stack | the first full validation batch completed successfully; campaign execution, resume, reportability checks, Tier 1 profiling, and study generation all produced usable evidence | Medium | the `validation_phase` study summarizes a selected `9`-run slice from a `15`-job campaign; important first-batch artifacts still live in expiring scratch storage and should be archived or reproduced before paper promotion | Yes |
| `E-R0-PROF-0326` | `R0` profiler revalidation | live `validate-counter-set` revalidation for `gemm_reportable` and `layernorm_reportable` after profiler/reporting integration | `gpunode3` / `NVIDIA RTX A6000` / CUDA 12.9 after explicit CUDA path export | both reportable Tier 1 counter sets validated at `6/6` availability on a fresh A6000 shell; this strengthened operational confidence before long execution | High | this is operational requalification on `gpunode3`, not primary paper evidence for the original `gpunode2` baseline | No |
| `E-R0-G3-REQUAL` | `R0` same-class A6000 requalification | `validation_rounds_g3_requal` campaign `run_20260326T211132Z_0f6bd67a`; `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0` | `gpunode3` / `NVIDIA RTX A6000` / CUDA 12.9 / Nsight Compute 2025.2.1 | the full `gpunode3` requalification block completed with `15/15` jobs and `0` failures; the broad cross-run study reproduced the overall direction of the original validation story and confirmed that the same-class A6000 path is stable enough for targeted follow-up work | High | this is still a `gpunode3` confirmation block, not an automatic replacement for the original `gpunode2` reportable baseline; the broad study still uses the selected-group slicing rules in the study spec | Yes |
| `E-H1-VAL1` | `H1` cheap-signal usefulness | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence supported `H1`: cheap compile signals help with pruning, but do not yet produce a trustworthy final ranking on representative GEMM | Medium | only one original homogeneous batch was registered when this evidence first landed | Yes |
| `E-H1-G3-CONF` | `H1` confirmation | `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0`; `h13_confirmation_g3` study `run_20260326T233133Z_7c560d98` | `gpunode3` same-class A6000 confirmation block | `H1` is now materially stronger: the broad and narrow `gpunode3` batches both show that compile-ranked selectors keep converging on smaller asymmetric GEMM tiles while the best held-out representative GEMM config is the balanced `128x128x32`, `num_stages=4`, `num_warps=4` family found by random search | High | final promotion should still be gated on archival reproduction or a confirming rerun on the original `gpunode2` baseline | Yes |
| `E-H3-VAL1` | `H3` aligned vs representative GEMM | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence supported `H3`: aligned GEMM made the selector ladder look better than the representative workload matrix did | Medium | the original aligned and representative groups were not perfectly paired in the study slice | Yes |
| `E-H3-G3-CONF` | `H3` confirmation | `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0`; `h13_confirmation_g3` study `run_20260326T233133Z_7c560d98` | `gpunode3` same-class A6000 confirmation block | the broad `gpunode3` study again supported `H3`, and the narrower `H1/H3` batch reproduced the same direction: representative GEMM remains meaningfully less flattering than aligned GEMM | Medium | the narrow `h13_confirmation_g3` batch missed the pre-registered `0.02` support margin by a small amount, so this should be treated as a strengthened but not fully closed claim | Yes |
| `E-H2-VAL1` | `H2` profiling value by kernel family | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence did not support `H2`: under the current budget, counter set, and selector logic, profiling did not help LayerNorm more than GEMM | Low | the initial non-support could still have reflected too-weak LayerNorm follow-up or selector use of the counters | Yes |
| `E-H2-G3-FOLLOWUP` | `H2` focused follow-up | `h2_followup_g3` campaign `run_20260326T233138Z_3b4f22f2`; study `run_20260327T001439Z_80ff8355` | `gpunode3` same-class A6000 confirmation block | `H2` again came back unsupported in the focused follow-up: LayerNorm profiling did not outperform the GEMM profiling story under the current matched budget | Medium | this is not yet promotable as a strong negative result because the current LayerNorm `default_config` is not valid across the full representative workload, leaving the `large_batch` primary metrics as `null` in the study summary | Yes |
| `E-H2-G3-CORRECTED` | `H2` corrected focused follow-up | `h2_followup_g3_baselinefix` campaign `run_20260327T021158Z_de62eb5e`; study `run_20260327T025533Z_0d0e6750` | `gpunode3` same-class A6000 confirmation block | after replacing the LayerNorm default with a valid baseline, `H2` still remained unsupported; LayerNorm profiling improved over `prune_rank` only slightly (`1.0430` vs `1.0337`), which was not enough to satisfy the pre-registered margin and still did not produce the intended cross-kernel advantage over GEMM | High | this is now a much stronger negative-result candidate for the current profiling recipe, but it is still a `gpunode3` same-class confirmation result rather than a re-run on the original `gpunode2` baseline | Yes |
| `E-H2-DIAG-G3` | `H2` diagnostic explanation | post-broad diagnostic passes recorded in `artifacts/g3_postbroad_chain_20260326T224436Z.log`; `layernorm_diag_all_calibration_g3`; `layernorm_diag_explicit_shapes_g3` | `gpunode3` diagnostic profiling block | LayerNorm diagnostics suggest the current representative workload spans at least two regimes: `large_batch, hidden=4096` is bandwidth-heavy at about `91%` DRAM throughput, while `small_batch, hidden=4096` is lower-throughput and more long-scoreboard dominated; one memory-only ranking recipe is likely too blunt for both | Medium | the diagnostic runs explain why the current `memory_lite` story is incomplete, but they are not themselves a matched-budget promotable result | No |
| `E-H4-VAL1` | `H4` opportunity-guided revision | original `validation_phase` study `run_20260323T005040Z_99898cc6`, comparing `prune_rank_revised` against `prune_rank` | pinned `gpunode2` reportable batch | first-pass evidence did not support `H4`: the `v2_validation` revised selector did not reliably outperform its parent under unchanged budget | Low | only one revision batch was admitted, and the mechanism of failure was not yet cleanly diagnosed | Yes |
| `E-H4-G3-MECH` | `H4` mechanism diagnosis | broad and focused `gpunode3` GEMM studies: `validation_phase_g3_requal` `run_20260326T224438Z_672398c0` and `h13_confirmation_g3` `run_20260326T233133Z_7c560d98` | `gpunode3` same-class A6000 confirmation block | the current `v2_validation` revision failed for a principled reason: it reranked inside the already-constructed compile frontier, but the representative GEMM winner consistently sat outside that frontier; this mechanism diagnosis was later validated directly by the successful `v3_h4_targeted` retry | High | this is still same-class `gpunode3` evidence rather than a direct rerun on the original pinned baseline host | No |
| `E-H4-G3-V3` | `H4` frontier-aware retry | `h4_retry_g3` campaign `run_20260327T025541Z_2f0e9a5e`; study `run_20260327T035659Z_10f9baec` | `gpunode3` same-class A6000 confirmation block | the frontier-aware `v3_h4_targeted` revision supported `H4`: `prune_rank_revised` reached `1.0996x` geometric-mean speedup vs default, beating the parent `prune_rank` at `0.9666x` by a large `0.1331` margin under unchanged budget; this is the clearest tuner-forward win in the project so far | High | the win is currently demonstrated on representative GEMM only, and final paper promotion still depends on archival or a matching `gpunode2` confirmation policy | Yes |
| `E-CONF-LN-BASELINE` | evaluation confound | original `layernorm_reportable_g3_requal` run family inside `h2_followup_g3`, later corrected by `layernorm_reportable_g3_baselinefix` | `gpunode3` same-class A6000 confirmation block | the historical LayerNorm `default_config` confound was real and materially affected the first focused `H2` follow-up; it has now been resolved by the corrected baseline rerun and should be retained as a methodological lesson rather than an active blocker | High | no active unresolved confound remains on this issue; the row is retained so the paper can explain why the corrected rerun was necessary | No |

## Hypothesis Status Snapshot

| Hypothesis | Current Status | Notes |
| --- | --- | --- |
| `H1` | Strengthened support | supported by the original validation batch and strengthened by the `gpunode3` broad plus focused confirmation studies; the leading mechanism is now frontier-construction failure on representative GEMM |
| `H2` | Repeated non-support on a corrected baseline | the original and focused studies failed to support `H2`, and the corrected `h2_followup_g3_baselinefix` rerun also remained unsupported; this is now a much stronger negative-result candidate for the current LayerNorm profiling recipe |
| `H3` | Broad support, narrow directional confirmation | supported by the broad original and broad `gpunode3` studies; the narrower confirmation batch reproduced the direction but missed the pre-registered margin slightly |
| `H4` | Supported by the frontier-aware representative GEMM retry | the initial revised selector failed, but the frontier-aware `v3_h4_targeted` retry supported `H4` with a large matched-budget gain over the current selector on representative GEMM |

## Current Next Evidence Targets

- Phase 2 representative GEMM v2 baseline mapping on the expanded space
- Phase 2 representative GEMM selector ablation isolating frontier construction versus profile-aware reranking
- Phase 2 LayerNorm regime-separated studies using `memory_activity_lite`

## Evidence Source Notes

- The completed `gpunode3` execution block is real research evidence, not only tooling smoke testing.
- The broad `gpunode3` source is:
  - campaign: `validation_rounds_g3_requal` `run_20260326T211132Z_0f6bd67a`
  - study: `validation_phase_g3_requal` `run_20260326T224438Z_672398c0`
- The focused `gpunode3` sources are:
  - `h13_confirmation_g3` study `run_20260326T233133Z_7c560d98`
  - `h2_followup_g3` study `run_20260327T001439Z_80ff8355`
- The corrected follow-up sources are:
  - `h2_followup_g3_baselinefix` study `run_20260327T025533Z_0d0e6750`
  - `h4_retry_g3` study `run_20260327T035659Z_10f9baec`
- The detailed chronological record for the full `gpunode3` block should be maintained in a dated log entry under `logs/`.
- The detailed chronological record for the corrected follow-up block should also be maintained in a dated log entry under `logs/`.
- Batch-level study outputs remain the automated result source.
- This registry remains the authoritative place to assign project-level confidence and next actions.

## Promotion Rule

Evidence should only be promoted into the paper backbone when:

- the relevant round exit gate has been passed,
- the evidence is marked reportable or explicitly diagnostic in the registry,
- the interpretation survives at least one repeated or cross-run check appropriate to the claim,
- and no unresolved confound is still blocking the intended paper claim.
