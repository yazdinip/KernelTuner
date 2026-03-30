# Research Program

Purpose: define the scientific backbone of `KernelTuner` and fix the research posture for the project.
Status: Backbone
Update Rule: update only when the research question, scope, or claim style changes materially.
Feeds Paper Sections: Introduction, Research Question, Contributions, Limitations
Depends On: [../01_project_charter.md](../01_project_charter.md), [../04_experiment_protocol.md](../04_experiment_protocol.md), [../../visual_computing_revised_proposal.md](../../visual_computing_revised_proposal.md)

## Research Question

Can a bottleneck-aware configuration selector use cheap compile-adjacent signals and limited profiling feedback to guide Triton kernel schedule selection better than default settings or equally budgeted naive tuning?

This question is intentionally narrower than "general Triton autotuning." The project is about whether a disciplined, mechanism-aware selector can use limited evidence to spend tuning budget better.

## Central Paper Claim

The paper should be framed as an empirical systems study:

- identify what parts of the Triton schedule space are actually worth tuning,
- identify which hardware or compile-time signals are informative enough to guide tuning,
- test whether those signals improve matched-budget configuration selection,
- and explain the cases where they fail.

The intended claim is not that `KernelTuner` is a universal autotuner. The intended claim is that a bottleneck-aware, schedule-first tuner can sometimes beat default and naive baselines under constrained budget, and that the same experimental machinery can explain negative results where it cannot.

## Positioning Against Prior Work

This research story depends on being explicit about what category of work `KernelTuner` belongs to.

- It is **not** a compiler-scale autoscheduler in the Halide or TVM sense.
- It is **not** a full-kernel CUDA generator or an agentic kernel-synthesis system.
- It is **not** merely a thin wrapper around Triton's built-in autotuning.

Instead, it is a schedule-first Triton tuning study that sits between those categories:

- like Halide and TVM-style autoscheduling, it treats schedule choice as a serious optimization problem,
- like Triton's built-in autotuning, it works over a compact meta-parameter space that practitioners already care about,
- and like external kernel autotuners, it emphasizes candidate generation, correctness validation, bounded benchmarking, and fair strategy comparison.

That middle-ground positioning is important for the paper. It explains why the project is narrow enough to remain interpretable, but still substantial enough to matter scientifically.

For the literature-facing version of this argument, see [12_related_work_and_positioning.md](12_related_work_and_positioning.md).

Final project-level implication:

- cheap compile-adjacent signals are strong enough to prune but not strong enough to carry representative GEMM ranking by themselves,
- narrow heuristic wins do not automatically transfer to expanded spaces,
- bounded negative results can still improve the paper by producing principled keep/drop decisions,
- and a conservative final non-`split_k` mainline selector can recover the strongest representative GEMM result in the project without reopening the research program.

## Fixed Research Posture

The following are fixed for the research program unless a new ADR-level decision replaces them:

- **Tuner scope:** schedule-first
- **Paper style:** empirical systems study
- **Project horizon:** term-sized
- **Primary case study:** GEMM
- **Validation case study:** LayerNorm
- **Execution environment:** one homogeneous Linux CUDA pool, one GPU model
- **Comparator style:** matched-budget baselines
- **Selector style:** heuristic ladder first, learned model optional and late

## What A "Good Tuner" Means Here

Within this project, a good tuner is one that satisfies all of the following:

1. It works inside a fixed, explicit measurement budget.
2. It makes decisions that can be tied to observable bottlenecks or resource tradeoffs.
3. It improves held-out performance or reduces search effort relative to naive baselines.
4. When it fails, the failure can be diagnosed from recorded evidence rather than guessed after the fact.

This definition is stricter than "produces one fast configuration." The tuner must be interpretable enough for research claims and controlled enough for fair comparison.

## Success And Failure Outcomes

The project succeeds if any one of these is supported by reportable evidence:

1. The selector finds better held-out configurations than default or naive baselines under the same budget.
2. The selector reaches comparable held-out performance with less calibration cost.
3. The study shows that the chosen signals are too weak, unstable, or workload-specific to support reliable tuning, and explains why.

The project fails only if it cannot produce a fair, interpretable answer to the research question.

## Scope Boundaries

### In scope

- Triton schedule/configuration decisions
- compile-adjacent and profiler-derived signals
- one pinned GPU environment
- one deep primary kernel family
- one validation kernel family
- matched-budget baseline comparison
- mechanism-level failure analysis

### Out of scope for the paper backbone

- multi-GPU or multi-architecture claims
- production deployment claims
- compiler redesign
- broad claims about all Triton workloads
- unconstrained learned autotuning

## Research Outputs

The research program must produce:

- a bottleneck taxonomy,
- a knob-to-signal theory of tuning,
- a workload matrix designed to falsify the method,
- a pre-registered hypothesis set,
- a sequence of experiment rounds with evidence gates,
- a living evidence registry,
- a living opportunity log,
- and a direct mapping from artifacts to paper sections and figures.

## Negative Result Rule

A negative result is acceptable only if the following are still true:

- budgets were matched fairly,
- reportable and diagnostic evidence were separated,
- the selector's failures can be traced to specific signal weaknesses or workload effects,
- and the paper can say what the project learned about the limits of lightweight bottleneck-aware tuning.

## Current Research Thesis

The working thesis for the project is:

> Many poor Triton schedule choices can be filtered or deprioritized with cheap signals, but strong final selection requires conservative frontier construction plus a small amount of bounded profiling whose value depends strongly on kernel family and workload class.

This thesis is what the rest of the research package is designed to test, refine, or reject.

Literature-facing refinement:

- the project borrows the schedule-search viewpoint from autoscheduling research,
- narrows it to a fixed Triton kernel setting that is closer to practical autotuning workflows,
- and treats explanation quality, matched-budget fairness, and negative-result discipline as first-class contributions rather than afterthoughts.

Final posture after `R6`:

- representative GEMM is the truth source for the paper headline,
- aligned GEMM is supporting context only,
- LayerNorm is a bounded regime-split secondary story,
- `split_k` and `rows_per_program` remain archived diagnostic surfaces rather than final mainline knobs,
- and no new selector-family expansion is part of the current paper-facing program.
