# Tuning Theory And Knob Space

Purpose: define the tunable decision surface for the project and explain why each knob family matters physically.
Status: Backbone
Update Rule: update only when a knob family is added, removed, or re-scoped for the research program.
Feeds Paper Sections: Method, Tuning Space, Discussion
Depends On: [../01_project_charter.md](../01_project_charter.md), [../specs/kernel_registry.md](../specs/kernel_registry.md), [../specs/config_space_generator.md](../specs/config_space_generator.md), [01_research_program.md](01_research_program.md)

## Why The Tuner Is Schedule-First

This project does not start by tuning arbitrary kernel code. It starts by tuning schedule and launch decisions that Triton already exposes naturally. This keeps the research question narrow enough to answer:

- the search space is still large enough to be interesting,
- the knobs have clear physical meaning,
- and the selector can be judged on how well it reasons about bottlenecks rather than on hidden algorithmic changes.

Algorithmic or kernel-variant tuning is allowed later only if the schedule-first study reaches a clear limit that justifies broader scope.

## Knob Families

| Knob Family | What It Changes Physically | Likely Upside | Likely Failure Mode | Applies To | Scope |
| --- | --- | --- | --- | --- | --- |
| `block_m`, `block_n` | output tile geometry and reuse footprint | better reuse, better tensor-core utilization, fewer launches | larger shared-memory footprint, register pressure, masked-edge inefficiency | GEMM | In scope now |
| `block_k` | reduction depth per tile | better reuse and fewer memory rounds | larger live state, more register pressure, occupancy loss | GEMM | In scope now |
| `group_size_m` | grouped launch ordering along the M dimension | better wave ordering and cache/locality behavior on asymmetric GEMM shapes | weak benefit on square cases, extra search burden if admitted too early | GEMM | In scope now |
| `num_warps` | work distribution and issue width per program | better latency hiding and throughput | occupancy collapse, math-pipe throttling, oversubscription | GEMM, LayerNorm | In scope now |
| `num_stages` | software pipelining depth | hides latency, improves overlap | higher register use, higher shared-memory pressure | GEMM, LayerNorm | In scope now |
| `block_size` | per-row work granularity and reduction footprint | better normalization throughput, fewer loop trips | wasted work on short rows, pressure on registers and scheduling | LayerNorm | In scope now |
| `rows_per_program` | how many rows one LayerNorm program handles | better amortization and launch efficiency on larger-row groups | lower flexibility or reduced latency sensitivity on small-batch cases | LayerNorm | Evaluated in Phase 3; retire from mainline |
| vectorization/access granularity | bytes moved per instruction and access pattern | better memory efficiency, fewer LSU instructions | alignment sensitivity, wasted bandwidth, higher pressure per wave | GEMM, LayerNorm | Planned later |
| `split_k` | parallel decomposition along reduction dimension | more parallelism for long reductions and an extra schedule family beyond tile-only choices | reduction overhead, extra synchronization, launch cost | GEMM | Evaluated in Phase 3; retire from mainline |
| persistent/work decomposition choices | residency and wave scheduling pattern | steadier occupancy, better cache behavior on some shapes | starvation, underutilization, harder correctness/debug path | GEMM | Planned later |
| swizzle/layout permutations | mapping from logical tile to memory or shared-memory layout | reduced bank conflicts or better locality | brittle wins, shape-specific regressions | kernel-specific | Planned later |

## Kernel-Family-Specific Decision Surfaces

### GEMM

The current and near-term GEMM tuner is expected to reason over:

- output tile geometry: `block_m`, `block_n`
- reduction tile depth: `block_k`
- grouped launch ordering: `group_size_m`
- launch-scale parallelism: `num_warps`
- pipeline depth: `num_stages`

Archived or diagnostic-only GEMM surface:

- reduction decomposition: `split_k`

Planned GEMM extensions after the completed Phase 3 split-`k` evaluation, only if new evidence justifies them:

- vectorized load/store variants
- persistent scheduling or tile ordering variants

### LayerNorm

The current LayerNorm tuner is intentionally narrower:

