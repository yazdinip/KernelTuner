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
| `OPP-001` | compile-signal ranking remains weak on representative GEMM survivors that already pass cheap-resource filters | compute vs memory discrimination is too weak among near-tied survivors | first validation batch currently supports `H1`; representative GEMM shows that compile-only ranking does not separate the final winner reliably enough | representative GEMM, especially non-aligned and aspect-ratio-skewed classes | run one tighter follow-up that uses Tier 1 compute evidence to justify a narrower revised ranker, not a broad heuristic rewrite | Yes, indirectly via `prune_rank_profiled` and `prune_rank_revised` | first-pass profiling and revision did not yet produce a clear stable fix | Keep, but require one narrower evidence-backed retry |
| `OPP-002` | aligned GEMM makes the strategy ladder look stronger than the representative workload does | study-design simplification hides edge and aspect-ratio bottlenecks | first validation batch currently supports `H3`; aligned GEMM produced more flattering outcomes than the representative matrix | aligned GEMM versus representative GEMM | treat representative GEMM as the primary truth source and aligned GEMM as a supporting reference workload only | Yes | produced a useful evaluation-policy result rather than a selector improvement | Keep as an evaluation-policy constraint |
| `OPP-003` | LayerNorm profiling did not clearly outperform compile-only ranking under the current matched budget | memory-centric counters may be too coarsely aggregated, or the LayerNorm knob surface may be too small to expose useful profiler-driven separation | first validation batch did not support `H2` under the current `memory_lite` + selector setup | LayerNorm `small_batch` and `large_batch` classes | run one targeted LayerNorm follow-up with the same budget discipline, explicit inspection of profiling-derived ranking behavior, and no unrelated heuristic growth | Yes, in the first validation batch | current evidence is non-support, but not yet strong enough to kill the idea | Keep for targeted follow-up |
| `OPP-004` | the first opportunity-guided revised selector did not reliably beat `prune_rank` | the admitted revision may still be too broad or not tightly linked enough to one failure mode | first validation batch did not support `H4`; `v2_validation` failed to establish a stable held-out gain under unchanged budget | representative GEMM and LayerNorm | admit at most one additional revision batch and require a single explicit bottleneck rationale plus unchanged-budget comparison | Yes | first admitted revision did not justify promotion | Keep, but narrow the next attempt sharply |

## Deferred Until Evidence Exists

The following ideas are intentionally *not* admitted yet:

- multiple new selector revisions at once
- LayerNorm-specific ranking changes that are not tied to the targeted `H2` follow-up
- `split_k` expansion without a demonstrated GEMM reduction-latency bottleneck
- vectorized access variants without stable memory-pressure evidence
- persistent scheduling variants without a clearly documented scheduling inefficiency case

## Promotion Path

Ideas should move through this sequence:

1. a dated note in `logs/`
2. an admitted opportunity here once the bottleneck and intervention are concrete
3. an evaluated comparison in the evidence registry after the intervention is run
4. a selector or paper-backbone change only if the evidence survives repeated checks
