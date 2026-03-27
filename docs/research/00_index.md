# Research Documentation Index

Purpose: define the research-layer table of contents for `KernelTuner` and explain how the research docs relate to the implementation docs.
Status: Backbone
Update Rule: update when the research package structure changes or a document changes role.
Feeds Paper Sections: all sections indirectly; this file controls the package reading order.
Depends On: [../00_index.md](../00_index.md), [../01_project_charter.md](../01_project_charter.md), [../../visual_computing_revised_proposal.md](../../visual_computing_revised_proposal.md)

## Why This Package Exists

The top-level `docs/` package already defines the implementation and evaluation contracts:

- `docs/specs/` says how the system behaves.
- `docs/adr/` says why fixed implementation decisions were made.
- `docs/research/` says what scientific questions are being asked, how they will be evaluated, and how evidence should be interpreted.

This package is the paper backbone. It should make it possible to answer:

- what the project is trying to prove,
- which tuning knobs and signals matter,
- which experiments are required next,
- how results will be interpreted,
- and how those results map into the eventual paper.

## How To Use This Package

1. Read the backbone docs in order.
2. Check the living registries to see the current evidence state, open opportunities, and which hypotheses are only provisionally answered.
3. Read the latest entries in `logs/` for chronological context.
4. Cross-reference back to `docs/04_experiment_protocol.md` and `docs/specs/` whenever a research idea implies a new implementation requirement.

Current project phase:

- the backbone is now relatively stable
- the main moving documents are the evidence registry, opportunity log, and dated logs
- the package is in Phase 2 analysis-and-synthesis mode rather than tooling-definition mode
- `gpunode2` and `gpunode3` are now treated as one qualified `RTX A6000` pool for new primary studies
- the latest detailed execution record is [logs/2026-03-26_g3_requalification_and_followup_execution.md](logs/2026-03-26_g3_requalification_and_followup_execution.md)
- the latest corrective follow-up record is [logs/2026-03-27_g3_followup_baselinefix_and_v3_retry.md](logs/2026-03-27_g3_followup_baselinefix_and_v3_retry.md)
- the latest implementation-side execution-preparation record is [logs/2026-03-27_phase2_deepening_implementation.md](logs/2026-03-27_phase2_deepening_implementation.md)
- the latest full Phase 2 result interpretation is [logs/2026-03-27_phase2_execution_analysis.md](logs/2026-03-27_phase2_execution_analysis.md)
- the canonical reusable Phase 2 artifact summary lives under `artifacts/analysis/phase2_20260327/`

## Reading Order

1. [01_research_program.md](01_research_program.md)
2. [02_tuning_theory_and_knob_space.md](02_tuning_theory_and_knob_space.md)
3. [03_bottleneck_taxonomy.md](03_bottleneck_taxonomy.md)
4. [04_signal_and_profiling_plan.md](04_signal_and_profiling_plan.md)
5. [05_workload_matrix_and_case_studies.md](05_workload_matrix_and_case_studies.md)
6. [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md)
7. [07_experiment_campaign_plan.md](07_experiment_campaign_plan.md)
8. [08_evidence_registry.md](08_evidence_registry.md)
9. [09_opportunity_log.md](09_opportunity_log.md)
10. [10_paper_outline_and_figure_plan.md](10_paper_outline_and_figure_plan.md)
11. [logs/](logs/)

## Research Package Map

| Path | Role | What It Must Answer | Status |
| --- | --- | --- | --- |
| [`01_research_program.md`](01_research_program.md) | Research charter | What is the actual scientific question and what counts as success? | Backbone |
| [`02_tuning_theory_and_knob_space.md`](02_tuning_theory_and_knob_space.md) | Tuning model | What knobs are worth tuning and why? | Backbone |
| [`03_bottleneck_taxonomy.md`](03_bottleneck_taxonomy.md) | Interpretation vocabulary | What bottlenecks are we trying to detect and how will we recognize them? | Backbone |
| [`04_signal_and_profiling_plan.md`](04_signal_and_profiling_plan.md) | Signal plan | Which signals justify which tuning actions? | Backbone |
| [`05_workload_matrix_and_case_studies.md`](05_workload_matrix_and_case_studies.md) | Workload plan | Which workloads can falsify the method? | Backbone |
| [`06_hypotheses_and_ablation_plan.md`](06_hypotheses_and_ablation_plan.md) | Hypothesis registry | What exact questions are being tested and how will they be judged? | Backbone |
| [`07_experiment_campaign_plan.md`](07_experiment_campaign_plan.md) | Research execution plan | What to run next, in what order, and why? | Backbone |
| [`08_evidence_registry.md`](08_evidence_registry.md) | Evidence ledger | What evidence exists today and how strong is it? | Living Registry |
| [`09_opportunity_log.md`](09_opportunity_log.md) | Opportunity tracker | What selector or measurement opportunities have been identified from evidence? | Living Registry |
| [`10_paper_outline_and_figure_plan.md`](10_paper_outline_and_figure_plan.md) | Paper assembly plan | Which artifacts and studies feed each paper section, figure, and table? | Backbone |
| [`logs/`](logs/) | Chronology | What changed, what was run, and what was observed in time order? | Log |

## Research Documentation Contracts

- Backbone docs change only when the research direction changes materially.
- Living registries change when evidence or interpretation changes.
- Log entries are append-only and dated.
- Research docs may reference implementation docs, but they should not restate module specs unless the scientific interpretation depends on them.
- No paper claim should be treated as stable unless it is reflected in a backbone doc and supported by the evidence registry.
