import subprocess
from pathlib import Path


def test_submit_script_dry_run_supports_nodelist():
    result = subprocess.run(
        [
            "bash",
            "scripts/slurm/submit_kerneltuner.sh",
            "--list",
            "configs/experiments/slurm_experiment_list.example.txt",
            "--partition",
            "gpunodes",
            "--nodelist",
            "gpunode2",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--nodelist=gpunode2" in result.stdout


def test_worker_script_sources_bootstrap_env_so_cuda_paths_persist():
    script = Path("scripts/slurm/run_kerneltuner_array.sbatch").read_text()
    assert 'source "$WORKSPACE_ROOT/scripts/bootstrap_env.sh" "$VENV_PATH"' in script
