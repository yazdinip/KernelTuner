# KernelTuner

`KernelTuner` is a research prototype for bottleneck-aware configuration selection for Triton GPU kernels.

The core question is narrow but substantial: can cheap compile-time signals plus limited profiling guide Triton configuration search better than default settings or equally budgeted naive tuning?

## Project Status

The repository is no longer docs-only. It contains a working v1 experimentation stack with:

- typed configs and schema-validated artifacts
- Triton kernel execution for GEMM and LayerNorm
- deterministic candidate generation
- correctness-checked benchmarking on GPU
- compile-signal collection
- selective Nsight Compute profiling
- matched-budget selector and baseline strategies
- run-level summaries and study-level cross-run comparison
- a research documentation layer under `docs/research/` for paper-facing planning and evidence tracking

Current emphasis has shifted from foundational implementation to research validation:

- stabilizing repeated reportable runs on the homogeneous `RTX A6000` pool (`gpunode2`, `gpunode3`)
- comparing runs across workload classes and kernel families
- expanding the code-backed tuning surface where evidence justifies it
- using evidence to justify any selector revision

## Research Posture

- This is a research system, not a production autotuning framework.
- GEMM is the primary case study.
- LayerNorm is the validation contrast kernel for memory-centric behavior.
- Negative results are valid if the measurement protocol and interpretation are rigorous.
- The objective is a defensible empirical story, not uncontrolled feature growth.

## Implemented Repository Structure

```text
src/kernel_tuner/
  analysis/
  baselines/
  benchmark/
  cli/
  common/
  config_space/
  experiments/
  kernels/
  profiling/
  selector/
  signals/
  storage/
configs/
  counters/
  experiments/
  kernels/
  studies/
artifacts/
docs/
  research/
scripts/
```

## Read This First

1. [Documentation Index](docs/00_index.md)
2. [Project Charter](docs/01_project_charter.md)
3. [System Overview](docs/02_system_overview.md)
4. [Experiment Protocol](docs/04_experiment_protocol.md)
5. [Data Model and Artifacts](docs/05_data_model_and_artifacts.md)
6. [Research Package Index](docs/research/00_index.md)

## Documentation Map

- Proposal: [visual_computing_revised_proposal.md](visual_computing_revised_proposal.md)
- Documentation index: [docs/00_index.md](docs/00_index.md)
- GPU job guide: [docs/gpu_job_guide.md](docs/gpu_job_guide.md)
- Research backbone: [docs/research/00_index.md](docs/research/00_index.md)
- Architecture decisions: [docs/adr/](docs/adr/)
- Module specifications: [docs/specs/](docs/specs/)

## Quickstart

On the current homogeneous `RTX A6000` pool:

```bash
export KTUNE_SCRATCH=/scratch/scratch-space/expires-xxxx/$USER/kerneltuner
scripts/bootstrap_env.sh "$KTUNE_SCRATCH/venv-py312"
source "$KTUNE_SCRATCH/venv-py312/bin/activate"

ktune validate-kernel --kernel configs/kernels/gemm.yaml
ktune run-experiment --experiment configs/experiments/gemm_smoke.yaml
ktune summarize --run artifacts/gemm_smoke/<run_id>/
ktune compare-runs --spec configs/studies/validation_phase.yaml
```

Useful starting configs:

- `configs/kernels/gemm.yaml`
- `configs/kernels/layernorm.yaml`
- `configs/kernels/gemm_v2.yaml`
- `configs/kernels/layernorm_v2.yaml`
- `configs/experiments/gemm_smoke.yaml`
- `configs/experiments/gemm_reportable.yaml`
- `configs/experiments/layernorm_reportable.yaml`
- `configs/experiments/gemm_v2_reportable.yaml`
- `configs/experiments/layernorm_v2_small_reportable.yaml`
- `configs/experiments/layernorm_v2_large_reportable.yaml`
- `configs/studies/validation_phase.yaml`
- `configs/studies/gemm_v2_baseline_mapping.yaml`

If you do not want to choose a scratch path manually, see the more explicit environment setup flow in [docs/gpu_job_guide.md](docs/gpu_job_guide.md).

## Slurm Submission Helpers

For cluster execution, the repo includes reusable Slurm scripts:

- `scripts/slurm/run_kerneltuner_array.sbatch`
- `scripts/slurm/submit_kerneltuner.sh`

The submit wrapper now supports explicit node pinning for reportable runs through `--nodelist`.
For Phase 2 work, `gpunode2` and `gpunode3` are treated as one qualified `RTX A6000`
pool, so reportable submissions may pin either host or otherwise restrict scheduling to
that homogeneous class.

Example:

```bash
scripts/slurm/submit_kerneltuner.sh \
  --list configs/experiments/slurm_experiment_list.example.txt \
  --partition gpunodes \
  --nodelist <gpunode2-or-gpunode3> \
  --gpu-type rtx_a6000 \
  --gpus 1 \
  --time 0-04:00 \
  --cpus 8 \
  --mem 24GB
```

## Slurm Submission Helpers

For cluster execution, the repo includes reusable Slurm scripts:

- `scripts/slurm/run_kerneltuner_array.sbatch`: array worker that maps one array task to one experiment YAML.
- `scripts/slurm/submit_kerneltuner.sh`: submit wrapper that computes array size from a list file.

Example list file:

- `configs/experiments/slurm_experiment_list.example.txt`

Basic usage:

```bash
chmod +x scripts/slurm/submit_kerneltuner.sh
cp configs/experiments/slurm_experiment_list.example.txt configs/experiments/slurm_experiment_list.txt
scripts/slurm/submit_kerneltuner.sh \
  --list configs/experiments/slurm_experiment_list.txt \
  --partition gpunodes \
  --gpu-type rtx_a2000 \
  --gpus 1 \
  --time 0-04:00 \
  --cpus 4 \
  --mem 24GB \
  --log-dir /scratch/scratch-space/expires-xxxx/$USER/kerneltuner_logs \
  --scratch-root /scratch/scratch-space/expires-xxxx/$USER/kerneltuner \
  --artifact-root /scratch/scratch-space/expires-xxxx/$USER/kerneltuner_artifacts \
  --mail-user you@example.com \
  --mail-type BEGIN,END,FAIL \
  --alert-email you@example.com \
  --alert-on-start
```

Useful environment overrides:

- `RUN_COMMAND_TEMPLATE` (default: `ktune run-experiment --experiment "{experiment}"`)
- `INSTALL_PACKAGES` (`0` to skip pip install in jobs)
- `EXTRA_PIP_PACKAGES` (space-separated extra pip packages)
- `SKIP_IF_ARTIFACTS_EXIST` (`0` to force reruns)
- `DRY_RUN=1` (worker-level dry run)
- `ALERT_EMAIL`, `ALERT_ON_START`, `ALERT_ON_END`, `ALERT_ON_FAIL` for worker-level alerts

Notes:

- `--artifact-root` overrides `artifact_root` in experiment YAML at submission time.
- If no scratch path exists on the node, jobs fall back to `<workspace>/.scratch/$USER`.
- Slurm native email (`--mail-user/--mail-type`) and worker-level alerts can be used together.

## What This Repo Is Not

- It is not a Triton compiler redesign effort.
- It is not a vendor-library replacement project.
- It is not a general-purpose multi-GPU autotuning platform.
- It is not a claim of universal tuning wins across kernels or hardware.
