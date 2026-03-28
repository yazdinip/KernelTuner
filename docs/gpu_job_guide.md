# GPU Job Guide (KernelTuner / Slurm)

## Purpose

This guide covers how to run `KernelTuner` on the Linux CUDA cluster environment used for authoritative experiments.

It focuses on the pinned v1 baseline and on the repo's actual current state, not the earlier docs-only setup.

## Current Repo State

The runnable experiment pipeline exists now. The repo currently provides:

- the `ktune` CLI
- Triton GEMM and LayerNorm kernels
- benchmark, signal, profiling, selection, and reporting paths
- study-level comparison through `ktune compare-runs`
- Slurm helper scripts for array submission and pinned reportable runs

The main practical distinction is no longer "implemented vs not implemented." It is:

- smoke and development runs for iteration,
- reportable runs on the qualified homogeneous `RTX A6000` pool,
- study comparisons built from completed reportable runs.

## Supported Benchmark Environment

Per [03_execution_environment.md](03_execution_environment.md), authoritative runs for the
current phase are:

- Linux `x86_64`
- Python `3.12.3` via system `python3`
- one `NVIDIA RTX A6000` on `gpunode2` or `gpunode3`
- CUDA `12.9` via `/usr/local/cuda-12.9`
- `torch==2.10.0` and `triton==3.6.0` in the same virtualenv
- Nsight Compute CLI (`ncu`) `2025.2.1`

For reportable runs, stay on one designated host or one explicitly homogeneous node class.
In the current project phase, that means the qualified `RTX A6000` pool made up of
`gpunode2` and `gpunode3`.

## Pinned Baseline

- Qualified nodes: `gpunode2`, `gpunode3`
- Partition: `gpunodes`
- GPU type: `rtx_a6000`
- GPU name: `NVIDIA RTX A6000`
- Python executable: `python3`
- CUDA root: `/usr/local/cuda-12.9`
- Nsight Compute binary: `/usr/local/cuda/bin/ncu`
- Nsight Systems binary: `/usr/local/cuda/bin/nsys`

Pinned package set:

- `torch==2.10.0`
- `triton==3.6.0`
- `PyYAML==6.0.3`
- `pandas==3.0.1`
- `pyarrow==23.0.1`
- `pytest==8.4.2`
- `pydantic==2.12.5`
- `typer==0.24.1`
- `matplotlib==3.10.8`

Current host-image note:

- `ncu` and `nvcc` are installed on the GPU nodes, but are not always exported on `PATH` by default.
- the login host is for submission and editing; authoritative benchmarking happens only inside a Slurm allocation on the GPU node.

## Useful Files

Kernel and experiment configs:

- `configs/kernels/gemm.yaml`
- `configs/kernels/layernorm.yaml`
- `configs/experiments/gemm_smoke.yaml`
- `configs/experiments/gemm_reportable.yaml`
- `configs/experiments/layernorm_reportable.yaml`
- `configs/experiments/gemm_v2_reportable.yaml`
- `configs/experiments/layernorm_v2_small_reportable.yaml`
- `configs/experiments/layernorm_v2_large_reportable.yaml`
- `configs/studies/validation_phase.yaml`

Counter sets:

- `configs/counters/default_calibration.yaml`
- `configs/counters/compute_lite.yaml`
- `configs/counters/memory_lite.yaml`
- `configs/counters/shared_diag.yaml`

Operational scripts:

- `scripts/bootstrap_env.sh`
- `scripts/slurm/submit_kerneltuner.sh`
- `scripts/slurm/run_kerneltuner_array.sbatch`

## Connect to the Cluster

Use your own SSH alias or direct host command. Example:

```bash
ssh <your-gpu-host-alias>
```

To inspect available GPU nodes:

```bash
sinfo -p gpunodes -N -o "%15N %5t %10m %10G %8c %16e"
```

## Start an Interactive GPU Shell

For reportable work, request one node from the qualified pool directly:

```bash
srun --partition=gpunodes \
     --nodelist=<gpunode2-or-gpunode3> \
     --gres=gpu:rtx_a6000:1 \
     --cpus-per-task=8 \
     --mem=24G \
     --time=02:00:00 \
     --pty bash -l
```

Inside the session, verify the machine:

```bash
nvidia-smi
python3 --version
export CUDA_HOME=/usr/local/cuda-12.9
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
ncu --version
```

If you want a persistent shell, start `tmux` after entering the allocation:

```bash
tmux new -s kerneltuner_gpu
```

## Create the Environment

The repo now provides a bootstrap script for the pinned environment:

```bash
export KTUNE_SCRATCH_BASE="$(ls -d /scratch/scratch-space/expires-* 2>/dev/null | sort | tail -n 1)"
if [[ -n "$KTUNE_SCRATCH_BASE" ]]; then
  export KTUNE_SCRATCH="$KTUNE_SCRATCH_BASE/$USER/kerneltuner"
else
  export KTUNE_SCRATCH="/tmp/$USER/kerneltuner"
fi

source scripts/bootstrap_env.sh "$KTUNE_SCRATCH/venv-py312"
```

