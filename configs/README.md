# Configs

This directory stores human-authored configuration files for `KernelTuner`.

## Layout

- `kernels/`: kernel specifications
- `experiments/`: experiment specifications
- `counters/`: named profiling counter sets

Example templates are included as `.example.yaml` files and should be copied or adapted into real configs during implementation.

## Historical v1 configs

- `kernels/gemm.yaml`: pinned Triton GEMM kernel space for the v1 baseline
- `counters/default_calibration.yaml`: pinned Nsight Compute counter set for calibration profiling
- `experiments/gemm_smoke.yaml`: single-shape smoke run for wiring validation
- `experiments/gemm_development.yaml`: faster end-to-end development study with profiling enabled
- `experiments/gemm_reportable.yaml`: pinned reportable baseline on `gpunode2` / `NVIDIA RTX A6000`

## Current Phase 2 configs

- `kernels/gemm_v2.yaml`: expanded GEMM search space with `group_size_m`
- `kernels/layernorm_v2.yaml`: regime-aware LayerNorm v2 space with `rows_per_program`
- `counters/memory_activity_lite.yaml`: LayerNorm profiling set extended with activity/occupancy context
- `experiments/gemm_v2_reportable.yaml`: primary representative GEMM Phase 2 study on the qualified `RTX A6000` pool
- `experiments/layernorm_v2_small_reportable.yaml`: Phase 2 small-batch LayerNorm regime study
- `experiments/layernorm_v2_large_reportable.yaml`: Phase 2 large-batch LayerNorm regime study
- `studies/gemm_v2_baseline_mapping.yaml`: representative GEMM v2 baseline mapping study
- `studies/gemm_v2_selector_ablation.yaml`: frontier-only vs profile-aware GEMM selector ablation
- `campaigns/gemm_v2_baseline_mapping.yaml`: repeatability and robustness entrypoint for representative GEMM v2
