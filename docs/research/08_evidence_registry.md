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
| `E-R0-VAL1` | `R0` measurement validity | `validation_rounds` campaign `run_20260322T234810Z_884986d3`; `validation_phase` study `run_20260323T005040Z_99898cc6` | reportable batch executed on the pinned `gpunode2` / `NVIDIA RTX A6000` / CUDA 12.9 stack | the first full validation batch completed successfully; campaign execution, resume, reportability checks, Tier 1 profiling, and study generation all produced usable evidence, so the project may proceed to long-run execution | Medium | current study summary covers `9` runs from a `15`-job campaign because the study spec slices specific groups; important artifacts still live in expiring scratch storage and should be archived or reproduced before paper promotion | Yes |
| `E-R0-PROF-0326` | `R0` profiler revalidation | live `validate-counter-set` revalidation for `gemm_reportable` and `layernorm_reportable` after profiler/reporting integration | `gpunode3` / `NVIDIA RTX A6000` / CUDA 12.9 after explicit CUDA path export | both reportable Tier 1 counter sets validated at `6/6` availability on a fresh A6000 shell; this strengthens operational confidence in long-run execution and documents the `ncu` path requirement | High | this is a requalification / operational check on `gpunode3`, not primary paper evidence for the reportable baseline | No |
| `E-H1-VAL1` | `H1` cheap-signal usefulness | `validation_phase` study `run_20260323T005040Z_99898cc6`, drawing from representative GEMM and aligned GEMM groups in `validation_rounds` | pinned `gpunode2` reportable batch | first-pass evidence currently supports `H1`: cheap compile signals appear useful for pruning, but they do not yet produce a trustworthy final ranking on representative GEMM | Medium | only one homogeneous batch is registered so far; the automated support result should still be confirmed by an additional representative GEMM batch before the paper treats it as strong | Yes |
| `E-H2-VAL1` | `H2` profiling value by kernel family | `validation_phase` study `run_20260323T005040Z_99898cc6`, comparing profiled GEMM and LayerNorm reportable groups | pinned `gpunode2` reportable batch | first-pass evidence does **not** support `H2`: under the current budget, counter set, and selector logic, profiling did not help LayerNorm more than GEMM | Low | this may reflect limited LayerNorm knob surface, too-weak use of profiling features, or insufficient follow-up rather than a durable negative result | Yes |
| `E-H3-VAL1` | `H3` aligned vs representative GEMM | `validation_phase` study `run_20260323T005040Z_99898cc6`, comparing `gemm_aligned_reportable` and `gemm_reportable` groups | pinned `gpunode2` reportable batch | first-pass evidence currently supports `H3`: aligned GEMM makes the strategy ladder look better than the representative workload matrix does | Medium | the current aligned group uses repeatability runs while the representative groups use robustness slicing, so one more explicitly paired confirmation batch is still desirable | Yes |
| `E-H4-VAL1` | `H4` opportunity-guided revision | `validation_phase` study `run_20260323T005040Z_99898cc6`, comparing `prune_rank_revised` against `prune_rank` | pinned `gpunode2` reportable batch | first-pass evidence does **not** support `H4`: the `v2_validation` revised selector did not reliably outperform its parent under unchanged budget | Low | only one revision batch has been admitted so far; the current result is a useful constraint, not a final rejection of opportunity-guided refinement | Yes |

## Hypothesis Status Snapshot

| Hypothesis | Current Status | Notes |
| --- | --- | --- |
| `H1` | Initial support | supported by the first validation batch; confirm with another representative GEMM-focused batch before treating as a strong paper claim |
| `H2` | Initial non-support | not supported by the first validation batch; targeted LayerNorm follow-up is still required before treating this as a strong negative result |
| `H3` | Initial support | supported by the first validation batch; use representative GEMM as the main truth source while confirmation proceeds |
| `H4` | Initial non-support | not supported by the first validation batch; only one evidence-backed revision retry should be admitted next |

## Evidence Source Notes

- The first registered validation batch is real research evidence, not only tooling smoke testing.
- The strongest current evidence source is the `validation_phase` study run `run_20260323T005040Z_99898cc6`, backed by the `validation_rounds` campaign run `run_20260322T234810Z_884986d3`.
- The automated hypothesis labels in generated study outputs are batch-level results.
- Project-level confidence should be taken from this registry, not from one CSV row in isolation.
- Some current artifacts live under expiring scratch space; they should be reproduced or archived before being cited as final paper evidence.

## Promotion Rule

Evidence should only be promoted into the paper backbone when:

- the relevant round exit gate has been passed,
- the evidence is marked reportable or explicitly diagnostic in the registry,
- and the interpretation survives at least one repeated or cross-run check appropriate to the claim.