If you want to choose the virtualenv path explicitly:

```bash
source scripts/bootstrap_env.sh /scratch/scratch-space/expires-xxxx/$USER/kerneltuner/venv-py312
```

The bootstrap script:

- exports CUDA paths
- prefers scratch-backed caches
- creates a Python 3.12 virtualenv
- installs the repo with GPU and dev extras

Record the environment immediately after install:

```bash
python - <<'PY'
import platform
import torch
import triton
import yaml
import pandas
import pyarrow
import pydantic
import typer
print("python", platform.python_version())
print("torch", torch.__version__)
print("triton", triton.__version__)
print("pyyaml", yaml.__version__)
print("pandas", pandas.__version__)
print("pyarrow", pyarrow.__version__)
print("pydantic", pydantic.__version__)
print("typer", typer.__version__)
PY

pip freeze > "${KTUNE_SCRATCH:-/tmp/$USER/kerneltuner}/pip-freeze.txt"
```

## Run the CLI Directly

Basic validation and smoke workflow:

```bash
ktune validate-kernel --kernel configs/kernels/gemm.yaml
ktune validate-kernel --kernel configs/kernels/layernorm.yaml

ktune run-experiment --experiment configs/experiments/gemm_smoke.yaml
ktune run-experiment --experiment configs/experiments/gemm_reportable.yaml
ktune run-experiment --experiment configs/experiments/layernorm_reportable.yaml
```

Post-run analysis:

```bash
ktune summarize --run artifacts/gemm_reportable/<run_id>/
ktune compare-runs --spec configs/studies/validation_phase.yaml
```

Stage-by-stage commands are also available:

```bash
ktune generate-configs --experiment configs/experiments/gemm_reportable.yaml
ktune benchmark --experiment configs/experiments/gemm_reportable.yaml
ktune collect-signals --experiment configs/experiments/gemm_reportable.yaml
ktune profile --experiment configs/experiments/gemm_reportable.yaml
ktune select --experiment configs/experiments/gemm_reportable.yaml
```

## Slurm Helper Workflow

The repo ships two helper scripts:

- `scripts/slurm/submit_kerneltuner.sh`
- `scripts/slurm/run_kerneltuner_array.sbatch`

They are suitable for both development and reportable runs, provided reportable submissions
stay within the qualified `RTX A6000` pool and record the exact node in the manifest.

Basic pinned submission example:

```bash
chmod +x scripts/slurm/submit_kerneltuner.sh

scripts/slurm/submit_kerneltuner.sh \
  --list configs/experiments/slurm_experiment_list.example.txt \
  --partition gpunodes \
  --nodelist <gpunode2-or-gpunode3> \
  --gpu-type rtx_a6000 \
  --gpus 1 \
  --time 0-04:00 \
  --cpus 8 \
  --mem 24GB \
  --workspace "$(pwd)"
```

Useful environment overrides:

- `RUN_COMMAND_TEMPLATE`
- `INSTALL_PACKAGES=0`
- `EXTRA_PIP_PACKAGES`
- `SKIP_IF_ARTIFACTS_EXIST=0`
- `DRY_RUN=1`
- `ALERT_EMAIL`
- `ALERT_ON_START`
- `ALERT_ON_END`
- `ALERT_ON_FAIL`

Important operational notes:

- the worker script exports CUDA paths before running
- the worker script uses `scripts/bootstrap_env.sh` when `INSTALL_PACKAGES=1`
- `--artifact-root` overrides the experiment YAML artifact root at submit time
- if no scratch path exists on the node, jobs fall back to `<workspace>/.scratch/$USER`

## Reportable-Run Policy

For reportable runs:

- pin one node from the qualified `RTX A6000` pool
- keep one GPU per run
- do not mix non-`RTX A6000` GPU classes within one comparative study
- preserve `pip freeze` and environment provenance
- do not treat `shared_diag` as matched-budget reportable evidence unless the protocol explicitly marks it diagnostic-only

## Common Failure Checks

If something fails unexpectedly, check:

1. `CUDA_HOME`, `PATH`, and `LD_LIBRARY_PATH` are exported correctly.
2. `ncu --version` works inside the allocation.
3. the virtualenv is active and contains `torch` and `triton`.
4. you are on `gpunode2` or `gpunode3` for reportable A6000-pool work.
5. the experiment config points to the intended artifact root and counter set.

## What This Guide Is Not

- It is not a substitute for the scientific protocol in [04_experiment_protocol.md](04_experiment_protocol.md).
- It is not the artifact schema reference; use [05_data_model_and_artifacts.md](05_data_model_and_artifacts.md) for that.
- It is not the research plan; use [docs/research/00_index.md](research/00_index.md) for the paper-facing backbone.