- per-row block size: `block_size`
- warp count: `num_warps`
- pipeline depth: `num_stages`

LayerNorm remains the memory-bound contrast case, but the current evidence shows that it
must be interpreted as at least two regimes (`small_batch` and `large_batch`) rather than
as one pooled result.

Archived or diagnostic-only LayerNorm surface:

- rows per program: `rows_per_program`

## What A Proper Kernel Tuner Looks Like In This Project

A proper kernel tuner for this study should:

1. expose only knobs with clear, defensible physical meaning,
2. track how those knobs affect resources and bottlenecks,
3. use cheap signals to eliminate obvious losers,
4. spend limited profiling budget only where additional evidence can plausibly change the ranking,
5. and record enough reasoning that each selector revision can be justified in the paper.

The goal is not to search every plausible knob. The goal is to search the right knobs well enough to support a scientific argument.

## Knob-To-Signal Matrix

| Knob | Expected Effect | Observable Signals | Candidate Interventions |
| --- | --- | --- | --- |
| larger `block_m` / `block_n` | more arithmetic per tile, more reuse, larger footprint | tensor activity, shared-memory bytes, register count, occupancy | enlarge tiles on compute-heavy shapes; shrink tiles if occupancy or shared memory collapses |
| larger `block_k` | fewer reduction rounds, more reuse | tensor activity, long scoreboard stall, register count | increase `block_k` when compute utilization is low and memory pressure is manageable |
| larger `num_warps` | more parallel issue capacity | occupancy estimate, warps active, math-pipe throttle, lg throttle | raise warps when latency hiding is poor; lower if occupancy or throttle worsens |
| larger `num_stages` | deeper software pipeline | long scoreboard stall, register count, shared-memory bytes | increase stages if memory latency dominates and resources allow; reduce if registers become excessive |
| larger `block_size` | fewer reduction passes for LayerNorm | dram throughput, lg throttle, occupancy | increase for large hidden sizes when memory behavior dominates; reduce if waste and occupancy loss dominate |
| vectorized accesses | fewer memory instructions and better coalescing | global-load bytes, cache hit rate, lg throttle | try vectorization if memory pressure is high and alignment is favorable |
| `split_k` | more parallelism on long reductions and a new family of frontier tradeoffs | runtime first, then schedule-diagnostic counters if needed | archived as a bounded Phase 3 negative-result family; do not keep it in the main reportable GEMM surface |
| persistent scheduling | different residency and wave structure | occupancy, warps active, runtime stability | consider only after baseline schedule knobs are exhausted on large steady-state shapes |

## Scope Discipline

The tuner should only absorb a new knob family when all of these hold:

- a bottleneck in the current space has been observed,
- the new knob plausibly targets that bottleneck,
- the knob can be exposed in a controlled, measurable way,
- and the additional search burden does not undermine matched-budget fairness.

If those conditions do not hold, the knob belongs in the "planned later" column rather than the active search space.

Completed Phase 3 decision:

- `split_k` was the only new GEMM schedule family admitted beyond the Phase 2 v2 space.
- The completed Phase 3 evidence did not justify keeping it in the main reportable GEMM surface.
- `rows_per_program` likewise did not justify staying in the main reportable LayerNorm surface.
- Both knobs remain scientifically useful as archived bounded experiments, but not as current mainline paper-surface knobs.

## Final Mainline Surfaces

The final paper-facing tuning surfaces are now:

- `configs/kernels/gemm_final.yaml`
  - inherits the Phase 2 non-`split_k` GEMM surface
  - keeps `block_m`, `block_n`, `block_k`, `group_size_m`, `num_warps`, and `num_stages`
  - excludes `split_k`
- `configs/kernels/layernorm_final.yaml`
  - inherits the regime-aware LayerNorm surface
  - keeps `block_size`, `num_warps`, and `num_stages`
  - fixes `rows_per_program=1` on the final reportable surface

Paper-facing rule:

- `split_k` and `rows_per_program` stay implemented for archival or diagnostic reproducibility
- they are not part of the final mainline surface used for headline claims
