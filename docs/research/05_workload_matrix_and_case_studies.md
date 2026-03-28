# Workload Matrix And Case Studies

Purpose: define the workload program for the paper and explain why each workload class exists.
Status: Backbone
Update Rule: update when a reportable workload class or case-study role changes.
Feeds Paper Sections: Experimental Setup, Results, Limitations
Depends On: [../03_execution_environment.md](../03_execution_environment.md), [../04_experiment_protocol.md](../04_experiment_protocol.md), [../adr/ADR-005-primary-kernel-first.md](../adr/ADR-005-primary-kernel-first.md), [03_bottleneck_taxonomy.md](03_bottleneck_taxonomy.md)

## Case-Study Roles

The research package uses two kernel families with distinct roles:

- **Primary case study:** GEMM
- **Validation case study:** LayerNorm

GEMM is the main place where the selector must prove it can reason about a meaningful Triton schedule space. LayerNorm is the contrast case used to test whether profiling helps more on a memory-bound workload than on a compute-heavy one.

## GEMM Program

### Reportable representative GEMM study

Config: `configs/experiments/gemm_reportable.yaml`

| Workload Class | Shapes | Why It Exists | Expected Bottlenecks |
| --- | --- | --- | --- |
| `square_compute` | `(1024,1024,1024)`, `(2048,2048,2048)`, `(4096,4096,2048)` | tests compute-heavy steady-state behavior where tile geometry should matter most | compute under-utilization, register pressure, occupancy collapse |
| `m_dominant` | `(4096,1024,1024)`, `(4096,512,2048)`, `(2048,512,4096)` | tests tall-output aspect ratios and changes in tile reuse balance | memory latency, occupancy sensitivity, tile-shape mismatch |
| `n_dominant` | `(1024,4096,1024)`, `(512,4096,2048)`, `(512,2048,4096)` | tests wide-output aspect ratios with different access and reuse behavior | memory pressure, warp scaling, shape-sensitive scheduling |
| `edge_nondivisible` | `(1536,1792,960)`, `(2304,3072,1536)`, `(3584,1536,1280)` | tests masked-edge and irregular-tile effects that aligned workloads can hide | masked overhead, memory inefficiency, schedule brittleness |

### Reportable aligned-reference GEMM study

Config: `configs/experiments/gemm_aligned_reportable.yaml`

| Workload Class | Shapes | Why It Exists |
| --- | --- | --- |
| `aligned_square` | `(512,512,512)`, `(1024,1024,1024)`, `(2048,2048,1024)`, `(2048,2048,2048)`, `(4096,4096,2048)` | preserves the easier, more regular GEMM baseline used to test whether aligned workloads overstate selector quality |
| `aligned_rectangular` | `(4096,2048,1024)` | preserves one non-square but still regular reference point |

This aligned study exists specifically for the workload-representativeness hypothesis. It is not the main reportable workload going forward.

### Phase 3 representative GEMM study

Config: `configs/experiments/gemm_v3_reportable.yaml`

The Phase 3 GEMM study keeps the same representative workload classes but enlarges the schedule space with `split_k`.

- The workload matrix is intentionally unchanged so Phase 3 results can be compared directly against the Phase 2 v2 bundle.
- The new question is whether a transfer-safe frontier policy can still recover near-random-search performance after the space admits one orthogonal schedule family.

### Phase 3 aligned GEMM context study

Config: `configs/experiments/gemm_v3_aligned_reportable.yaml`

This is still a supporting context workload, not the primary optimization target.

- It exists to refresh the `H3` interpretation under the Phase 3 search space.
- It should not replace the representative GEMM study as the main paper-facing truth source.

### Development and smoke GEMM studies

| Study | Config | Role |
| --- | --- | --- |
| smoke | `configs/experiments/gemm_smoke.yaml` | wiring and tool validation only |
| development | `configs/experiments/gemm_development.yaml` | faster iteration on representative classes before full reportable runs |

## LayerNorm Program

### Reportable LayerNorm study

Config: `configs/experiments/layernorm_reportable.yaml`

| Workload Class | Shapes | Why It Exists | Expected Bottlenecks |
| --- | --- | --- | --- |
| `small_batch` | `(128,768)`, `(128,1024)`, `(128,2048)`, `(128,4096)` | tests short-batch regimes where per-row overhead and work granularity dominate | latency-bound memory behavior, under-utilization, block-size mismatch |
| `large_batch` | `(2048,768)`, `(2048,1024)`, `(2048,2048)`, `(2048,4096)` | tests steadier throughput regimes where memory efficiency and warp scaling matter more | bandwidth pressure, lg throttle, occupancy tradeoffs |

### Phase 2 and Phase 3 LayerNorm regime studies

Configs:

- `configs/experiments/layernorm_v2_small_reportable.yaml`
- `configs/experiments/layernorm_v2_large_reportable.yaml`
- `configs/experiments/layernorm_v2_small_microstudy.yaml`
- `configs/experiments/layernorm_v2_large_microstudy.yaml`

Current interpretation:

- LayerNorm is now intentionally split by regime rather than treated as one pooled reportable story.
- The reportable v2 regime studies established the current weak-or-negative result.
- The Phase 3 microstudy exists only to decide whether `rows_per_program` is a real regime lever or dead weight.
- LayerNorm remains a secondary explanatory track, not the main tuner-growth path.

### Development and smoke LayerNorm studies

| Study | Config | Role |
| --- | --- | --- |
| smoke | `configs/experiments/layernorm_smoke.yaml` | wiring and tool validation only |
| development | `configs/experiments/layernorm_development.yaml` | faster iteration on memory-centric tuning behavior |

## Reportable vs Non-Reportable Workloads

### Reportable

- `gemm_reportable`
- `gemm_aligned_reportable`
- `layernorm_reportable`
- `gemm_v2_reportable`
- `gemm_v2_aligned_reportable`
- `layernorm_v2_small_reportable`
- `layernorm_v2_large_reportable`
- `gemm_v3_reportable`
- `gemm_v3_aligned_reportable`

### Development only

- `gemm_development`
- `layernorm_development`
- `gemm_v3_schedule_diag`
- `layernorm_v2_small_microstudy`
- `layernorm_v2_large_microstudy`

### Smoke only

- `gemm_smoke`
- `layernorm_smoke`

Smoke and development runs may be useful for debugging or iteration, but they do not count as final comparative evidence unless explicitly promoted with full protocol compliance.

## Why This Workload Matrix Can Falsify The Method

The workload matrix is intentionally designed so the selector can fail for real reasons:

- aligned GEMM can make tuning look easier than it is,
- irregular GEMM can expose schedule brittleness,
- compute-heavy GEMM tests whether cheap signals actually say anything useful about tensor utilization,
- and LayerNorm tests whether limited profiling matters more on a memory-bound kernel family.

If the selector only works on aligned square GEMM and fails elsewhere, that is a scientifically useful result. The workload matrix is successful only if it can reveal that kind of limitation clearly.

Current Phase 3 workload rule:

- keep the representative GEMM and aligned GEMM class definitions stable while the search space changes
- keep LayerNorm split into `small_batch` and `large_batch`
- use new Phase 3 runs to explain transfer and schedule-family behavior, not to reopen the entire workload program
