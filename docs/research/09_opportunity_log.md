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

| Opportunity ID | Observed Failure Mode | Suspected Bottleneck | Signal Evidence | Affected Workload Class | Candidate Intervention | Tried? | Result | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `OPP-001` | representative GEMM keeps selecting smaller asymmetric tiles while the stable held-out winner is the balanced `128x128x32`, `num_stages=4`, `num_warps=4` family | selector frontier construction is biased too early toward cheap compile-resource proxies and underweights balanced high-area tiles | original validation plus `gpunode3` broad and `H1/H3` confirmation batches; `naive_random_search` picks `cfg_ccbf6a0142ec` stably, while `prune_rank`, `prune_rank_profiled`, and `prune_rank_revised` mostly choose `cfg_72eefb2e03cf` / `cfg_bbbcabc7810a` | representative GEMM, especially `m_dominant`, `square_compute`, and `edge_nondivisible` classes | create one frontier-aware `v3` revision that reranks the compile frontier before profiling using config-shape features such as `tile_area`, `shape_balance`, `num_stages`, and `num_warps` | Yes | the `v3_h4_targeted` retry succeeded on representative GEMM and supported `H4`, improving `prune_rank_revised` to `1.0996x` vs default against the parent `prune_rank` at `0.9666x` | Keep and promote as the current tuner-forward result |
| `OPP-002` | aligned GEMM continues to make the current selector ladder look better than the representative matrix | evaluation simplification hides edge and aspect-ratio failure modes that matter on the representative workload | original validation batch plus broad `gpunode3` requalification both support the same direction; the narrow `H1/H3` batch reproduces the effect direction even though it misses the support margin slightly | aligned GEMM versus representative GEMM | keep representative GEMM as the primary truth source; use aligned GEMM as a supporting reference workload only | Yes | this has become a stable evaluation-policy constraint, not a tuner change by itself | Keep |
| `OPP-003` | LayerNorm `H2` follow-up is partially confounded because the current kernel default baseline is not valid across the full representative workload | baseline-definition and workload-validity issue rather than a profiling bottleneck by itself | the original `h2_followup_g3` study reported `null` primary metrics for `large_batch`; the kernel default in [layernorm.yaml](../../configs/kernels/layernorm.yaml) was `block_size=1024` while the workload includes `hidden=4096` | representative LayerNorm, especially the `large_batch` held-out path | replace the LayerNorm default with a universally valid baseline config, then rerun the narrowed `H2` study before promoting any LayerNorm profiling conclusion | Yes | the confound was removed by the `layernorm_baselinefix` rerun; `H2` still remained unsupported afterward, so this opportunity is now a resolved methodological prerequisite rather than an active tuner change | Keep as evaluation discipline |
| `OPP-004` | LayerNorm does not behave like one uniform memory-bound regime | the current `memory_lite` counters are informative for some shapes but too blunt across both bandwidth-heavy and latency-sensitive LayerNorm cases | diagnostic profiling after `h2_followup_g3` showed `rows=2048, hidden=4096` near `91%` DRAM throughput with lower long-scoreboard stall, while `rows=128, hidden=4096` was far lower throughput with higher long-scoreboard stall; the corrected `h2_followup_g3_baselinefix` rerun still produced only a small LayerNorm profiling gain overall | LayerNorm `large_batch` versus `small_batch` classes | run a stricter stratified diagnostic microstudy and consider augmenting LayerNorm ranking with one occupancy/activity signal or class-specific interpretation before the next paper-facing claim | Yes, diagnostically and via corrected rerun | diagnostics and the corrected rerun both support the regime split, but the current evidence still does not justify a new LayerNorm selector path as the main next project priority | Keep as lower-priority future work |
| `OPP-005` | the current `v2_validation` revised selector does not beat its parent because it only reranks inside the frontier it inherits | revision logic is attacking late tie-breaking when the main loss already happened during frontier construction | `H4` non-support in the original batch, plus `gpunode3` GEMM evidence showing that the winning config family often lies outside the benchmarked frontier | representative GEMM | make the next and only admissible `H4` retry a frontier-aware GEMM-focused revision under unchanged budget; do not add another profile-only reranker first | Yes | the `v3_h4_targeted` retry validated this diagnosis directly and turned `H4` into a supported result | Keep as the motivating failed baseline, but superseded by `OPP-001` implementation |
| `OPP-006` | the v1 candidate generator could silently cap the search space before kernel validation | hidden raw-space truncation makes larger-space studies methodologically suspect because candidate IDs, not valid kernels, determine what survives | Phase 2 planning and code review showed that the historical generator truncated the raw Cartesian space to `max_candidates` before validating configs | all kernel families once the space expands beyond v1 | make `max_candidates` a hard admissibility limit after validation, record raw and valid counts, and fail explicitly on overflow | Yes | implemented in the Phase 2 generator path; new v2 reportable studies can no longer silently truncate valid config spaces | Keep as a methodological safeguard |
| `OPP-007` | LayerNorm still behaves like at least two regimes after the corrected `H2` rerun | one pooled LayerNorm ranking story is too coarse; small-batch and large-batch shapes likely need at least one activity-aware signal and one additional launch-shape knob | corrected `h2_followup_g3_baselinefix` still left `H2` unsupported, while diagnostic runs showed strongly different DRAM-throughput and scoreboard patterns between `small_batch` and `large_batch` | LayerNorm `small_batch` and `large_batch` | split the next LayerNorm studies by regime, add `rows_per_program`, and use `memory_activity_lite` instead of relying only on `memory_lite` | Admitted for Phase 2 | implementation committed, evidence pending | Keep and evaluate in the next batch |

## Deferred Until Evidence Exists

The following ideas are intentionally *not* admitted yet:

- broad new kernel families before the GEMM v2 and LayerNorm v2 spaces are evaluated
- LayerNorm-specific selector changes that outrun the current regime split and `memory_activity_lite` follow-up
- multiple new selector revisions at once
- `split_k`, persistent scheduling, or algorithm-family expansion without a post-`v3` need

## Promotion Path

Ideas should move through this sequence:

1. a dated note in `logs/`
2. an admitted opportunity here once the bottleneck and intervention are concrete
3. an evaluated comparison in the evidence registry after the intervention is run
4. a selector or paper-backbone change only if the evidence survives repeated checks
