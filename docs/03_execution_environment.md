# Execution Environment

## Purpose

This document defines the supported runtime and tooling assumptions for `KernelTuner` v1.

## Supported Environment

| Area | v1 Assumption |
| --- | --- |
| Host OS | Linux x86_64 |
| Recommended distro | Ubuntu 24.04 LTS or a comparable recent Linux distribution |
| Python | Python 3.12.3 via system `python3` on the benchmark node |
| GPU | One NVIDIA RTX A6000 48 GB on `gpunode2` |
| CUDA | CUDA 12.9 via `/usr/local/cuda-12.9` |
| Triton runtime | `triton==3.6.0` for the initial implementation milestone |
| Tensor runtime | `torch==2.10.0` for the initial implementation milestone |
| Profiler | Nsight Compute CLI (`ncu`) 2025.2.1 via `/usr/local/cuda/bin/ncu` |
| Optional diagnostic profiler | Nsight Systems (`nsys`) for development diagnostics only, not as a primary matched-budget signal source |
| Artifact formats | YAML, JSON, CSV, PNG, Parquet |

## Pinned Milestone 0 Baseline

The initial implementation milestone is pinned to one concrete execution baseline so implementation does not start against moving environment targets.

Selected authoritative benchmark target:

- Slurm partition: `gpunodes`
- Authoritative node: `gpunode2`
- GPU model: `NVIDIA RTX A6000` with `49140 MiB`
- Node OS: Ubuntu 24.04 LTS class image
- Python: `3.12.3`
- CUDA toolkit: `12.9` at `/usr/local/cuda-12.9`
- Nsight Compute CLI: `2025.2.1`
- GCC: `13.3.0`

Pinned Python package set for initial implementation:

- `torch==2.10.0`
- `triton==3.6.0`
- `PyYAML==6.0.3`
- `pandas==3.0.1`
- `pyarrow==23.0.1`
- `pytest==8.4.2`
- `pydantic==2.12.5`
- `typer==0.24.1`
- `matplotlib==3.10.8`

Operational policy for this baseline:

- Reportable runs are pinned to `gpunode2`.
- `gpunode3` may be used only for development or for explicit requalification when `gpunode2` is unavailable.
- A single comparative study must not mix `gpunode2` and `gpunode3`.
- Clock control is not assumed for the initial milestone; the implementation should record observed clock behavior and persistence state rather than require clock locking.

## Operating Model

- Development may happen from any machine.
- Benchmarking and profiling are supported only on the designated Linux CUDA host in v1.
- For the initial implementation milestone, the designated host is `gpunode2`.
- Native Windows is not a supported execution environment for v1 experiments.
- Windows plus WSL is acceptable for editing and light validation, but authoritative measurements must be run on the Linux host.
- If Slurm is used, one authoritative host or one explicitly homogeneous node class must be designated for reportable runs.
- Reportable comparisons must not mix GPU models, MIG partitions, or materially different host classes within the same study.

## Required Tooling

The target machine must provide:

- Python 3.12 with virtual environment support
- NVIDIA driver compatible with CUDA 12.x
- CUDA runtime and device visibility
- PyTorch and Triton installed in the same environment
- `ncu` available on `PATH` for profiling runs, either directly or via an explicit CUDA `bin/` export
- Parquet support through a Python library such as `pyarrow`

If cluster execution is used, the environment should also provide:

- Slurm submission capability for the chosen partition
- stable access to scratch storage for caches, virtualenvs, and temporary profiler output
- node-level visibility into job metadata such as job ID, node name, partition, and allocated GPU

## Benchmark Host Qualification

Before treating a host as authoritative for reportable measurements, verify:

- `nvidia-smi` reports the expected GPU model and no unexpected competing workloads
- `python --version`, `torch.__version__`, and `triton.__version__` match the intended study environment
- `ncu --version` is recorded and functional
- one Triton compile-and-run smoke succeeds on the target GPU
- clock control, persistence mode, or other performance-affecting settings are either fixed or explicitly recorded as unavailable

