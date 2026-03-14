# GPU Job Guide (KernelTuner / Slurm)

## Purpose

This guide is for running `KernelTuner` work on a Linux CUDA host managed by Slurm.

Important current-state note:

- `main` is still documentation-first.
- The runnable experiment pipeline is not implemented yet.
- The repo now includes Slurm helper scripts and example YAMLs.
- The documented `ktune` CLI is still planned, not available on the current branch.

Use this guide to prepare the GPU environment correctly, work from the example configs, and avoid mixing this repo up with commands from unrelated projects.

## Supported benchmark environment

Per [03_execution_environment.md](03_execution_environment.md), authoritative runs for v1 are:

- Linux `x86_64`
- Python `3.12.3` via system `python3`
- one `NVIDIA RTX A6000` on `gpunode2`
- CUDA `12.9` via `/usr/local/cuda-12.9`
- `torch==2.10.0` and `triton==3.6.0` in the same virtualenv
- Nsight Compute CLI (`ncu`) `2025.2.1` via `/usr/local/cuda/bin/ncu`

For reportable runs, stay on one designated host or one explicitly homogeneous Slurm node class.

Native Windows is not a supported benchmark platform for this repo.

## Pinned Milestone 0 baseline

The initial implementation milestone is pinned to one concrete cluster target so implementation starts from a known-good environment contract instead of placeholders.

- Authoritative node: `gpunode2`
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

Current host-image note:

- `ncu` and `nvcc` are installed on the GPU nodes, but not exported on `PATH` by default.
- `python3.11` is not present on the current node image.
- The login host is for submission and editing; authoritative benchmarking happens only inside a Slurm allocation on the GPU node.

## Repo status on `main`

What exists now:

- architecture and experiment docs under `docs/`
- example configs under `configs/`
- package skeleton under `src/kernel_tuner/`
- Slurm helper scripts under `scripts/slurm/`

What does not exist yet on `main`:

- implemented Triton kernels
- implemented benchmark/selector/profiling pipeline
- a `ktune` console entrypoint

That means GPU-node work right now is mainly:

1. setting up the Linux environment,
2. validating tool availability,
3. preparing experiment YAMLs,
4. using dry-run or custom-command Slurm flows until the pipeline lands.

## Useful files to start from

- `configs/kernels/gemm.example.yaml`
- `configs/experiments/gemm_smoke.example.yaml`
- `configs/experiments/slurm_experiment_list.example.txt`
- `configs/counters/default_calibration.example.yaml`
- `scripts/slurm/submit_kerneltuner.sh`
- `scripts/slurm/run_kerneltuner_array.sbatch`
- [00_index.md](00_index.md)
- [04_experiment_protocol.md](04_experiment_protocol.md)
- [05_data_model_and_artifacts.md](05_data_model_and_artifacts.md)

The primary v1 kernel family is GEMM.

## Connect to the GPU host

Use your own SSH alias or direct host command. Example:

```bash
ssh <your-gpu-host-alias>
```

If your cluster exposes GPU nodes through Slurm, check what is available before requesting one:

```bash
sinfo -p gpunodes -N -o "%15N %5t %10m %10G %8c %16e"
```

Adjust partition and GPU type names to match your cluster.

## Start an interactive GPU shell

`KernelTuner` v1 assumes one GPU per run, so request the pinned authoritative node directly for reportable work:

```bash
srun --partition=gpunodes \
     --nodelist=gpunode2 \
     --gres=gpu:rtx_a6000:1 \
     --cpus-per-task=8 \
     --mem=24G \
     --time=02:00:00 \
     --pty bash -l
```

Inside the session, verify the machine is suitable:

```bash
nvidia-smi
python3 --version
export CUDA_HOME=/usr/local/cuda-12.9
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
ncu --version
```

If you want a persistent shell, start `tmux` after entering the allocated GPU shell:

```bash
tmux new -s kerneltuner_gpu
```

## Create a clean environment on scratch storage

Keep the virtualenv and pip cache off your home quota when possible:

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

export KTUNE_SCRATCH_BASE="$(ls -d /scratch/scratch-space/expires-* 2>/dev/null | sort | tail -n 1)"
if [[ -n "$KTUNE_SCRATCH_BASE" ]]; then
  export KTUNE_SCRATCH="$KTUNE_SCRATCH_BASE/$USER/kerneltuner"
else
  export KTUNE_SCRATCH="/tmp/$USER/kerneltuner"
fi
export PIP_CACHE_DIR=$KTUNE_SCRATCH/pip-cache
mkdir -p "$KTUNE_SCRATCH"

python3 -m venv "$KTUNE_SCRATCH/venv-py312"
source "$KTUNE_SCRATCH/venv-py312/bin/activate"

python -m pip install --upgrade pip setuptools wheel
pip install -e . \
  "torch==2.10.0" \
  "triton==3.6.0" \
  "PyYAML==6.0.3" \
  "pandas==3.0.1" \
  "pyarrow==23.0.1" \
  "pytest==8.4.2"
