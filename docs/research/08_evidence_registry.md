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
- historical rows may still retain node-specific provenance, but current project-level
  interpretation treats both nodes as one homogeneous `RTX A6000` pool

Current promotion boundary:

- the completed bounded Phase 3 execution program is now promoted in this registry
- the completed bounded `R6` final-mainline program is now also promoted
- the canonical confirmation studies remain the primary Phase 3 evidence set
- the canonical `R6` studies are:
  - `gemm_final_baseline_mapping` `run_20260330T014317Z_359c1904`
  - `gemm_final_selector_ablation` `run_20260330T023529Z_7c800187`
- the optional `R6` aligned refresh and confirmation reruns were skipped by gate and are therefore not missing evidence
- the earlier main Phase 3 studies are retained as replication evidence
- no incomplete Phase 3 or `R6` campaign roots are part of the promoted evidence set

## Current Evidence State

| Evidence ID | Round / Hypothesis | Experiment Config Or Study | Environment | Current Interpretation | Confidence | Unresolved Confounds | Reportable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `E-R0-VAL1` | `R0` measurement validity | `validation_rounds` campaign `run_20260322T234810Z_884986d3`; `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` / `NVIDIA RTX A6000` / CUDA 12.9 stack | the first full validation batch completed successfully; campaign execution, resume, reportability checks, Tier 1 profiling, and study generation all produced usable evidence | Medium | the `validation_phase` study summarizes a selected `9`-run slice from a `15`-job campaign; important first-batch artifacts still live in expiring scratch storage and should be archived or reproduced before paper promotion | Yes |
| `E-R0-PROF-0326` | `R0` profiler revalidation | live `validate-counter-set` revalidation for `gemm_reportable` and `layernorm_reportable` after profiler/reporting integration | `gpunode3` / `NVIDIA RTX A6000` / CUDA 12.9 after explicit CUDA path export | both reportable Tier 1 counter sets validated at `6/6` availability on a fresh A6000 shell; this strengthened operational confidence before long execution | High | this is operational requalification rather than a comparative speedup study, but it is fully relevant to the qualified A6000 pool | No |
| `E-R0-G3-REQUAL` | `R0` homogeneous A6000 requalification | `validation_rounds_g3_requal` campaign `run_20260326T211132Z_0f6bd67a`; `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0` | `gpunode3` / `NVIDIA RTX A6000` / CUDA 12.9 / Nsight Compute 2025.2.1 | the full `gpunode3` requalification block completed with `15/15` jobs and `0` failures; the broad cross-run study reproduced the overall direction of the original validation story and confirmed that the homogeneous A6000 pool is stable enough for targeted follow-up work | High | the broad study still uses the selected-group slicing rules in the study spec | Yes |
| `E-H1-VAL1` | `H1` cheap-signal usefulness | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence supported `H1`: cheap compile signals help with pruning, but do not yet produce a trustworthy final ranking on representative GEMM | Medium | only one original homogeneous batch was registered when this evidence first landed | Yes |
| `E-H1-G3-CONF` | `H1` confirmation | `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0`; `h13_confirmation_g3` study `run_20260326T233133Z_7c560d98` | `gpunode3` / `NVIDIA RTX A6000` | `H1` is now materially stronger: the broad and narrow `gpunode3` batches both show that compile-ranked selectors keep converging on smaller asymmetric GEMM tiles while the best held-out representative GEMM config is the balanced `128x128x32`, `num_stages=4`, `num_warps=4` family found by random search | High | no active node-class confound remains under the current homogeneous A6000-pool policy | Yes |
| `E-H3-VAL1` | `H3` aligned vs representative GEMM | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence supported `H3`: aligned GEMM made the selector ladder look better than the representative workload matrix did | Medium | the original aligned and representative groups were not perfectly paired in the study slice | Yes |
| `E-H3-G3-CONF` | `H3` confirmation | `validation_phase_g3_requal` study `run_20260326T224438Z_672398c0`; `h13_confirmation_g3` study `run_20260326T233133Z_7c560d98` | `gpunode3` / `NVIDIA RTX A6000` | the broad `gpunode3` study again supported `H3`, and the narrower `H1/H3` batch reproduced the same direction: representative GEMM remains meaningfully less flattering than aligned GEMM | Medium | the narrow `h13_confirmation_g3` batch missed the pre-registered `0.02` support margin by a small amount, so this should be treated as a strengthened but not fully closed claim | Yes |
| `E-H2-VAL1` | `H2` profiling value by kernel family | original `validation_phase` study `run_20260323T005040Z_99898cc6` | pinned `gpunode2` reportable batch | first-pass evidence did not support `H2`: under the current budget, counter set, and selector logic, profiling did not help LayerNorm more than GEMM | Low | the initial non-support could still have reflected too-weak LayerNorm follow-up or selector use of the counters | Yes |
| `E-H2-G3-FOLLOWUP` | `H2` focused follow-up | `h2_followup_g3` campaign `run_20260326T233138Z_3b4f22f2`; study `run_20260327T001439Z_80ff8355` | `gpunode3` / `NVIDIA RTX A6000` | `H2` again came back unsupported in the focused follow-up: LayerNorm profiling did not outperform the GEMM profiling story under the current matched budget | Medium | this early focused follow-up still contained the later-resolved LayerNorm default-baseline confound, so it should be read mainly as historical lead-in to the corrected and regime-split studies | Yes |
| `E-H2-G3-CORRECTED` | `H2` corrected focused follow-up | `h2_followup_g3_baselinefix` campaign `run_20260327T021158Z_de62eb5e`; study `run_20260327T025533Z_0d0e6750` | `gpunode3` / `NVIDIA RTX A6000` | after replacing the LayerNorm default with a valid baseline, `H2` still remained unsupported; LayerNorm profiling improved over `prune_rank` only slightly (`1.0430` vs `1.0337`), which was not enough to satisfy the pre-registered margin and still did not produce the intended cross-kernel advantage over GEMM | High | this is a negative-result candidate for the current profiling recipe, but the later regime-split v2 studies now provide the cleaner LayerNorm interpretation | Yes |
| `E-H2-DIAG-G3` | `H2` diagnostic explanation | post-broad diagnostic passes recorded in `artifacts/g3_postbroad_chain_20260326T224436Z.log`; `layernorm_diag_all_calibration_g3`; `layernorm_diag_explicit_shapes_g3` | `gpunode3` diagnostic profiling block | LayerNorm diagnostics suggest the current representative workload spans at least two regimes: `large_batch, hidden=4096` is bandwidth-heavy at about `91%` DRAM throughput, while `small_batch, hidden=4096` is lower-throughput and more long-scoreboard dominated; one memory-only ranking recipe is likely too blunt for both | Medium | the diagnostic runs explain why the current `memory_lite` story is incomplete, but they are not themselves a matched-budget promotable result | No |
| `E-H4-VAL1` | `H4` opportunity-guided revision | original `validation_phase` study `run_20260323T005040Z_99898cc6`, comparing `prune_rank_revised` against `prune_rank` | pinned `gpunode2` reportable batch | first-pass evidence did not support `H4`: the `v2_validation` revised selector did not reliably outperform its parent under unchanged budget | Low | only one revision batch was admitted, and the mechanism of failure was not yet cleanly diagnosed | Yes |
| `E-H4-G3-MECH` | `H4` mechanism diagnosis | broad and focused `gpunode3` GEMM studies: `validation_phase_g3_requal` `run_20260326T224438Z_672398c0` and `h13_confirmation_g3` `run_20260326T233133Z_7c560d98` | `gpunode3` / `NVIDIA RTX A6000` | the current `v2_validation` revision failed for a principled reason: it reranked inside the already-constructed compile frontier, but the representative GEMM winner consistently sat outside that frontier; this mechanism diagnosis was later validated directly by the successful `v3_h4_targeted` retry | High | this is a mechanism row, and the later Phase 2 studies show that the frontier rule itself still needed better transfer behavior | No |
| `E-H4-G3-V3` | `H4` frontier-aware retry | `h4_retry_g3` campaign `run_20260327T025541Z_2f0e9a5e`; study `run_20260327T035659Z_10f9baec` | `gpunode3` / `NVIDIA RTX A6000` | the frontier-aware `v3_h4_targeted` revision supported `H4`: `prune_rank_revised` reached `1.0996x` geometric-mean speedup vs default, beating the parent `prune_rank` at `0.9666x` by a large `0.1331` margin under unchanged budget; this remains the clearest narrow-space tuner-forward win in the project | High | this row now needs to be read together with the later Phase 2 v2 transfer failure, not as a final universal revised-selector success | Yes |
| `E-P2-INTEGRITY` | `R4` Phase 2 artifact integrity | Phase 2 deepening cycle `phase2_deepening_cycle_20260327T155853Z`; analysis bundle `artifacts/analysis/phase2_20260327/` | qualified homogeneous `RTX A6000` pool | the completed Phase 2 chain is internally consistent: all four campaigns finished successfully, all five studies emitted their full report sets, and the reusable analysis bundle captures campaign integrity, study integrity, strategy means, config-family snapshots, and claim summaries | High | this row only proves completeness and provenance, not scientific direction by itself | No |
| `E-H1-P2-V2` | `H1` expanded-space representative GEMM | `gemm_v2_baseline_mapping` campaign `run_20260327T155909Z_11e2551b`; study `run_20260327T164637Z_0403b989` | qualified homogeneous `RTX A6000` pool | `H1` stayed supported on the expanded representative GEMM space: `naive_random_search` reached `1.0331x` vs default while `prune_rank` stayed at `0.8265x`; the enlarged space therefore strengthens the conclusion that cheap compile-ranked selection still misses the best reachable held-out family | High | the strongest winner is still delivered by `naive_random_search`, not by a deterministic revised selector | Yes |
| `E-H4-P2-V2` | `H4` expanded-space representative GEMM | `gemm_v2_baseline_mapping` study `run_20260327T164637Z_0403b989`; `gemm_v2_selector_ablation` study `run_20260327T175823Z_376d6bbc` | qualified homogeneous `RTX A6000` pool | the earlier narrow-space `v3_h4_targeted` win did not generalize to the expanded v2 space: `prune_rank_revised` collapsed to `0.1458x` vs default in the baseline mapping study, and the ablation showed that both `v3_frontier_only` (`0.1432x`) and full `v3_h4_targeted` (`0.1439x`) fail for the same reason | High | this is a controlled expanded-space result rather than a direct contradiction of the earlier narrow-space win; the correct project-level reading is now “mixed transfer” rather than simple support or rejection | Yes |
| `E-H2-P2-SMALL` | `H2` LayerNorm small-batch regime | `layernorm_v2_small_regime` study `run_20260327T183157Z_53565cba` | qualified homogeneous `RTX A6000` pool | the small-batch LayerNorm regime remained unsupported as a strong profiling win: `prune_rank_profiled` improved only slightly over `prune_rank` (`1.0113x` vs `1.0100x`), far below the pre-registered `+0.02` margin | Medium | the result is directionally positive but very small, so it should be written as a marginal or weak regime rather than a true profiling success | Yes |
| `E-H2-P2-LARGE` | `H2` LayerNorm large-batch regime | `layernorm_v2_large_regime` study `run_20260327T183158Z_37695a2d` | qualified homogeneous `RTX A6000` pool | the large-batch LayerNorm regime is currently a stronger negative result: `prune_rank` reached `1.0029x` vs default while `prune_rank_profiled` regressed to `0.9856x`; the regime split therefore clarifies that the current profiling recipe is not helping uniformly across LayerNorm workloads | High | the mechanism behind the large-batch regression is still explanatory work rather than settled fact | Yes |
| `E-H3-P2-CONTEXT` | `H3` expanded-space context | `gemm_v2_baseline_mapping` study `run_20260327T164637Z_0403b989`; `gemm_v2_aligned_reference` study `run_20260327T190124Z_3a34cdc7` | qualified homogeneous `RTX A6000` pool | aligned GEMM remained more flattering than representative GEMM for the compile-ranked selectors in Phase 2: for `prune_rank`, representative GEMM averaged `0.8265x` vs default while aligned GEMM averaged `0.8795x`; the same directional effect held for `prune_rank_profiled` | Medium | this is contextual Phase 2 evidence, not a separately re-pre-registered hypothesis row | Yes |
| `E-CONF-LN-BASELINE` | evaluation confound | original `layernorm_reportable_g3_requal` run family inside `h2_followup_g3`, later corrected by `layernorm_reportable_g3_baselinefix` | `gpunode3` / `NVIDIA RTX A6000` | the historical LayerNorm `default_config` confound was real and materially affected the first focused `H2` follow-up; it has now been resolved by the corrected baseline rerun and should be retained as a methodological lesson rather than an active blocker | High | no active unresolved confound remains on this issue; the row is retained so the paper can explain why the corrected rerun was necessary | No |
| `E-P3-READY` | `R5` implementation readiness | Phase 3 implementation pass on top of the completed Phase 2 baseline; local validation of new selector revisions, GEMM v3 split-`k` kernel surface, diagnostic reporting outputs, studies, campaigns, and helper script `scripts/run_phase3_cycle.sh` | local implementation environment plus config-level CLI validation | the bounded Phase 3 corrective surface was implemented and locally validated before the later live execution block; this row is retained as provenance for the execution launch point, not as the main Phase 3 result | Medium | this row proves readiness, not comparative scientific direction; it is superseded scientifically by the completed Phase 3 evidence rows below | No |
| `E-P3-INTEGRITY` | `R5` Phase 3 artifact integrity | canonical confirmation studies plus reusable analysis bundle `artifacts/analysis/phase3_20260329/` | qualified homogeneous `RTX A6000` pool | the completed Phase 3 program is internally consistent: all canonical and replication campaigns finished successfully, all promoted studies emitted their expected report sets under the diagnostic/reportable rules, and the reusable analysis bundle records integrity, replication consistency, frontier diagnostics, and keep/drop decisions | High | this row proves completeness and provenance, not scientific direction by itself | No |
| `E-H5-P3` | `H5` representative GEMM transfer-safe test | `gemm_v3_baseline_mapping` canonical study `run_20260329T010211Z_dfb53abb`, supported by replication study `run_20260328T010058Z_7226d3f1` | qualified homogeneous `RTX A6000` pool | `H5` is unsupported: the canonical representative GEMM v3 study gives `v4_transfer_safe_profiled=0.1609x` vs default, far below both parent `prune_rank=1.0324x` and `naive_random_search=1.0427x`; the earlier main Phase 3 run also left `H5` unsupported, so no rerun gate is triggered | High | this is a bounded negative result for the current v4 rule, not proof that representative GEMM is now solved by the parent selector | Yes |
| `E-H4-P3-ABLATION` | `H4` / transfer mechanism | `gemm_v3_selector_ablation` canonical study `run_20260329T034953Z_e8b8ac98`, supported by replication study `run_20260328T034306Z_5055e181` | qualified homogeneous `RTX A6000` pool | the Phase 3 ablation shows that frontier-only and profiled-v4 fail almost identically on the expanded representative GEMM space; profiling therefore does not rescue the revised selector once the frontier is wrong | High | this deepens the transfer-failure story for the current revision family but does not rule out future revisions motivated by a new concrete mechanism | Yes |
| `E-P3-SCHEDULE` | `R5` GEMM schedule-family diagnostic | `gemm_v3_schedule_diag` canonical study `run_20260328T212649Z_7755304a`; Phase 3 analysis bundle `frontier_diagnostics_summary.csv` and `splitk_decision_table.csv` | qualified homogeneous `RTX A6000` pool | the diagnostic schedule batch completed successfully and shows that non-unit `split_k` values appear only as dominated frontier alternatives; they never survive as chosen or best-scored canonical GEMM families | High | diagnostic-only evidence explains failure modes but does not by itself prove reportable superiority or inferiority | No |
| `E-H3-P3-CONTEXT` | `H3` Phase 3 aligned-context refresh | `gemm_v3_aligned_reference` canonical study `run_20260329T045530Z_7086b0e7`, compared against canonical `gemm_v3_baseline_mapping` | qualified homogeneous `RTX A6000` pool | the Phase 3 aligned refresh does not strengthen the earlier `H3` story: aligned GEMM remains context, but the canonical `prune_rank` mean (`1.0158x`) is slightly below the canonical representative GEMM mean (`1.0324x`) | Medium | this weakens Phase-3-specific reinforcement without overturning the broader earlier H3 evidence from validation and Phase 2 | Yes |
| `E-H2-P3-SMALL` | `H2` LayerNorm small-batch microstudy | `layernorm_v2_small_microstudy` canonical study `run_20260329T053448Z_7c6e5dc1`, supported by replication study `run_20260328T231251Z_29646063` | qualified homogeneous `RTX A6000` pool | the small-batch microstudy remains weak and noisy: canonical `prune_rank_profiled` improves only slightly over default (`1.0013x`) and only modestly over `prune_rank` (`0.9721x`), while `naive_random_search` is much higher but unstable; this is not a strong profiling success story | Medium | replication variability is large enough that the correct paper framing is bounded and cautious, not promotive | No |
| `E-H2-P3-LARGE` | `H2` LayerNorm large-batch microstudy | `layernorm_v2_large_microstudy` canonical study `run_20260329T053455Z_c4118a25`, supported by replication study `run_20260328T231256Z_847b98a5` | qualified homogeneous `RTX A6000` pool | the large-batch microstudy continues to favor compile-only ranking: canonical `prune_rank=1.0149x` vs default while `prune_rank_profiled=0.9971x` and `prune_rank_revised=0.9777x`; this keeps LayerNorm as a bounded explanatory thread rather than a major positive result | High | the evidence is strong enough to bound the claim, but still not rich enough to motivate a major new LayerNorm selector program | No |
| `E-P3-ROWS` | `R5` LayerNorm keep/drop decision | Phase 3 analysis bundle `rows_per_program_decision_table.csv`, grounded in canonical `layernorm_v2_small_microstudy` and `layernorm_v2_large_microstudy` | qualified homogeneous `RTX A6000` pool | `rows_per_program` should be retired from the main reportable LayerNorm surface: non-unit selections occur only in weak or regressing profiled/revised paths and do not produce a stable selector-level gain | High | the knob can remain as archived diagnostic surface, but it no longer belongs in the mainline paper-facing tuning surface | No |
| `E-R6-INTEGRITY` | `R6` final artifact integrity | `gemm_final_baseline_mapping` campaign `run_20260330T003313Z_9e0cdfce`; `gemm_final_selector_ablation` campaign `run_20260330T014321Z_c4e9fa9d`; final bundle `artifacts/analysis/final_paper_20260330/` | qualified homogeneous `RTX A6000` pool | the bounded final-mainline program completed cleanly: both required campaigns finished with `0` failures, the optional aligned refresh and confirmation reruns were skipped by explicit gate, and the final paper bundle pins all promoted sources to stable repo-local artifacts | High | this row proves completeness and promotion discipline rather than scientific direction by itself | No |
| `E-R6-HEADLINE` | `R6` final representative GEMM mainline | `gemm_final_baseline_mapping` canonical study `run_20260330T014317Z_359c1904`, with mechanism support from `gemm_final_selector_ablation` `run_20260330T023529Z_7c800187` | qualified homogeneous `RTX A6000` pool | the guarded `v5_mainline_profiled` selector is the final positive mainline result: it reaches `1.0286x` vs default on representative GEMM, beating parent `prune_rank=0.8101x` by `0.2185` while also surpassing `naive_random_search=1.0011x`; the final bundle treats this as a bounded improvement rather than the strongest promotion tier because the stricter positive-seed gate did not clear | High | this is the final non-`split_k` mainline result and must not be merged conceptually with the unsupported `H5` split-`k` result | Yes |
| `E-R6-ABLATION` | `R6` final revised-selector mechanism | `gemm_final_selector_ablation` canonical study `run_20260330T023529Z_7c800187` | qualified homogeneous `RTX A6000` pool | the final guarded mainline ablation shows that both `v5_mainline_frontier` (`1.0272x`) and `v5_mainline_profiled` (`1.0283x`) recover the parent baseline (`0.8103x`) on the non-`split_k` surface, with profiling adding only a very small increment once the conservative frontier union is in place | High | the ablation is final-mainline evidence only; it does not overturn the earlier bounded negative result for the Phase 3 `split_k` space | Yes |
| `E-R6-BUNDLE` | final paper-evidence lock | `artifacts/analysis/final_paper_20260330/` and [11_final_claim_inventory.md](11_final_claim_inventory.md) | repository-local promoted artifact set | the final paper-evidence package is now reproducible from repo-local artifacts: the canonical artifact map, figure source map, final claim table, and final claim inventory all agree on one narrow figure set and one final wording discipline | High | if a future paper draft needs a figure not covered by this bundle, that request should be treated as a provenance gap rather than as justification for a new exploratory run | No |

