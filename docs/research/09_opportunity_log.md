# Opportunity Log

Purpose: track bottleneck-driven tuner opportunities and prevent ad hoc selector changes.
Status: Living Registry
Update Rule: update whenever a new failure mode or tuning opportunity is identified from evidence.
Feeds Paper Sections: Results, Failure Analysis, Discussion
Depends On: [03_bottleneck_taxonomy.md](03_bottleneck_taxonomy.md), [04_signal_and_profiling_plan.md](04_signal_and_profiling_plan.md), [08_evidence_registry.md](08_evidence_registry.md)

## Admission Rule

An opportunity should only be admitted when there is at least one concrete observation linking:

- a failure mode or selector weakness,
- a bottleneck category,
- and a candidate tuning intervention.

If the observation is purely speculative, keep it in a dated log entry instead of promoting it here.

## Current Opportunities

Promotion note:

- an opportunity may be implemented before it is promoted into the evidence registry as a comparative result
- the current Phase 3 state is now evaluated rather than pending: the transfer-safe corrective pass has completed and the bounded keep/drop decisions are known

| Opportunity ID | Observed Failure Mode | Suspected Bottleneck | Signal Evidence | Affected Workload Class | Candidate Intervention | Tried? | Result | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `OPP-001` | representative GEMM frontier construction is still wrong, but the failure mode changed under Phase 2 expansion | compile-frontier ranking is sensitive both to underweighting balanced high-area tiles and to overcorrecting toward oversized masked tiles once the space expands | earlier evidence showed the selector missing the balanced `128x128x32` family; the Phase 2 expanded space now shows `naive_random_search` preferring `cfg_695bff677bfb` while both `v3_frontier_only` and full `v3_h4_targeted` collapse onto oversized `cfg_24d8f84f938f` | representative GEMM, especially `m_dominant`, `square_compute`, and `edge_nondivisible` classes | replace the current area-seeking frontier rule with a shape-relative, mask-aware frontier rule rather than adding another profile-only reranker | Yes, twice | the narrow-space retry worked, but the expanded-space rerun and ablation showed that the current `v3` rule does not generalize | Keep as the main current tuner-forward opportunity, but redefine it around transfer-safe frontier construction |
| `OPP-002` | aligned GEMM continues to make the current selector ladder look better than the representative matrix | evaluation simplification hides edge and aspect-ratio failure modes that matter on the representative workload | original validation batch plus broad `gpunode3` requalification both support the same direction; the narrow `H1/H3` batch reproduces the effect direction even though it misses the support margin slightly | aligned GEMM versus representative GEMM | keep representative GEMM as the primary truth source; use aligned GEMM as a supporting reference workload only | Yes | this has become a stable evaluation-policy constraint, not a tuner change by itself | Keep |
| `OPP-003` | LayerNorm `H2` follow-up is partially confounded because the current kernel default baseline is not valid across the full representative workload | baseline-definition and workload-validity issue rather than a profiling bottleneck by itself | the original `h2_followup_g3` study reported `null` primary metrics for `large_batch`; the kernel default in [layernorm.yaml](../../configs/kernels/layernorm.yaml) was `block_size=1024` while the workload includes `hidden=4096` | representative LayerNorm, especially the `large_batch` held-out path | replace the LayerNorm default with a universally valid baseline config, then rerun the narrowed `H2` study before promoting any LayerNorm profiling conclusion | Yes | the confound was removed by the `layernorm_baselinefix` rerun; `H2` still remained unsupported afterward, so this opportunity is now a resolved methodological prerequisite rather than an active tuner change | Keep as evaluation discipline |
| `OPP-004` | LayerNorm does not behave like one uniform memory-bound regime | the current `memory_lite` counters are informative for some shapes but too blunt across both bandwidth-heavy and latency-sensitive LayerNorm cases | diagnostic profiling after `h2_followup_g3` showed `rows=2048, hidden=4096` near `91%` DRAM throughput with lower long-scoreboard stall, while `rows=128, hidden=4096` was far lower throughput with higher long-scoreboard stall; the corrected `h2_followup_g3_baselinefix` rerun still produced only a small LayerNorm profiling gain overall | LayerNorm `large_batch` versus `small_batch` classes | run a stricter stratified diagnostic microstudy and consider augmenting LayerNorm ranking with one occupancy/activity signal or class-specific interpretation before the next paper-facing claim | Yes, diagnostically and via corrected rerun | diagnostics and the corrected rerun both support the regime split, but the current evidence still does not justify a new LayerNorm selector path as the main next project priority | Keep as lower-priority future work |
| `OPP-005` | the current `v2_validation` revised selector does not beat its parent because it only reranks inside the frontier it inherits | revision logic is attacking late tie-breaking when the main loss already happened during frontier construction | `H4` non-support in the original batch, plus `gpunode3` GEMM evidence showing that the winning config family often lies outside the benchmarked frontier | representative GEMM | make the next and only admissible `H4` retry a frontier-aware GEMM-focused revision under unchanged budget; do not add another profile-only reranker first | Yes | the `v3_h4_targeted` retry validated this diagnosis directly, but Phase 2 later showed that the resulting frontier rule was not robust enough to transfer to the expanded space | Keep as the motivating failed baseline for the original revision, but no longer as the current leading intervention |
| `OPP-006` | the v1 candidate generator could silently cap the search space before kernel validation | hidden raw-space truncation makes larger-space studies methodologically suspect because candidate IDs, not valid kernels, determine what survives | Phase 2 planning and code review showed that the historical generator truncated the raw Cartesian space to `max_candidates` before validating configs | all kernel families once the space expands beyond v1 | make `max_candidates` a hard admissibility limit after validation, record raw and valid counts, and fail explicitly on overflow | Yes | implemented in the Phase 2 generator path; new v2 reportable studies can no longer silently truncate valid config spaces | Keep as a methodological safeguard |
| `OPP-007` | LayerNorm still behaves like at least two regimes after the corrected `H2` rerun | one pooled LayerNorm ranking story is too coarse; small-batch and large-batch shapes likely need at least one activity-aware signal and one additional launch-shape knob | corrected `h2_followup_g3_baselinefix` still left `H2` unsupported, while diagnostic runs showed strongly different DRAM-throughput and scoreboard patterns between `small_batch` and `large_batch`; Phase 2 then confirmed a marginal small-batch gain and a large-batch regression under `memory_activity_lite` | LayerNorm `small_batch` and `large_batch` | split the next LayerNorm studies by regime, add `rows_per_program`, and use `memory_activity_lite` instead of relying only on `memory_lite` | Yes | the regime split was scientifically useful, but the completed Phase 3 microstudy showed that `rows_per_program` is too weak and noisy to keep in the main LayerNorm surface | Keep as a lower-priority explanatory thread; retire `rows_per_program` from the mainline surface |
| `OPP-008` | the current Phase 2 GEMM revision overgeneralizes toward oversized masked tiles | the frontier rule rewards tile area and balance without enough penalty for excessive masking or shape-relative overcoverage | `gemm_v2_baseline_mapping` and `gemm_v2_selector_ablation` both show `prune_rank_revised` selecting `cfg_24d8f84f938f` (`256x256x32`, `group_size_m=8`, `num_stages=4`, `num_warps=8`) across all representative workload classes, with catastrophic held-out performance | representative GEMM expanded v2 space | add a shape-relative tile-fit term or an explicit masked-oversize penalty before admitting any further GEMM revised-selector retry | Yes | the completed Phase 3 corrective pass promoted this diagnosis into `v4_transfer_safe_frontier` / `v4_transfer_safe_profiled`, but the resulting selector family still failed badly on the split-`k` space | Keep as failure-analysis evidence, not as justification for another immediate selector retry |
| `OPP-009` | the project needed to know whether `split_k` was a helpful orthogonal schedule family or just added burden | one new schedule family may improve representative GEMM reachability, but it may also amplify reduction overhead and destabilize frontier transfer if the selector cannot reason about it | Phase 2 already showed that tile-only frontier rules were fragile once the space expanded; Phase 3 admitted `split_k` specifically to test whether a transfer-safe selector could stay near random search even when the search space included a new decomposition choice | representative GEMM expanded Phase 3 space | admit `split_k` once, keep budgets explicit, record family mismatch and frontier diagnostics, and decide keep/drop from Phase 3 evidence rather than intuition | Yes | the completed Phase 3 bundle showed that non-unit `split_k` values never survived into chosen or best-scored canonical GEMM families and appeared only as dominated frontier alternatives | Close as a bounded negative result; retire `split_k` from the mainline surface |

## Deferred Until Evidence Exists

The following ideas are intentionally *not* admitted yet:

- broad new kernel families beyond GEMM and LayerNorm before the current Phase 2 findings are written up
- LayerNorm-specific selector changes that outrun the current regime split and `memory_activity_lite` follow-up
- multiple new selector revisions at once
- persistent scheduling or broader algorithm-family expansion before a new concrete post-Phase-3 mechanism appears

## Promotion Path

Ideas should move through this sequence:

1. a dated note in `logs/`
2. an admitted opportunity here once the bottleneck and intervention are concrete
3. an evaluated comparison in the evidence registry after the intervention is run
4. a selector or paper-backbone change only if the evidence survives repeated checks
