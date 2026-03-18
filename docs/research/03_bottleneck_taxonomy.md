# Bottleneck Taxonomy

Purpose: define the shared bottleneck vocabulary used to interpret profiling and selector behavior.
Status: Backbone
Update Rule: update only when a new bottleneck category becomes necessary or an existing category is split or merged.
Feeds Paper Sections: Background, Method, Failure Analysis, Discussion
Depends On: [../04_experiment_protocol.md](../04_experiment_protocol.md), [../specs/profiling_adapter.md](../specs/profiling_adapter.md), [02_tuning_theory_and_knob_space.md](02_tuning_theory_and_knob_space.md)

## Interpretation Rule

No single counter is a bottleneck by itself. A bottleneck category should only be assigned when:

- runtime behavior supports the diagnosis,
- the relevant signals are available and internally consistent,
- and the diagnosis points to a plausible tuning response.

This taxonomy exists to keep the selector and the paper honest. It prevents "counter chasing" without mechanism.

## Bottleneck Categories

| Category | Symptoms | Plausible Evidence | Likely Helpful Knobs | Common False Positives |
| --- | --- | --- | --- | --- |
| compute under-utilization | low throughput on compute-heavy shapes without obvious memory saturation | low warps active, low tensor activity, low math-pipe use | larger tiles, larger `block_k`, more warps | small problem size, launch overhead, masked edges |
| memory bandwidth pressure | throughput plateaus while memory traffic is high | high DRAM throughput, large global-load volume, low cache effectiveness | larger reuse tiles, access vectorization, better work decomposition | high traffic caused by inefficiency rather than a true bandwidth wall |
| latency-bound memory behavior | execution waits on data despite modest bandwidth | high long-scoreboard stall, high lg throttle, low utilization | more staging, different tile shape, more warps | profiler replay artifacts, under-occupied kernels |
| shared-memory conflict or pressure | local-storage path limits progress | high bank-conflict indicators, large shared-memory footprint, low effective occupancy | smaller tiles, layout changes, block-shape changes | high shared-memory allocation without actual bank conflicts |
| register-pressure / occupancy collapse | hardware cannot keep enough work resident | high register count, low occupancy estimate, poor warps active | lower `num_stages`, lower `num_warps`, smaller tiles | occupancy estimate can be misleading if the kernel is not occupancy-limited |
| synchronization / scheduling inefficiency | progress is limited by wave structure or reduction overhead | runtime regressions without clear memory or compute explanation, instability across shapes | work decomposition changes, persistent scheduling, `split_k` only when justified | simple noise, cache effects, host-side disturbances |

## Category Notes

### Compute under-utilization

This category matters most on square or compute-heavy GEMM shapes. The core question is whether the kernel is leaving tensor-core or arithmetic throughput unused because the tile geometry or warp scale is too conservative.

### Memory bandwidth pressure

This category matters when data movement is already close to the practical limit for the device. In that case, further schedule changes should focus on reuse or efficiency rather than just increasing parallelism.

### Latency-bound memory behavior

This is different from raw bandwidth pressure. A kernel may not saturate DRAM but still spend cycles waiting on dependent memory operations. This is where `num_stages`, warp scale, and tile geometry can matter most.

### Shared-memory conflict or pressure

This category is especially important once layout-sensitive or larger-tile variants are introduced. It should remain diagnostic-only until the relevant counters are stable enough to interpret confidently.

### Register-pressure / occupancy collapse

This is the most important "cheap signal" category because it can often be detected without expensive profiling. It is also the easiest to over-interpret, so it must be paired with held-out outcomes rather than treated as a universal rule.

### Synchronization / scheduling inefficiency

This is the catch-all category for effects that are real but not cleanly explained by the other buckets. It is a valid category, but it should trigger caution and stronger diagnostic requirements before motivating a selector change.

## Taxonomy-To-Selector Use

The selector is expected to use this taxonomy in three ways:

1. **Pruning:** reject obviously bad regions such as severe occupancy collapse or consistent compile/resource failure.
2. **Ranking:** reorder surviving candidates when the observed bottleneck suggests a specific knob direction.
3. **Diagnosis:** explain missed selections, instability, or regressions after the fact.

If a planned selector revision does not correspond to a taxonomy category, it does not belong in the paper backbone.