When fixed clocks or similar controls are not possible on the cluster, the run manifest must still record the observed environment and any known limitations.

For the initial implementation milestone, the expected qualification values are:

- node: `gpunode2`
- GPU: `NVIDIA RTX A6000`
- Python: `3.12.3`
- CUDA toolkit root: `/usr/local/cuda-12.9`
- Nsight Compute: `2025.2.1`
- package pins: the versions listed in the pinned baseline above

## Slurm and Cluster Policy

- Slurm is an execution convenience, not a relaxation of the single-host, single-GPU study contract.
- Reportable runs should prefer one designated node when feasible.
- For the initial implementation milestone, reportable runs should pin `--nodelist=gpunode2`.
- If a single node cannot be guaranteed, runs may use a homogeneous node class only if GPU model, driver, CUDA stack, and partition remain identical across comparisons.
- Slurm metadata must be recorded per run, including job ID, task ID, partition, node name, GRES allocation, CPU count, memory allocation, and `CUDA_VISIBLE_DEVICES` when available.
- Preemptible or time-limited queues may be used for development or smoke runs, but reportable runs must document any preemption risk and partial-run handling policy.

Current repo-specific policy:

- The existing Slurm helper scripts are acceptable for development, smoke, and reportable runs.
- Reportable helper-based submissions must still pin `--nodelist=gpunode2` explicitly and preserve full environment provenance.

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
- git branch and whether the working tree was dirty
- `ncu` version when profiling is enabled
- Slurm metadata when scheduled through Slurm
- cache locations that could affect compilation or benchmark behavior when they are explicitly configured

Recommended additional provenance:

- `pip freeze` or an equivalent locked environment export
- a reference to a saved working-tree diff if the run used uncommitted changes
- Triton cache root and any benchmark scratch directories
- clock-control or persistence-mode settings if known
- `CUDA_HOME` and any explicit `PATH` or `LD_LIBRARY_PATH` additions used to expose CUDA or profiler tools

Additional expectations:

- Use the same host and GPU for all comparisons within a study.
- Use a fixed random seed where random sampling or ordering is involved.
- Keep benchmark configuration constant across strategies.
- Prefer isolated benchmark windows rather than interleaving unrelated GPU activity.
- Keep the working tree clean for reportable runs or archive the diff alongside the artifacts.
- Prefer separate scratch-local caches for Triton compilation and profiling intermediates to avoid quota and cross-run interference.

## Unsupported or Deferred Environments

- Native Windows execution for authoritative measurements
- Multi-GPU experiments
- Cross-vendor GPU support
- MacOS execution
- Cloud-hosted benchmark environments where hardware state cannot be controlled or recorded reliably

Cluster scheduling itself is allowed, but heterogeneous or weakly controlled cluster execution is unsupported for reportable measurements.

## Environment Setup Policy

The repo now provides `scripts/bootstrap_env.sh` as the preferred bootstrap path for the pinned environment. Reportable runs should use that script or a documented equivalent, record exact package versions in experiment manifests, and preserve an environment export such as `pip freeze`.

For the current cluster image, assume:

- system Python is `python3`, not `python3.11`
- CUDA and Nsight tools may require exporting `/usr/local/cuda-12.9/bin` or `/usr/local/cuda/bin`
- scratch-backed virtual environments and caches should be preferred over home-directory installs

## Stable Contracts

- Linux x86_64 plus one NVIDIA GPU is the only supported benchmark environment in v1.
- Python 3.12.3 on `gpunode2` is the baseline language runtime for the initial implementation milestone.
- Profiling is defined in terms of Nsight Compute CLI.
- Environment metadata is part of the required run manifest.
- Slurm use must still satisfy the single-host or homogeneous-node-class comparability requirement.
- Dirty working trees must be recorded explicitly if they are used for development measurements.

## Exploratory Areas

- Package revisions after the initial implementation baseline is working
- Whether the project later broadens from one pinned node to a homogeneous node class
- Optional use of containers once implementation begins
