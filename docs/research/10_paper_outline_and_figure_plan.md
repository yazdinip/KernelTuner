# Paper Outline And Figure Plan

Purpose: map the research docs and generated artifacts directly onto the eventual paper structure.
Status: Backbone
Update Rule: update whenever a required paper section, figure, or table changes.
Feeds Paper Sections: all sections directly
Depends On: [01_research_program.md](01_research_program.md), [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [08_evidence_registry.md](08_evidence_registry.md)

## Paper Outline

| Section | Purpose | Primary Source Docs | Primary Artifact Sources |
| --- | --- | --- | --- |
| Introduction | motivate bottleneck-aware Triton tuning and state the research question | `01_research_program.md`, proposal | manual prose plus final hypothesis summary |
| Background and Tuning Space | explain schedule-first tuning and knob families | `02_tuning_theory_and_knob_space.md`, `03_bottleneck_taxonomy.md` | knob-to-signal matrix, bottleneck taxonomy table |
| Method | describe the selector ladder, signal tiers, workload program, and matched-budget protocol | `04_signal_and_profiling_plan.md`, `05_workload_matrix_and_case_studies.md`, `06_hypotheses_and_ablation_plan.md` | protocol tables, workload tables, study configs |
| Experimental Setup | pin the environment, workloads, and evaluation rules | `05_workload_matrix_and_case_studies.md`, top-level protocol and environment docs | environment provenance, experiment configs |
| Results | answer `H1` through `H4` with cross-run evidence | `06_hypotheses_and_ablation_plan.md`, `08_evidence_registry.md` | `cross_run_summary.json`, stability reports, held-out comparison tables |
| Failure Analysis and Opportunities | explain wins, misses, and revised-selector behavior | `03_bottleneck_taxonomy.md`, `09_opportunity_log.md` | opportunity catalog, bottleneck signatures, case-study plots |
| Limitations | state what the study does not claim | `01_research_program.md`, `08_evidence_registry.md` | hypothesis status table, unresolved-confounds summary |
| Conclusion | summarize what was learned about lightweight bottleneck-aware tuning | final evidence registry and paper draft | final hypothesis summary |

## Required Tables

| Table ID | Table | Source |
| --- | --- | --- |
| `T1` | Research question, scope, and success criteria | `01_research_program.md` |
| `T2` | Knob families and expected physical effects | `02_tuning_theory_and_knob_space.md` |
| `T3` | Bottleneck taxonomy | `03_bottleneck_taxonomy.md` |
| `T4` | Signal tiers and counter sets | `04_signal_and_profiling_plan.md` |
| `T5` | Workload matrix by kernel family and class | `05_workload_matrix_and_case_studies.md` |
| `T6` | Selector ladder and hypothesis mapping | `06_hypotheses_and_ablation_plan.md` |
| `T7` | Final hypothesis status summary | `08_evidence_registry.md` and final cross-run summary |

## Required Figures

| Figure ID | Figure | Claim It Supports | Source Study / Artifact |
| --- | --- | --- | --- |
| `F1` | strategy speedup by workload class on representative GEMM v2 | selector quality is workload-dependent and the expanded space preserves the representative GEMM miss | `gemm_v2_baseline_mapping` |
| `F2` | aligned vs representative GEMM comparison under v2 | aligned workloads can overstate selector quality | `gemm_v2_aligned_reference` vs `gemm_v2_baseline_mapping` |
| `F3` | LayerNorm regime split: `small_batch` vs `large_batch` profiling outcomes | profiling helps differently by LayerNorm regime and not uniformly by kernel family | `layernorm_v2_small_regime` and `layernorm_v2_large_regime` |
| `F4` | repeated-run stability by strategy | results are or are not stable enough for strong claims | stability reports from repeatability mode |
| `F5` | counter availability by counter set | reportable vs diagnostic profiling evidence is clearly separated | counter-availability reports |
| `F6` | signal-to-runtime correlation overview | some cheap signals are informative and others are weak | correlation artifacts from GEMM and LayerNorm runs |
| `F7` | revised-selector transfer ablation | measured failure analysis can motivate a better heuristic, but the same heuristic can fail to transfer when the space expands | `gemm_v2_selector_ablation`, `gemm_v2_baseline_mapping`, plus the earlier `h4_retry_g3` retry as context |
| `F8` | bottleneck or opportunity distribution across workload classes | failure modes are structured rather than random | bottleneck signatures and opportunity catalog |

## Current Figure Readiness

| Figure ID | Current Readiness | Notes |
| --- | --- | --- |
| `F1` | Strongly provisionally backed | `gemm_v2_baseline_mapping` is now the strongest representative GEMM source because it preserves the original failure direction on the expanded space and ties that result to stable config families |
| `F2` | More strongly provisionally backed | the completed `gemm_v2_aligned_reference` study preserves the direction that aligned GEMM flatters the selector ladder more than representative GEMM |
| `F3` | Strongly provisionally backed as a regime-split negative-result figure | the completed `layernorm_v2_small_regime` and `layernorm_v2_large_regime` studies replace the old pooled LayerNorm story with a cleaner weak-versus-negative regime split |
| `F4` | Provisionally backed | repeatability and robustness evidence now exists in both the original validation block and the completed v2 studies; final paper usage should rely on archived artifact paths |
| `F5` | Provisionally backed | Tier 1 counter-set acceptance has live evidence on the current A6000 stack, including `memory_activity_lite` |
| `F6` | Provisionally backed | correlation artifacts still need interpretation and pruning, but the v2 studies now give a cleaner set of candidate figure sources |
| `F7` | Strongly provisionally backed as a transfer-failure ablation | the project now has both sides of the story: the narrow-space `h4_retry_g3` success and the expanded-space `gemm_v2_selector_ablation` failure, which together make a stronger mechanism figure than a pure success plot alone |
| `F8` | Strongly provisionally backed | bottleneck-signature, opportunity, and diagnostic artifacts now include the completed v2 studies and the reusable Phase 2 analysis bundle |

## Current Strongest Artifact Sources

- Representative GEMM expanded-space baseline mapping:
  - `gemm_v2_baseline_mapping` `run_20260327T164637Z_0403b989`
- Representative GEMM selector ablation:
  - `gemm_v2_selector_ablation` `run_20260327T175823Z_376d6bbc`
- LayerNorm regime split:
  - `layernorm_v2_small_regime` `run_20260327T183157Z_53565cba`
  - `layernorm_v2_large_regime` `run_20260327T183158Z_37695a2d`
- Aligned GEMM v2 context:
  - `gemm_v2_aligned_reference` `run_20260327T190124Z_3a34cdc7`
- Narrow-space revised-selector success context:
  - `h4_retry_g3` `run_20260327T035659Z_10f9baec`
- Canonical summary bundle:
  - `artifacts/analysis/phase2_20260327/`
- Full chronological execution record:
  - `docs/research/logs/2026-03-26_g3_requalification_and_followup_execution.md`
  - `docs/research/logs/2026-03-27_g3_followup_baselinefix_and_v3_retry.md`
  - `docs/research/logs/2026-03-27_phase2_execution_analysis.md`

## Current Writing-Ready Claims

- Cheap compile signals are useful for pruning but not sufficient for representative GEMM ranking, and that result survives the expanded v2 space.
  - strongest source: `gemm_v2_baseline_mapping`
- Aligned GEMM still overstates selector quality relative to the representative workload.
  - strongest sources: `gemm_v2_baseline_mapping`, `gemm_v2_aligned_reference`, supported by the earlier broad studies
- LayerNorm should be written as a regime-aware mixed result, not a pooled profiling success.
  - strongest sources: `layernorm_v2_small_regime`, `layernorm_v2_large_regime`
- A frontier-aware revised selector can work on a narrower space, but the current rule does not transfer to the expanded v2 GEMM space.
  - strongest sources: `h4_retry_g3`, `gemm_v2_baseline_mapping`, `gemm_v2_selector_ablation`

## Current Analysis Goal

The next synthesis phase should not add new top-level claims. It should:

- lock the representative GEMM story to the Phase 2 expanded-space evidence,
- write the revised-selector result as a transfer/ablation story rather than a pure win,
- and turn LayerNorm from one pooled negative result into a regime-aware secondary story.

## Figure Readiness Rules

A figure is ready for the paper only when:

- its source study is reportable or explicitly labeled diagnostic,
- the relevant hypothesis status is up to date,
- and the figure can be reproduced from recorded artifacts without manual hidden steps.

Current caution:

- the first validation batch is useful for planning and interpretation, but some artifacts still live in expiring scratch paths
- any figure promoted into the final paper should come from archived or rerun evidence with stable provenance

## What Counts As Unproductive Experimentation

An experiment is not helping the paper if it does not:

- move one hypothesis toward support, rejection, or inconclusive,
- create a new admitted opportunity entry,
- or fill a missing figure/table source.

If a planned run does none of those things, it should be deprioritized.
