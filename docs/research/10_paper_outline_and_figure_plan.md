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
| `F1` | strategy speedup by workload class on representative GEMM | selector quality is workload-dependent | `gemm_reportable` held-out comparison outputs |
| `F2` | aligned vs representative GEMM comparison | aligned workloads can overstate selector quality | `gemm_aligned_reportable` vs `gemm_reportable` cross-run comparison |
| `F3` | profiling-gain comparison for GEMM vs LayerNorm | profiling helps differently by kernel family | `validation_phase` cross-run study |
| `F4` | repeated-run stability by strategy | results are or are not stable enough for strong claims | stability reports from repeatability mode |
| `F5` | counter availability by counter set | reportable vs diagnostic profiling evidence is clearly separated | counter-availability reports |
| `F6` | signal-to-runtime correlation overview | some cheap signals are informative and others are weak | correlation artifacts from GEMM and LayerNorm runs |
| `F7` | opportunity-guided revised selector case study | measured failure analysis can motivate a better heuristic | revised-selector comparison plus opportunity log |
| `F8` | bottleneck or opportunity distribution across workload classes | failure modes are structured rather than random | bottleneck signatures and opportunity catalog |

## Current Figure Readiness

| Figure ID | Current Readiness | Notes |
| --- | --- | --- |
| `F1` | Provisionally backed | the first validation batch already contains representative GEMM strategy results by workload class; a second confirmation batch would strengthen it |
| `F2` | Provisionally backed | aligned-vs-representative evidence exists from the first validation batch, but the paired comparison should be tightened before paper freeze |
| `F3` | Not ready | the first batch did not support `H2`; targeted LayerNorm follow-up is still required |
| `F4` | Provisionally backed | repeatability and robustness evidence exists, but final paper usage should rely on archived or reproduced artifacts |
| `F5` | Provisionally backed | Tier 1 counter-set acceptance has live evidence on the current A6000 stack |
| `F6` | Provisionally backed | first-batch correlation artifacts exist; they still need interpretation and likely pruning for the final paper |
| `F7` | Not ready | the current revised-selector batch did not justify the figure yet |
| `F8` | Provisionally backed | bottleneck-signature and opportunity artifacts exist, but the opportunity log still needs one more evidence-backed cycle |

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
