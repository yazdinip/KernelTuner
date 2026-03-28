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
| `memory_activity_lite` | LayerNorm | can one lightweight activity-aware recipe distinguish bandwidth-heavy and latency-sensitive LayerNorm regimes better than `memory_lite` alone? |

### Tier 2: diagnostic-only profiling

These signals are for explanation, not matched-budget reportable ranking.

| Counter Set | Role | Reason It Stays Diagnostic |
| --- | --- | --- |
| `shared_diag` | shared-memory investigation | too specialized and potentially fragile for front-line reportable use |
| `compute_schedule_diag` | GEMM schedule-family explanation | intended to explain transfer behavior and split-`k` tradeoffs, not to change the main matched-budget reportable comparison |
| ad hoc development diagnostics | debugging only | not part of a stable counter contract |

## Current Counter Sets

### `compute_lite`

Used for GEMM reportable studies.

- `sm__warps_active.avg.pct_of_peak_sustained_active`
- `smsp__inst_executed.sum`
- `smsp__inst_executed_pipe_tensor_op_hmma.avg`
- `smsp__pipe_tensor_op_hmma_cycles_active.avg`
- `smsp__warp_issue_stalled_math_pipe_throttle_per_warp_active.pct`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct`

Operational notes:

- reportable use now assumes `kernel_name_regex: matmul_kernel`
- live validation on the pinned `RTX A6000` stack established `6/6` counter availability when `ncu` is on `PATH`

### `memory_lite`

Used for LayerNorm reportable studies.

- `dram__bytes.avg`
- `dram__throughput.avg.pct_of_peak_sustained_elapsed`
- `l1tex__t_bytes_pipe_lsu_mem_global_op_ld.avg`
- `l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate`
- `smsp__warp_issue_stalled_lg_throttle_per_warp_active.pct`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct`

Operational notes:

- reportable use now assumes `kernel_name_regex: layer_norm_kernel`
- live validation on the pinned `RTX A6000` stack established `6/6` counter availability when `ncu` is on `PATH`

### `shared_diag`

Diagnostic-only.

- `l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld.avg`
- `l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st.avg`
- `l1tex__data_pipe_lsu_wavefronts_mem_shared.avg`
- `smsp__warp_issue_stalled_short_scoreboard_per_warp_active.pct`

Operational notes:

- this set remains diagnostic-only even when availability is high
- it is appropriate for explanation and case studies, not matched-budget superiority claims

### `compute_schedule_diag`

Phase 3 GEMM diagnostic-only set for schedule-family explanation.

