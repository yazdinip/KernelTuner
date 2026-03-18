# Evidence Registry

Purpose: maintain a structured ledger of what evidence currently exists, what it means, and how much confidence the project should place in it.
Status: Living Registry
Update Rule: update after each completed experiment batch that materially affects interpretation.
Feeds Paper Sections: Results, Discussion, Limitations
Depends On: [06_hypotheses_and_ablation_plan.md](06_hypotheses_and_ablation_plan.md), [07_experiment_campaign_plan.md](07_experiment_campaign_plan.md), [10_paper_outline_and_figure_plan.md](10_paper_outline_and_figure_plan.md)

## Registry Rules

- Keep entries concise and cumulative.
- One row should correspond to one coherent body of evidence, not one observation.
- Distinguish clearly between:
  - evidence that exists,
  - interpretation that follows from it,
  - and unresolved confounds that still limit the claim.

## Current Evidence State

| Evidence ID | Round / Hypothesis | Experiment Config Or Study | Environment | Current Interpretation | Confidence | Unresolved Confounds | Reportable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `E-R0-INIT` | `R0` measurement validity | `gemm_smoke`, `gemm_reportable`, `layernorm_smoke`, `validation_phase` | pinned target is `gpunode2` / `NVIDIA RTX A6000` / CUDA 12.9 | the repo has enough implementation surface to begin the research campaign, but the research-phase measurement gate has not yet been closed | Low | repeatability and counter-availability evidence still needs to be registered under the new research package | No |
| `E-H1-INIT` | `H1` cheap-signal usefulness | `gemm_reportable`, `gemm_aligned_reportable` | same as target environment | no reportable research-phase evidence has yet been recorded; hypothesis remains untested in the registry | Low | representative GEMM runs and selector stability data are still missing from the registry | No |
| `E-H2-INIT` | `H2` profiling value by kernel family | `gemm_reportable`, `layernorm_reportable` | same as target environment | counter sets and workloads are defined, but no accepted cross-kernel evidence has been registered yet | Low | memory-centric and compute-centric profiled runs are not yet logged here | No |
| `E-H3-INIT` | `H3` aligned vs representative GEMM | `gemm_aligned_reportable`, `gemm_reportable` | same as target environment | the aligned-reference and representative workloads are both defined; comparative evidence is still pending | Low | no repeated aligned-vs-representative comparison has yet been registered | No |
| `E-H4-INIT` | `H4` opportunity-guided revision | `prune_rank_revised` on reportable GEMM and LayerNorm | same as target environment | revised-selector evaluation is planned but not yet admitted as evidence | Low | opportunity-guided heuristic changes have not yet been justified by completed study evidence | No |

## Hypothesis Status Snapshot

| Hypothesis | Current Status | Notes |
| --- | --- | --- |
| `H1` | Not evaluated | waiting on representative GEMM campaign evidence |
| `H2` | Not evaluated | waiting on matched-budget profiled GEMM and LayerNorm evidence |
| `H3` | Not evaluated | waiting on aligned vs representative GEMM comparison |
| `H4` | Not evaluated | waiting on opportunity log entries promoted into a revised-selector batch |

## Promotion Rule

Evidence should only be promoted into the paper backbone when:

- the relevant round exit gate has been passed,
- the evidence is marked reportable or explicitly diagnostic in the registry,
- and the interpretation survives at least one repeated or cross-run check appropriate to the claim.
