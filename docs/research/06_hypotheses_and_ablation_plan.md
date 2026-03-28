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
| `H5` | A shape-relative, transfer-safe frontier policy can recover near-random-search GEMM performance on the expanded schedule space under the same matched budget, even after admitting `split_k`. | transfer-safe frontier construction should keep strong families reachable without collapsing onto oversized masked tiles once the space admits one orthogonal schedule family | `v4_transfer_safe_frontier` / `v4_transfer_safe_profiled` vs `prune_rank` and `naive_random_search` on representative GEMM v3 | `v4_transfer_safe_profiled` beats parent `prune_rank` by at least `+0.05` geomean speedup vs default, lands within `0.02` of `naive_random_search`, and the win is not confined to one seed or workload class | transfer-safe revisions still miss random search badly, only help one isolated class, or profiling remains necessary to rescue a weak frontier | hidden split-`k` overhead, search-space overflow, unstable frontier diagnostics |

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

## Status Interpretation Discipline

Generated study outputs use the labels `supported`, `unsupported`, and `inconclusive` for the current evaluated batch.

Interpret these labels carefully:

- `supported` means the current batch satisfied the pre-registered support criterion
- `unsupported` means the current batch did not satisfy the support criterion
- `unsupported` does **not** automatically mean the project should treat the hypothesis as finally rejected
- promotion from a batch-level result to a stronger project-level conclusion must pass through the evidence registry and survive at least one appropriate confirmation or follow-up batch

Practical rule:

- the study output is the automated comparison result
- the evidence registry is the authoritative record of how much confidence the project currently places in that result

Latest evaluated batches:

- the current project-level interpretation of the completed `gpunode2` and `gpunode3` execution blocks lives in [08_evidence_registry.md](08_evidence_registry.md)
- the detailed chronological record of the `gpunode3` long execution block should be kept in the dated logs under `logs/`
- the corrected LayerNorm follow-up is recorded in `h2_followup_g3_baselinefix` study `run_20260327T025533Z_0d0e6750`
- the frontier-aware GEMM retry is recorded in `h4_retry_g3` study `run_20260327T035659Z_10f9baec`
- the completed Phase 2 expanded-space studies are:
  - `gemm_v2_baseline_mapping` study `run_20260327T164637Z_0403b989`
  - `gemm_v2_selector_ablation` study `run_20260327T175823Z_376d6bbc`
  - `layernorm_v2_small_regime` study `run_20260327T183157Z_53565cba`
  - `layernorm_v2_large_regime` study `run_20260327T183158Z_37695a2d`
  - `gemm_v2_aligned_reference` study `run_20260327T190124Z_3a34cdc7`
- the canonical Phase 2 analysis summary is recorded in [logs/2026-03-27_phase2_execution_analysis.md](logs/2026-03-27_phase2_execution_analysis.md)

Current post-Phase-2 rule:

- exactly one new top-level hypothesis is admitted:
  - `H5`, the Phase 3 transfer-safe frontier hypothesis
- `H1` is now stronger because the expanded representative GEMM space preserved the original result direction
- `H2` should now be interpreted through split LayerNorm regimes rather than one pooled LayerNorm result
- `H4` should now be interpreted as mixed:
  - the narrower v1 representative GEMM retry supported the frontier-aware revision
  - the expanded v2 representative GEMM space did not preserve that win
- `H3` remains an evaluation-context hypothesis and should be refreshed only as a supporting comparison workload
- Phase 3 execution is justified narrowly by the concrete Phase 2 mechanism:
  - the expanded-space frontier collapsed toward oversized masked tiles
  - and the next admissible corrective pass is a shape-relative, transfer-safe frontier plus one bounded new schedule family (`split_k`)

## Hypothesis Cross-Reference

| Hypothesis | Required Workloads | Required Signals | Required Runs | Required Figures |
| --- | --- | --- | --- | --- |
| `H1` | `gemm_reportable`, `gemm_aligned_reportable` | Tier 0 cheap signals, optional `compute_lite` for diagnosis | repeatability GEMM runs and robustness-seed GEMM runs | per-workload-class speedup, selector stability, signal-runtime correlation |
| `H2` | `gemm_reportable`, `layernorm_reportable`; later `layernorm_v2_small_reportable` and `layernorm_v2_large_reportable` | `compute_lite`, `memory_lite`, later `memory_activity_lite` | matched-budget profiled runs on both kernel families, plus regime-split LayerNorm follow-up | cross-kernel profiling-gain comparison, regime-specific LayerNorm comparison, counter availability plot |
| `H3` | `gemm_aligned_reportable`, `gemm_reportable` | Tier 0 cheap signals and held-out runtime | aligned vs representative GEMM run groups | aligned-vs-representative speedup figure, workload-class breakdown |
| `H4` | `gemm_reportable`, `layernorm_reportable`; later `gemm_v2_reportable` and ablation-only GEMM v2 groups | Tier 0 plus whichever Tier 1 signals motivated the revision | revised-selector run groups under unchanged budgets, later expanded-space ablation runs | revised-vs-current selector comparison, opportunity case-study figure, frontier-only versus full-v3 ablation |
| `H5` | `gemm_v3_reportable`, `gemm_v3_aligned_reportable`, `gemm_v3_schedule_diag` | Tier 0 shape-relative frontier features, `compute_lite`, and diagnostic `compute_schedule_diag` when needed | representative GEMM v3 mapping, selector ablation, and schedule-diagnostic follow-up | parent-vs-v4-vs-random comparison, frontier-only-vs-profiled ablation, chosen-family-vs-best-family frontier diagnostic |

## Ablation Discipline

The paper should avoid arbitrary tuner growth. Every selector revision must answer all of these:

1. What failure mode was observed?
2. Which bottleneck category does it correspond to?
3. Which signals support that diagnosis?
4. Which knob response does the revised heuristic favor?
5. What matched-budget comparison will show whether the revision helped?

If those questions cannot be answered, the revision does not belong in the ablation plan.