- `sm__warps_active.avg.pct_of_peak_sustained_active`
- `smsp__inst_executed_pipe_tensor_op_hmma.avg`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct`
- `dram__throughput.avg.pct_of_peak_sustained_elapsed`
- `l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate.pct`

Operational notes:

- this set is diagnostic-only by design
- it exists to explain why a chosen GEMM family wins or fails after the frontier is fixed
- it should not be promoted into the main matched-budget reportable comparison without a later explicit validation pass

### `memory_activity_lite`

Phase 2 LayerNorm profiling set for regime-aware follow-up studies.

- `dram__bytes.avg`
- `dram__throughput.avg.pct_of_peak_sustained_elapsed`
- `l1tex__t_bytes_pipe_lsu_mem_global_op_ld.avg`
- `l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate.pct`
- `sm__warps_active.avg.pct_of_peak_sustained_active`
- `smsp__warp_issue_stalled_lg_throttle_per_warp_active.pct`
- `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct`

Operational notes:

- this set extends `memory_lite` with one activity/occupancy signal
- it is intended for the split `small_batch` / `large_batch` Phase 2 LayerNorm studies
- it should be preferred over `memory_lite` for new LayerNorm v2 reportable work

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

## Attribution And Status Discipline

Tier 1 profiling is only scientifically useful if the profiler row can be attributed to the intended Triton kernel.

Current rules:

- reportable Tier 1 counter sets must declare `kernel_name_regex`
- the profiler must either attribute one intended kernel row or mark the measurement as unusable
- ambiguous or unattributable profiler output should be recorded explicitly rather than treated as partially successful evidence

Current profiler status meanings:

| Status | Meaning | Reportable Tier 1 Use |
| --- | --- | --- |
| `success` | counters were collected and attributed cleanly | yes |
| `unsupported_counter` | Nsight ran but one or more requested counters were unavailable | only if the counter-availability threshold still passes |
| `no_profile_data` | profiler output could not be attributed to the intended kernel row | no |
| `timeout` | profiling exceeded the configured timeout | no |
| `invocation_failed` | Nsight invocation failed for reasons other than unsupported counters | no |
| `tool_unavailable` | `ncu` is not available in the environment | no |

## Reportable Signal Rules

- Tier 1 counters only count as reportable evidence if the configured availability threshold is met.
- Tier 1 counters only count as reportable evidence if kernel attribution is defensible.
- If a counter set falls below the threshold, it is downgraded to diagnostic-only for that batch.
- Diagnostic-only results may explain a case study, but they may not support matched-budget superiority claims by themselves.

## Current Operational Status

As of March 27, 2026:

- `compute_lite` and `memory_lite` have both passed live validation on the current `RTX A6000` environment
- `memory_activity_lite` has also passed live validation on the current `RTX A6000` environment
- `shared_diag` remains intentionally diagnostic-only
- `compute_schedule_diag` is admitted for Phase 3 mechanism work but still awaits its first live validation and execution pass
- a fresh GPU shell may still require explicit CUDA path export before `ncu` is visible

Operational requirement on fresh shells:

- use `scripts/bootstrap_env.sh` when possible
- if the shell still does not expose `ncu`, export:
  - `CUDA_HOME=/usr/local/cuda-12.9`
  - `PATH=$CUDA_HOME/bin:$PATH`
  - `LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}`

## Methodological Notes From The First Long Execution Block

The completed `gpunode3` requalification and follow-up campaigns added two practical constraints that should inform future reportable studies:

- The current representative LayerNorm workload spans at least two profiling regimes.
  - `large_batch, hidden=4096` behaves like a bandwidth-heavy case with very high DRAM throughput.
  - `small_batch, hidden=4096` shows lower throughput and stronger long-scoreboard behavior.
  - Future LayerNorm interpretation should therefore remain workload-class-aware, and the next diagnostic cycle may need one additional activity or occupancy signal before a strong paper claim is made.

- Default baselines must be valid for every held-out shape in a workload program.
  - If the declared `default_config` is invalid for part of the workload matrix, cross-run primary metrics may become partially missing and the resulting study should remain provisional.
  - This now matters concretely for LayerNorm and should be treated as part of future reportability discipline.

## Methodological Notes From The Corrected Follow-up Cycle

The March 27, 2026 corrective follow-up cycle added two more signal-level conclusions:

- Fixing the LayerNorm baseline removed the main methodological confound, but did not reverse the `H2` result.
  - The corrected `h2_followup_g3_baselinefix` study still left `H2` unsupported.
  - LayerNorm profiling did produce a positive matched-budget gain over `prune_rank`, but the gain was too small to satisfy the pre-registered margin.
  - Current implication: `memory_lite` is usable and directionally informative, but it is not yet strong enough to support the intended “profiling helps LayerNorm more than GEMM” paper claim under the present budget and selector logic.

- The most successful selector improvement so far was not a richer profile rule, but a better compile-frontier construction rule.
  - The `v3_h4_targeted` revision succeeded by changing which GEMM configs entered the benchmarked frontier before profiling.
  - Current implication: for representative GEMM, Tier 0 and config-derived shape features are now more important to the next tuning step than adding more Tier 1 profiling complexity.

## Methodological Notes From The Completed Phase 2 Deepening Pass

The completed Phase 2 v2 studies sharpened the signal interpretation further:

- `memory_activity_lite` was operationally sound but scientifically weak as a universal LayerNorm ranking recipe.
  - In `small_batch`, profiling improved `prune_rank` only marginally.
  - In `large_batch`, profiling regressed against compile-only ranking.
  - Current implication: adding one activity or occupancy signal was not enough by itself to turn LayerNorm profiling into a strong matched-budget story.

- The current LayerNorm v2 knob expansion did not yet activate a new launch-shape family.
  - The selected configs in both Phase 2 LayerNorm regime studies stayed at `rows_per_program=1`.
  - Current implication: the regime split was valuable for interpretation, but the added LayerNorm knob did not become an active tuner lever in this batch.

- The representative GEMM failure on the expanded v2 space is still dominated by frontier construction, not by the lack of more Tier 1 signals.
  - The Phase 2 ablation showed that both `v3_frontier_only` and full `v3_h4_targeted` failed in almost the same way once the frontier collapsed onto oversized masked tiles.
  - Current implication: another signal-only escalation is less justified than a shape-relative or mask-aware frontier correction.

## Methodological Notes For Phase 3

The Phase 3 transfer-safe GEMM pass changes the role of profiling slightly:

- the main reportable GEMM comparison still stays on `compute_lite`
- the new selector revisions rely more heavily on shape-relative Tier 0 and config-derived frontier features before any profiling happens
- `compute_schedule_diag` exists only to explain why one schedule family wins after the frontier is already built

Current implication:

- Phase 3 is not a broad profiling rewrite
- it is a frontier-first corrective pass, with one bounded diagnostic counter set to explain schedule-family behavior if the runtime results warrant it

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