## Hypothesis Status Snapshot

| Hypothesis | Current Status | Notes |
| --- | --- | --- |
| `H1` | Strong overall | supported by the original validation batch, strengthened by the `gpunode3` confirmation runs, and reinforced by the Phase 2 expanded non-`split_k` representative GEMM result |
| `H2` | Regime-split weak or negative result | the pooled corrected rerun remained unsupported; the Phase 2 split studies and Phase 3 microstudy keep LayerNorm bounded to a weak small-batch and negative large-batch story |
| `H3` | Contextual support | supported by the earlier validation and Phase 2 evidence; the Phase 3 aligned refresh did not strengthen it, and the final paper bundle intentionally uses the stronger Phase 2 aligned context |
| `H4` | Mixed and transfer-limited | the frontier-aware retry succeeded on the narrower representative GEMM space, the expanded v2 and v3 spaces did not preserve that success, and the final non-`split_k` R6 mainline pass recovers a bounded positive result only after a more conservative surface lock |
| `H5` | Unsupported | the completed representative GEMM v3 mapping and ablation show that the current transfer-safe v4 selector family remains far below both parent `prune_rank` and `naive_random_search` on the expanded `split_k` space |

## Final Mainline Snapshot

The final mainline headline is intentionally tracked separately from `H5`.

