# Initial Validation And Execution Readiness

Purpose: record the first completed research-phase validation batch, the resulting provisional hypothesis statuses, and the operational readiness state before long-run execution.
Status: Log
Update Rule: append-only; do not rewrite past observations except to fix factual errors.
Feeds Paper Sections: none directly; this is chronological support material.
Depends On: [../07_experiment_campaign_plan.md](../07_experiment_campaign_plan.md), [../08_evidence_registry.md](../08_evidence_registry.md), [../09_opportunity_log.md](../09_opportunity_log.md)

## What Changed

- completed the first full validation batch under the new research-execution tooling
- registered a real `validation_rounds` campaign and a real `validation_phase` study as the first coherent research-phase evidence source
- live-tested the profiler, campaign, resume, reportability, and comparison surfaces rather than relying only on unit coverage
- selectively integrated additional profiler/reporting improvements after PR review
- revalidated reportable counter sets on an `RTX A6000` development allocation after the PR integration work

## First Registered Validation Batch

Primary evidence source:

- campaign: `validation_rounds`
- campaign run: `run_20260322T234810Z_884986d3`
- study: `validation_phase`
- study run: `run_20260323T005040Z_99898cc6`

Key facts:

- the full campaign completed with `15` jobs and `0` failed jobs
- the current `validation_phase` study summarizes `9` runs across `3` groups because the study spec slices selected groups from the campaign rather than all campaign jobs
- the resulting study produced the first batch-level statuses for `H1` through `H4`

Current batch-level statuses:

- `H1`: supported
- `H2`: unsupported
- `H3`: supported
- `H4`: unsupported

Interpretation rule:

- these are current batch outcomes, not final project-level conclusions
- the evidence registry remains the authoritative place to assign confidence and next actions

## Operational Revalidation Performed Today

After integrating profiler/reporting improvements from recent PR review:

- reportable Tier 1 counter validation was re-run on `gpunode3` with `NVIDIA RTX A6000`
- both `compute_lite` and `memory_lite` validated at `6/6` available counters
- the main operational caveat is that fresh GPU shells may still need explicit CUDA path export before `ncu` is visible

Practical note:

- use `scripts/bootstrap_env.sh` first
- if `ncu` is still missing, export `/usr/local/cuda-12.9/bin` and `/usr/local/cuda-12.9/lib64`

## What This Means

- the project is no longer in a tooling-definition phase
- the system is credible enough to execute long-running, hypothesis-driven campaigns
- current evidence already constrains the story:
  - cheap compile signals appear useful for pruning but not yet for full ranking
  - aligned GEMM appears too flattering relative to the representative workload
  - the current LayerNorm profiling story needs a more targeted follow-up
  - the first revised selector was not good enough to justify promotion

## Immediate Next Execution Actions

1. Run a narrower `H1` / `H3` confirmation batch centered on representative and aligned GEMM.
2. Run a targeted LayerNorm profiling follow-up for `H2`.
3. Admit at most one additional revised-selector batch for `H4`, and only after a concrete opportunity entry is documented.
4. Reproduce or archive important scratch-resident artifacts before promoting them into final paper figures.
