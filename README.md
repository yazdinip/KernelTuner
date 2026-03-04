# KernelTuner

`KernelTuner` is a research prototype for bottleneck-aware configuration selection for Triton GPU kernels.

The project asks a narrow but substantial question: can lightweight resource signals and limited profiling feedback guide Triton kernel configuration search better than default settings or naive tuning under comparable budgets?

## Project Status

The repository is currently documentation-first. The proposal and the v1 documentation package define the system architecture, experiment protocol, artifact schemas, and module boundaries that implementation will follow.

Implementation has not started yet. The current goal of the repo is to remove design ambiguity before code is written.

## Core Question

Can a bottleneck-aware configuration selector use resource signals and limited profiling data to guide Triton kernel configuration search better than default settings or equally budgeted naive tuning?

## Research Posture

- This is a research prototype, not a production autotuning framework.
- A negative empirical result is still a valid project outcome if the system and evaluation are sound.
- GEMM is the required primary kernel family for v1.
- Additional kernels are optional validation targets once the core pipeline is stable.

## Planned v1 Repository Structure

```text
src/kernel_tuner/
  kernels/
  config_space/
  benchmark/
  signals/
  profiling/
  selector/
  baselines/
  experiments/
  storage/
  analysis/
  cli/
  common/
configs/
  kernels/
  experiments/
  counters/
artifacts/
docs/
```

## Read This First

1. [Documentation Index](docs/00_index.md)
2. [Project Charter](docs/01_project_charter.md)
3. [System Overview](docs/02_system_overview.md)
4. [Experiment Protocol](docs/04_experiment_protocol.md)
5. [Data Model and Artifacts](docs/05_data_model_and_artifacts.md)

## Documentation Map

- Proposal: [visual_computing_revised_proposal.md](visual_computing_revised_proposal.md)
- Documentation index: [docs/00_index.md](docs/00_index.md)
- Architecture decisions: [docs/adr/](docs/adr/)
- Module specifications: [docs/specs/](docs/specs/)

## Quickstart Intent

The initial workflow is document-driven:

1. Read the charter and system overview.
2. Use the protocol and data model docs to align on experiment behavior.
3. Implement modules against the specs in `docs/specs/`.
4. Keep deviations explicit through ADRs rather than ad hoc code changes.

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
- It is not a general-purpose multi-GPU autotuning platform in v1.
