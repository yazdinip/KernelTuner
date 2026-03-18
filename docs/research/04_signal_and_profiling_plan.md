# Signal And Profiling Plan

Purpose: define the scientific signal strategy for the tuner and separate reportable signals from diagnostic-only evidence.
Status: Backbone
Update Rule: update when a signal tier changes, a counter set changes role, or a signal is promoted or demoted between reportable and diagnostic use.
Feeds Paper Sections: Method, Experimental Setup, Failure Analysis
Depends On: [../04_experiment_protocol.md](../04_experiment_protocol.md), [../08_risks_and_open_questions.md](../08_risks_and_open_questions.md), [../specs/signal_collection.md](../specs/signal_collection.md), [../specs/profiling_adapter.md](../specs/profiling_adapter.md), [03_bottleneck_taxonomy.md](03_bottleneck_taxonomy.md)

## Signal Tiers

### Tier 0: broad cheap signals

These are collected for the broad candidate set and are intended to support pruning and coarse ranking.

| Signal | Why It Exists | Primary Use |
| --- | --- | --- |
| compile success / failure | separates unusable candidates from usable ones | pruning |
| correctness status | ensures performance claims are only made for valid candidates | gating |
| register count | rough proxy for live-state pressure | pruning, coarse ranking |
| shared-memory bytes | rough proxy for local-storage footprint | pruning, coarse ranking |
| occupancy estimate | rough proxy for residency and latency-hiding headroom | pruning, coarse ranking |

These signals are cheap enough to collect broadly, but they are not assumed to be sufficient for final ranking.

### Tier 1: matched-budget profiling

These signals may be used by the tuner during real selection, but only on a calibration subset and only when counter availability is good enough.

| Counter Set | Intended Kernel Family | Main Questions |
| --- | --- | --- |
| `compute_lite` | GEMM | is the kernel compute-limited, tensor-underutilized, or stalled by pipeline/scoreboard effects? |
| `memory_lite` | LayerNorm | is the kernel bandwidth-limited, latency-limited on memory, or suffering from poor memory efficiency? |

### Tier 2: diagnostic-only profiling

These signals are for explanation, not matched-budget reportable ranking.

| Counter Set | Role | Reason It Stays Diagnostic |
| --- | --- | --- |
| `shared_diag` | shared-memory investigation | too specialized and potentially fragile for front-line reportable use |
| ad hoc development diagnostics | debugging only | not part of a stable counter contract |

## Current Counter Sets

### `compute_lite`

Used for GEMM reportable studies.

- `sm__warps_active.avg.pct_of_peak_sustained_active`
- `smsp__inst_executed.sum`
- `smsp__inst_executed_pipe_tensor_op_hmma`
- `smsp__pipe_tensor_op_hmma_cycles_active`
- `smsp__warp_issue_stalled_math_pipe_throttle_per_warp_active`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active`

### `memory_lite`

Used for LayerNorm reportable studies.

- `dram__bytes`
- `dram__throughput`
- `l1tex__t_bytes_pipe_lsu_mem_global_op_ld`
- `l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate`
- `smsp__warp_issue_stalled_lg_throttle_per_warp_active`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active`

### `shared_diag`

Diagnostic-only.

- `l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld`
- `l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st`
- `l1tex__data_pipe_lsu_wavefronts_mem_shared`
- `smsp__warp_issue_stalled_short_scoreboard_per_warp_active`

## Signal Family Plan

| Signal Family | Question It Answers | Bottlenecks It Helps Distinguish | Tuning Decisions It Can Justify | Trust Limits |
| --- | --- | --- | --- | --- |
| register count + occupancy estimate | is the candidate obviously resource-heavy? | register pressure, occupancy collapse | lower `num_stages`, lower `num_warps`, smaller tiles | can over-penalize kernels that still win despite low occupancy |
| shared-memory bytes | is the tile footprint likely too large? | shared-memory pressure | smaller tiles, fewer stages | does not prove bank conflicts by itself |
| warps active | is the device seeing enough useful resident work? | compute under-utilization, occupancy issues | larger tiles, more warps, different schedule order | interpretation depends on problem size and workload class |
| tensor activity | are tensor-core paths being used effectively? | compute under-utilization | larger tiles, larger `block_k`, revised warp scale | meaningful mainly for tensor-core GEMM cases |
| DRAM throughput + global-load volume | is the kernel dominated by data movement? | memory bandwidth pressure | more reuse, vectorization, different tile geometry | high throughput can indicate success rather than a bottleneck |
| cache hit rate | is memory efficiency poor? | latency-bound or bandwidth-limited memory behavior | reuse-oriented tile changes, vectorization | hit-rate interpretation depends on workload and access pattern |
| long-scoreboard stall | is the kernel waiting on dependent memory or pipeline progress? | latency-bound memory behavior | more staging, different tile shapes, different warp scale | can be fragile across profiler modes and counters |
| lg throttle | is the LSU path saturated or pressured? | memory latency and LSU pressure | different access granularity, more reuse, staging | often needs to be interpreted together with throughput and scoreboard |
| shared-memory conflict counters | is local memory organization itself a limiter? | shared-memory conflict/pressure | layout changes, block-shape changes | diagnostic-only until availability and stability are proven |

## Reportable Signal Rules

- Tier 1 counters only count as reportable evidence if the configured availability threshold is met.
- If a counter set falls below the threshold, it is downgraded to diagnostic-only for that batch.
- Diagnostic-only results may explain a case study, but they may not support matched-budget superiority claims by themselves.

## Counter Availability Risk

Profiler counters are not equally reliable. The research program therefore treats counter availability as part of the evidence, not as an invisible tooling detail.

Required handling:

- track per-counter non-null fraction,
- record whether the counter set passed its acceptance threshold,
- separate "unsupported" from "missing because not collected",
- and explicitly mark a study non-comparable if the ranking logic depended on counters that did not meet acceptance rules.

## Profiler Perturbation Risk

Profiling changes execution conditions. The research plan therefore distinguishes:

- authoritative benchmark timings from the benchmark harness,
- profiler-derived counters from Nsight Compute,
- and development diagnostics from tools such as `nsys`.

Profiler-collected timings are not authoritative runtime measurements for matched-budget comparison.

## Promotion And Demotion Rule

A signal may be promoted from diagnostic-only to reportable only when:

- it is available consistently enough,
- it maps cleanly to a bottleneck category,
- it justifies a concrete knob intervention,
- and it improves explanation or ranking on more than one isolated case.

A signal should be demoted when it becomes unreliable, overly workload-specific, or too difficult to interpret cleanly in the paper.
