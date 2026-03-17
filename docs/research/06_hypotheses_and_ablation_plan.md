# Hypotheses And Ablation Plan

Purpose: pre-register the research hypotheses, define the selector ladder, and specify how support or rejection will be judged.
Status: Backbone
Update Rule: update only when a hypothesis changes materially, a new selector level is admitted, or a comparison rule changes.
Feeds Paper Sections: Research Questions, Method, Results, Ablations
Depends On: [../04_experiment_protocol.md](../04_experiment_protocol.md), [../adr/ADR-002-heuristic-first-selector.md](../adr/ADR-002-heuristic-first-selector.md), [05_workload_matrix_and_case_studies.md](05_workload_matrix_and_case_studies.md), [07_experiment_campaign_plan.md](07_experiment_campaign_plan.md)

## Measurement Gate

Before any substantive hypothesis is judged, the following gate must be passed:

- runtime stability is sufficient for repeated-run comparison,
- matched-budget counter sets satisfy their availability threshold,
- and reportable studies remain protocol-compliant on the pinned environment.

If this gate is not passed, substantive hypotheses remain inconclusive regardless of apparent wins.

## Primary Metrics

### Primary metric

- geometric mean of per-shape speedup ratios versus `default_config`

### Required secondary metrics

- speedup versus `naive_random_search`
- speedup versus `naive_grid_search`
- winner rate per held-out shape
- regret versus best measured calibration candidate
- selection agreement across repeated runs
- run-to-run stability band
- signal-to-runtime correlation
- profiler counter availability

## Selector Ladder

| Selector Level | Description | Intended Role |
| --- | --- | --- |
| `default_config` | fixed kernel default | baseline floor |
| `naive_random_search` | seeded random calibration search under budget | naive baseline |
| `naive_grid_search` | canonical-order calibration search under budget | naive baseline |
| `prune_only` | cheap-signal pruning, then first survivor | tests whether pruning alone helps |
| `prune_rank` | cheap-signal pruning plus compile-signal ranking | tests whether cheap signals support useful ranking |
| `prune_rank_profiled` | compile ranking plus limited profiling reorder | tests whether matched-budget profiling adds value |
| `prune_rank_revised` | opportunity-guided revised heuristic under the same budget | tests whether measured failure analysis leads to better selection |

No selector level should be added to the paper unless it answers a question the existing ladder cannot.

## Hypotheses

| ID | Statement | Expected Mechanism | Comparison Pair | Support Criterion | Reject Criterion | Main Confounds |
| --- | --- | --- | --- | --- | --- | --- |
| `H1` | Cheap compile signals can prune obvious losers, but they do not reliably rank near-tied GEMM configs on representative workloads. | cheap signals capture gross resource failures but miss fine-grained compute vs memory distinctions among survivors | `prune_only` / `prune_rank` vs profiled or revised selectors on representative GEMM | compile-signal selectors remove clearly weak configs, but profiled or revised selectors materially improve held-out behavior or stability on at least one representative GEMM class | cheap-signal selectors either fail to prune meaningfully or already match stronger selectors across representative GEMM classes | noise, too-small workload spread, insufficient profiler evidence |
| `H2` | Limited profiling helps more on LayerNorm than on GEMM under matched budget. | LayerNorm is more memory-bound and therefore benefits more from targeted memory-centric counters | `prune_rank_profiled` vs `prune_rank` on GEMM and LayerNorm | profiling yields a larger held-out improvement or stability improvement on LayerNorm than on GEMM | profiling gives no differential advantage or helps GEMM equally/more | counter availability, workload imbalance, profiling overhead |
| `H3` | The aligned GEMM workload overstates selector quality relative to the representative GEMM workload. | regular aligned shapes hide edge and aspect-ratio failure modes | `gemm_aligned_reportable` vs `gemm_reportable` using the same strategy ladder | selector gains are stronger or more stable on aligned GEMM than on representative GEMM | selector quality transfers equally well across both workload programs | insufficient irregular shapes, unstable reportable runs |
| `H4` | Opportunity-guided heuristic revisions improve held-out performance under the same budget more reliably than the current selector. | measured failure modes reveal specific ranking weaknesses that a revised heuristic can address | `prune_rank_revised` vs `prune_rank` on reportable GEMM and LayerNorm | revised selector improves held-out metrics or stability without increasing budget and the improvement is consistent enough across repeated runs | revision does not help or only helps via budget leakage or non-repeatable wins | overtuning to one workload class, hidden measurement confounds |

## Support / Reject / Inconclusive Rules

### Support

A hypothesis is supported when:

- the comparison is reportable,
- the sign of the effect matches the hypothesis,
- the effect is consistent enough across repeated runs or workload classes to survive noise,
- and the mechanism-level explanation matches the observed signals.

### Reject

A hypothesis is rejected when:

- the comparison is reportable,
- the evidence consistently points in the opposite direction,
- and no stronger confound explains the result.

### Inconclusive

A hypothesis remains inconclusive when:

- measurement validity is not established,
- counter availability is insufficient,
- the run matrix is incomplete,
- or the observed effect size is too unstable to distinguish from noise.

## Hypothesis Cross-Reference

| Hypothesis | Required Workloads | Required Signals | Required Runs | Required Figures |
| --- | --- | --- | --- | --- |
| `H1` | `gemm_reportable`, `gemm_aligned_reportable` | Tier 0 cheap signals, optional `compute_lite` for diagnosis | repeatability GEMM runs and robustness-seed GEMM runs | per-workload-class speedup, selector stability, signal-runtime correlation |
| `H2` | `gemm_reportable`, `layernorm_reportable` | `compute_lite`, `memory_lite` | matched-budget profiled runs on both kernel families | cross-kernel profiling-gain comparison, counter availability plot |
| `H3` | `gemm_aligned_reportable`, `gemm_reportable` | Tier 0 cheap signals and held-out runtime | aligned vs representative GEMM run groups | aligned-vs-representative speedup figure, workload-class breakdown |
| `H4` | `gemm_reportable`, `layernorm_reportable` | Tier 0 plus whichever Tier 1 signals motivated the revision | revised-selector run groups under unchanged budgets | revised-vs-current selector comparison, opportunity case-study figure |

## Ablation Discipline

The paper should avoid arbitrary tuner growth. Every selector revision must answer all of these:

1. What failure mode was observed?
2. Which bottleneck category does it correspond to?
3. Which signals support that diagnosis?
4. Which knob response does the revised heuristic favor?
5. What matched-budget comparison will show whether the revision helped?

If those questions cannot be answered, the revision does not belong in the ablation plan.