- `R6_profiled_headline` is the final positive mainline result:
  - `v5_mainline_profiled=1.0286x` vs default on representative GEMM
  - parent `prune_rank=0.8101x`
  - `naive_random_search=1.0011x`
- this is written as a bounded improvement rather than the strongest promotion tier because the stricter positive-seed gate did not clear
- `H5` remains unsupported and stays specific to the expanded Phase 3 `split_k` surface

## Current Next Evidence Targets

- preserve the reusable Phase 2, Phase 3, and final-paper bundles as the canonical parent references for writing and handoff
- use the final paper bundle as the paper-facing promotion boundary
- do not schedule a new rerun by default:
  - the Phase 3 rerun gates did not trigger
  - the bounded R6 program completed and the optional aligned refresh / confirmation reruns were skipped by gate rather than dropped accidentally
- focus next on synthesis, figure extraction, presentation material, and manuscript drafting rather than further exploratory expansion

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
- The completed Phase 2 sources are:
  - `gemm_v2_baseline_mapping` study `run_20260327T164637Z_0403b989`
  - `gemm_v2_selector_ablation` study `run_20260327T175823Z_376d6bbc`
  - `layernorm_v2_small_regime` study `run_20260327T183157Z_53565cba`
  - `layernorm_v2_large_regime` study `run_20260327T183158Z_37695a2d`
  - `gemm_v2_aligned_reference` study `run_20260327T190124Z_3a34cdc7`
