"""Environment and source provenance capture."""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from shutil import which
from pathlib import Path

from kernel_tuner.common.schema import EnvironmentMetadata, InvocationMetadata, SlurmMetadata


def _run_command(args: list[str], cwd: str | Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def resolve_tool_path(name: str) -> str:
    cuda_home = os.environ.get("CUDA_HOME")
    if cuda_home:
        candidate = Path(cuda_home) / "bin" / name
        if candidate.exists():
            return str(candidate)
    resolved = which(name)
    return resolved or name


def _import_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return getattr(module, "__version__", None)


def _capture_nvidia() -> dict[str, str | None]:
    result = {
        "gpu_name": None,
        "gpu_uuid": None,
        "nvidia_driver_version": None,
        "cuda_runtime_version": None,
        "persistence_mode": None,
        "graphics_clock_mhz": None,
        "memory_clock_mhz": None,
        "power_limit_w": None,
    }
    query = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version,persistence_mode,clocks.gr,clocks.mem,power.limit",
            "--format=csv,noheader",
        ]
    )
    if query:
        parts = [item.strip() for item in query.split(",")]
        if len(parts) >= 7:
            (
                result["gpu_name"],
                result["gpu_uuid"],
                result["nvidia_driver_version"],
                result["persistence_mode"],
                result["graphics_clock_mhz"],
                result["memory_clock_mhz"],
                result["power_limit_w"],
            ) = parts[:7]
    header = _run_command(["nvidia-smi"])
    if header:
        match = re.search(r"CUDA Version:\s+([0-9.]+)", header)
        if match:
            result["cuda_runtime_version"] = match.group(1)
    return result


def _capture_git(repo_root: str | Path) -> dict[str, str | bool | None]:
    commit = _run_command(["git", "rev-parse", "HEAD"], cwd=repo_root)
    branch = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    status = _run_command(["git", "status", "--porcelain"], cwd=repo_root)
    return {
        "git_commit": commit,
        "git_branch": branch,
        "git_dirty": bool(status) if status is not None else None,
    }


def _capture_ncu_version() -> str | None:
    output = _run_command([resolve_tool_path("ncu"), "--version"])
    if output:
        line = output.splitlines()[-1].strip()
        return line
    return None


def _cache_roots() -> dict[str, str]:
    cache_roots: dict[str, str] = {}
    for env_name in ["TRITON_CACHE_DIR", "CUDA_CACHE_PATH", "XDG_CACHE_HOME"]:
        value = os.environ.get(env_name)
        if value:
            cache_roots[env_name] = value
    return cache_roots


def _tool_paths() -> dict[str, str]:
    tools = {}
    for name in ["python3", "ncu", "nsys", "nvcc"]:
        path = resolve_tool_path(name)
        if path != name:
            tools[name] = path
    return tools


def capture_environment_metadata(repo_root: str | Path) -> EnvironmentMetadata:
    gpu_info = _capture_nvidia()
    git_info = _capture_git(repo_root)
    os_name = platform.system()
    os_version = platform.platform()
    return EnvironmentMetadata(
        hostname=platform.node(),
        os_name=os_name,
        os_version=os_version,
        python_version=platform.python_version(),
        gpu_name=gpu_info["gpu_name"],
        gpu_uuid=gpu_info["gpu_uuid"],
        nvidia_driver_version=gpu_info["nvidia_driver_version"],
        cuda_runtime_version=gpu_info["cuda_runtime_version"],
        pytorch_version=_import_version("torch"),
        triton_version=_import_version("triton"),
        ncu_version=_capture_ncu_version(),
        cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
        git_commit=git_info["git_commit"],
        git_branch=git_info["git_branch"],
        git_dirty=git_info["git_dirty"],
        cache_roots=_cache_roots(),
        tool_paths=_tool_paths(),
        gpu_attributes={
            "persistence_mode": gpu_info["persistence_mode"],
            "graphics_clock_mhz": gpu_info["graphics_clock_mhz"],
            "memory_clock_mhz": gpu_info["memory_clock_mhz"],
            "power_limit_w": gpu_info["power_limit_w"],
        },
    )


def capture_invocation_metadata(
    command: str,
    *,
    experiment_config_path: str | None = None,
    kernel_config_path: str | None = None,
    counter_config_path: str | None = None,
    study_config_path: str | None = None,
    campaign_config_path: str | None = None,
    seed: int | None = None,
    repeat_index: int | None = None,
    selector_revision_id: str | None = None,
    campaign_id: str | None = None,
) -> InvocationMetadata:
    return InvocationMetadata(
        command=command,
        experiment_config_path=experiment_config_path,
        kernel_config_path=kernel_config_path,
        counter_config_path=counter_config_path,
        study_config_path=study_config_path,
        campaign_config_path=campaign_config_path,
        seed=seed,
        repeat_index=repeat_index,
        selector_revision_id=selector_revision_id,
        campaign_id=campaign_id,
    )


def capture_slurm_metadata() -> SlurmMetadata | None:
    if not os.environ.get("SLURM_JOB_ID"):
        return None
    return SlurmMetadata(
        job_id=os.environ.get("SLURM_JOB_ID"),
        array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
        partition=os.environ.get("SLURM_JOB_PARTITION"),
        node_name=os.environ.get("SLURMD_NODENAME") or os.environ.get("SLURM_NODELIST"),
        gres=os.environ.get("SLURM_JOB_GRES"),
        cpus_per_task=os.environ.get("SLURM_CPUS_PER_TASK"),
        mem=os.environ.get("SLURM_MEM_PER_NODE") or os.environ.get("SLURM_MEM_PER_CPU"),
    )


def require_gpu_environment(expected_partition: str | None, expected_node_name: str | None) -> None:
    if expected_partition:
        actual_partition = os.environ.get("SLURM_JOB_PARTITION")
        if actual_partition and actual_partition != expected_partition:
            raise RuntimeError(
                f"expected partition '{expected_partition}' but found '{actual_partition}'"
            )
    if expected_node_name:
        actual_node = os.environ.get("SLURMD_NODENAME") or os.environ.get("SLURM_NODELIST")
        if actual_node and actual_node != expected_node_name:
            raise RuntimeError(f"expected node '{expected_node_name}' but found '{actual_node}'")


def python_command() -> str:
    return sys.executable
