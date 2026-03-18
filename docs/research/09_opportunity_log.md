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
| `OPP-001` | compile-signal-only selection is expected to be unstable on near-tied GEMM survivors | compute vs memory discrimination is too weak among candidates that already pass cheap-resource filters | prior project analysis identified weak separation between compile signals and final held-out outcomes on near-tied GEMM configs; research-phase validation still pending | representative GEMM, especially `square_compute` and `edge_nondivisible` | use `compute_lite` counters and an opportunity-guided revised ranker that penalizes tensor under-utilization and scoreboard-heavy survivors | Not yet under the research campaign | n/a | Unresolved |

## Deferred Until Evidence Exists

The following ideas are intentionally *not* admitted yet:

- LayerNorm-specific ranking changes without completed LayerNorm reportable evidence
- `split_k` expansion without a demonstrated GEMM reduction-latency bottleneck
- vectorized access variants without stable memory-pressure evidence
- persistent scheduling variants without a clearly documented scheduling inefficiency case

## Promotion Path

Ideas should move through this sequence:

1. a dated note in `logs/`
2. an admitted opportunity here once the bottleneck and intervention are concrete
3. an evaluated comparison in the evidence registry after the intervention is run
4. a selector or paper-backbone change only if the evidence survives repeated checks