- The completed canonical Phase 3 sources are:
  - `gemm_v3_baseline_mapping` study `run_20260329T010211Z_dfb53abb`
  - `gemm_v3_selector_ablation` study `run_20260329T034953Z_e8b8ac98`
  - `gemm_v3_schedule_diag` study `run_20260328T212649Z_7755304a`
  - `gemm_v3_aligned_reference` study `run_20260329T045530Z_7086b0e7`
  - `layernorm_v2_small_microstudy` study `run_20260329T053448Z_7c6e5dc1`
  - `layernorm_v2_large_microstudy` study `run_20260329T053455Z_c4118a25`
- The completed canonical `R6` sources are:
  - `gemm_final_baseline_mapping` study `run_20260330T014317Z_359c1904`
  - `gemm_final_selector_ablation` study `run_20260330T023529Z_7c800187`
  - `gemm_final_aligned_reference` was intentionally skipped by gate
- The reusable Phase 2 analysis bundle is:
  - `artifacts/analysis/phase2_20260327/`
- The reusable Phase 3 analysis bundle is:
  - `artifacts/analysis/phase3_20260329/`
- The final paper-evidence bundle is:
  - `artifacts/analysis/final_paper_20260330/`
- The detailed chronological record for the completed Phase 2 analysis is:
  - `docs/research/logs/2026-03-27_phase2_execution_analysis.md`
- The detailed chronological record for the completed Phase 3 analysis is:
  - `docs/research/logs/2026-03-29_phase3_execution_analysis.md`
- The detailed chronological record for the completed final-mainline synthesis is:
  - `docs/research/logs/2026-03-30_r6_final_synthesis_and_evidence_lock.md`
- The detailed chronological record for the full `gpunode3` block should be maintained in a dated log entry under `logs/`.
- The detailed chronological record for the corrected follow-up block should also be maintained in a dated log entry under `logs/`.
- Noncanonical Phase 3 raw experiment roots moved under `/tmp/.../phase3_raw` are archival provenance only and are not promoted figure or claim sources.
- Batch-level study outputs remain the automated result source.
- This registry remains the authoritative place to assign project-level confidence and next actions.

## Promotion Rule

Evidence should only be promoted into the paper backbone when:

- the relevant round exit gate has been passed,
- the evidence is marked reportable or explicitly diagnostic in the registry,
- the interpretation survives at least one repeated or cross-run check appropriate to the claim,
- and no unresolved confound is still blocking the intended paper claim.