```

These pins are the selected initial implementation baseline. Change them only if a later compatibility issue forces a documented update.

Record the environment immediately after install:

```bash
python - <<'PY'
import platform
import torch
import triton
import yaml
import pandas
import pyarrow
print("python", platform.python_version())
print("torch", torch.__version__)
print("triton", triton.__version__)
print("pyyaml", yaml.__version__)
print("pandas", pandas.__version__)
print("pyarrow", pyarrow.__version__)
PY

pip freeze > "$KTUNE_SCRATCH/pip-freeze.txt"
```

## Prepare local experiment configs

The repo already provides example configs. Copy them to real filenames before editing:

```bash
cp configs/kernels/gemm.example.yaml configs/kernels/gemm.yaml
cp configs/experiments/gemm_smoke.example.yaml configs/experiments/gemm_smoke.yaml
cp configs/counters/default_calibration.example.yaml configs/counters/default_calibration.yaml
cp configs/experiments/slurm_experiment_list.example.txt configs/experiments/slurm_experiment_list.txt
```

These files define:

- the kernel spec,
- the experiment spec,
- the named Nsight Compute counter set,
- the list of experiments for Slurm array submission.

`gemm_smoke.example.yaml` is a smoke-only config for wiring and tool validation. It is not a reportable study config.

## Planned workflow once implementation lands

The documented command surface is:

```bash
ktune validate-kernel --kernel configs/kernels/gemm.yaml
ktune generate-configs --experiment configs/experiments/gemm_smoke.yaml
ktune benchmark --experiment configs/experiments/gemm_smoke.yaml
ktune collect-signals --experiment configs/experiments/gemm_smoke.yaml
ktune profile --experiment configs/experiments/gemm_smoke.yaml
ktune select --experiment configs/experiments/gemm_smoke.yaml
ktune run-experiment --experiment configs/experiments/gemm_smoke.yaml
ktune summarize --run artifacts/<experiment_id>/<run_id>/
```

Do not expect those commands to work on the current `main` branch yet. They come from the v1 CLI spec, not from implemented code.

## Slurm helper workflow on current `main`

The repo now ships two helper scripts:

- `scripts/slurm/submit_kerneltuner.sh`
- `scripts/slurm/run_kerneltuner_array.sbatch`

These are useful now for:

- reserving GPU time,
- validating the environment,
- setting up a repeatable job wrapper,
- preparing for future `ktune run-experiment` runs.

For reportable runs, make sure the submission path also captures node name, Slurm job metadata, and an environment export such as `pip freeze`.

Important limitation for the current branch:

- The helper scripts do not yet expose a `--nodelist` option.
- That means they are currently suitable for smoke or development runs, not for final reportable runs that must stay pinned to `gpunode2`.
- Before using the helper path for reportable runs, add explicit node pinning to the submission path or use a manually pinned Slurm command.

Basic dry-run submission example:

```bash
chmod +x scripts/slurm/submit_kerneltuner.sh
cp configs/experiments/slurm_experiment_list.example.txt configs/experiments/slurm_experiment_list.txt

scripts/slurm/submit_kerneltuner.sh \
  --list configs/experiments/slurm_experiment_list.txt \
  --partition gpunodes \
  --gpu-type rtx_a6000 \
  --gpus 1 \
  --time 0-02:00 \
  --cpus 4 \
  --mem 24GB \
  --dry-run
```

If you want the worker to run something other than the future `ktune` command, override the command template:

```bash
export RUN_COMMAND_TEMPLATE='python -m pip list'
scripts/slurm/submit_kerneltuner.sh \
  --list configs/experiments/slurm_experiment_list.txt \
  --partition gpunodes \
  --gpus 1 \
  --time 0-00:30 \
  --cpus 2 \
  --mem 8GB
```

Available submission options include:

- `--workspace`
- `--log-dir`
- `--scratch-root`
- `--artifact-root`
- `--gpu-type`
- `--mail-user`
- `--mail-type`
- `--alert-email`

Useful worker-level environment overrides include:

- `RUN_COMMAND_TEMPLATE`
- `INSTALL_PACKAGES=0`
- `EXTRA_PIP_PACKAGES`
- `SKIP_IF_ARTIFACTS_EXIST=0`
- `DRY_RUN=1`

For development runs on the current helper path, prefer:

```bash
export EXTRA_PIP_PACKAGES='torch==2.10.0 triton==3.6.0 pytest==8.4.2'
```

## Expected artifact layout

When experiment execution is implemented, each run is supposed to write:

```text
artifacts/<experiment_id>/<run_id>/
  manifest.json
  experiment_spec.yaml
  candidates.parquet
  compile_signals.parquet
  runtime_measurements.parquet
  profile_measurements.parquet
  selection_decisions.parquet
  summary.json
  logs/
```

This layout is fixed by [05_data_model_and_artifacts.md](05_data_model_and_artifacts.md).
