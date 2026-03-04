# Execution Environment

## Purpose

This document defines the supported runtime and tooling assumptions for `KernelTuner` v1.

## Supported Environment

| Area | v1 Assumption |
| --- | --- |
| Host OS | Linux x86_64 |
| Recommended distro | Ubuntu 22.04 LTS or a comparable recent Linux distribution |
| Python | Python 3.11 |
| GPU | One NVIDIA GPU on a local host |
| CUDA | CUDA 12.x compatible runtime and driver |
| Triton runtime | A Triton release compatible with the chosen Python, PyTorch, and CUDA stack |
| Tensor runtime | PyTorch release compatible with the chosen Triton stack |
| Profiler | Nsight Compute CLI (`ncu`) |
| Artifact formats | YAML, JSON, Parquet |

## Operating Model

- Development may happen from any machine.
- Benchmarking and profiling are supported only on the designated Linux CUDA host in v1.
- Native Windows is not a supported execution environment for v1 experiments.
- Windows plus WSL is acceptable for editing and light validation, but authoritative measurements must be run on the Linux host.

## Required Tooling

The target machine must provide:

- Python 3.11 with virtual environment support
- NVIDIA driver compatible with CUDA 12.x
- CUDA runtime and device visibility
- PyTorch and Triton installed in the same environment
- `ncu` available on `PATH` for profiling runs
- Parquet support through a Python library such as `pyarrow`

## Recommended Host Characteristics

- The machine should be dedicated or mostly idle during benchmark runs.
- Background GPU workloads should be disabled.
- CPU power-saving behavior should be minimized if it affects launch overhead consistency.
- GPU model, driver version, CUDA version, Triton version, and PyTorch version must be recorded per run.

## Reproducibility Expectations

Every experiment run must record:

- hostname
- OS name and version
- GPU model and device name
- NVIDIA driver version
- CUDA runtime version
- Triton version
- PyTorch version
- Python version
- git commit if available

Additional expectations:

- Use the same host and GPU for all comparisons within a study.
- Use a fixed random seed where random sampling or ordering is involved.
- Keep benchmark configuration constant across strategies.
- Prefer isolated benchmark windows rather than interleaving unrelated GPU activity.

## Unsupported or Deferred Environments

- Native Windows execution for authoritative measurements
- Multi-GPU experiments
- Distributed or cluster execution
- Cross-vendor GPU support
- MacOS execution
- Cloud-hosted benchmark environments where hardware state cannot be controlled or recorded reliably

## Environment Setup Policy

v1 assumes that implementation will later add explicit bootstrap files for environment creation. Until those files exist, the build team should use a single pinned Python environment on the Linux host and record the exact package versions in experiment manifests.

## Stable Contracts

- Linux x86_64 plus one NVIDIA GPU is the only supported benchmark environment in v1.
- Python 3.11 is the baseline language runtime.
- Profiling is defined in terms of Nsight Compute CLI.
- Environment metadata is part of the required run manifest.

## Exploratory Areas

- Exact package pins before bootstrap files are added
- Exact GPU architecture used for the primary study
- Optional use of containers once implementation begins
