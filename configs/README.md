# Configs

This directory stores human-authored configuration files for `KernelTuner`.

## Layout

- `kernels/`: kernel specifications
- `experiments/`: experiment specifications
- `counters/`: named profiling counter sets

Example templates are included as `.example.yaml` files and should be copied or adapted into real configs during implementation.

## Pinned v1 configs

- `kernels/gemm.yaml`: pinned Triton GEMM kernel space for the v1 baseline
- `counters/default_calibration.yaml`: pinned Nsight Compute counter set for calibration profiling
- `experiments/gemm_smoke.yaml`: single-shape smoke run for wiring validation
- `experiments/gemm_development.yaml`: faster end-to-end development study with profiling enabled
- `experiments/gemm_reportable.yaml`: pinned reportable baseline on `gpunode2` / `NVIDIA RTX A6000`
