# 2026-04-03 R7 Paper Hardening And Execution Block

Purpose: record the `R7` paper-hardening implementation pass, the refreshed final paper bundle, and the operational reason the bounded `R7` GPU package was not launched today.

## Scope

This pass implemented the non-execution half of `R7 Paper Hardening and Evidence Generalization`:

- added final-mainline budget-sweep configs:
  - `configs/experiments/gemm_final_budget_sweep_b6p2.yaml`
  - `configs/experiments/gemm_final_budget_sweep_b9p3.yaml`
  - `configs/experiments/gemm_final_budget_sweep_b12p4.yaml`
  - `configs/experiments/gemm_final_budget_sweep_b18p6.yaml`
  - `configs/studies/gemm_final_budget_sweep.yaml`
  - `configs/campaigns/gemm_final_budget_sweep.yaml`
- added final-mainline stability-extension configs:
  - `configs/experiments/gemm_final_stability_reportable.yaml`
  - `configs/studies/gemm_final_stability_extension.yaml`
  - `configs/campaigns/gemm_final_stability_extension.yaml`
- added execution helper:
  - `scripts/run_r7_paper_hardening_cycle.sh`
- replaced the final bundle builder with a refreshed version that emits:
  - strategy-by-budget summaries
  - uncertainty / stability summaries
  - workload-class regret summaries
  - plot-ready CSVs for all promoted main-text figures
- added paper-figure generation:
  - `scripts/build_paper_figures.py`

## Local Validation

Local validation succeeded in a freshly bootstrapped project virtualenv:

- `ktune validate-study --spec configs/studies/gemm_final_budget_sweep.yaml`
- `ktune validate-study --spec configs/studies/gemm_final_stability_extension.yaml`
- `python scripts/build_final_paper_bundle.py --output-tag final_paper_20260403`
- `python scripts/build_paper_figures.py --bundle-dir artifacts/analysis/final_paper_20260403`

Generated outputs now include:

- final bundle:
  - `artifacts/analysis/final_paper_20260403/`
- generated figure PDFs:
  - `paper/figures/generated/figure1_pipeline.pdf`
  - `paper/figures/generated/figure2_budget_curve.pdf`
  - `paper/figures/generated/figure3_aligned_context.pdf`
  - `paper/figures/generated/figure4_layernorm_regimes.pdf`
  - `paper/figures/generated/figure5_transfer_mainline.pdf`

## Paper-Hardening Outcome

The manuscript and paper metadata were updated to reflect the hardened evidence package:

- the paper now uses generated vector figures instead of boxed numeric placeholders
- the main text is more explicitly framed around general matched-budget lessons rather than repo chronology
- the appendix and paper manifests now point to `artifacts/analysis/final_paper_20260403/`
- the final claim inventory remains unchanged in substance:
  - bounded final mainline improvement on representative GEMM
  - strong `H1`
  - bounded mixed `H2`
  - contextual `H3`
  - mixed transfer-limited `H4`
  - unsupported `H5`

## Why No New GPU Evidence Was Added

The bounded `R7` GPU package was prepared but not launched on April 3, 2026 because the qualified A6000 pool was unavailable:

- `gpunode2`: `DRAIN`
- `gpunode3`: `DRAIN`
- Slurm reason on both nodes: `moving to DCA`

This is an operational block, not a scientific stop rule.

No new `R7` campaign or study artifacts are promoted from this pass.

## Current State

- the canonical final paper bundle is now `artifacts/analysis/final_paper_20260403/`
- the prepared `R7` budget-sweep and stability package is ready to run once the qualified A6000 pool returns
- until then, the paper should keep the current headline wording:
  - bounded representative-GEMM improvement on the final non-`split_k` mainline
  - not yet upgraded to a stronger stability-backed claim
