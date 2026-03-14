"""Config loading, validation, and repo-relative path resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml

from kernel_tuner.common.ids import canonical_shape_id
from kernel_tuner.common.schema import CounterSetSpec, ExperimentSpec, KernelSpec, ProblemShape

T = TypeVar("T", KernelSpec, ExperimentSpec, CounterSetSpec)


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping at {path}")
    return data


def dump_yaml(path: str | Path, payload: dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def load_kernel_spec(path: str | Path) -> KernelSpec:
    return KernelSpec.model_validate(load_yaml(path))


def load_counter_set(path: str | Path) -> CounterSetSpec:
    return CounterSetSpec.model_validate(load_yaml(path))


def load_experiment_spec(path: str | Path) -> ExperimentSpec:
    payload = load_yaml(path)
    spec = ExperimentSpec.model_validate(payload)
    for shape in spec.shapes:
        _validate_shape_id(shape)
    return spec


def repo_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("could not locate repo root from path")


def kernel_config_path(kernel_id: str, base_path: str | Path | None = None) -> Path:
    root = repo_root(base_path)
    candidates = [
        root / "configs" / "kernels" / f"{kernel_id}.yaml",
        root / "configs" / "kernels" / f"{kernel_id}.example.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"kernel config not found for kernel_id '{kernel_id}'")


def counter_set_path(counter_set_id: str, base_path: str | Path | None = None) -> Path:
    root = repo_root(base_path)
    candidates = [
        root / "configs" / "counters" / f"{counter_set_id}.yaml",
        root / "configs" / "counters" / f"{counter_set_id}.example.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"counter set config not found for '{counter_set_id}'")


def resolve_artifact_root(
    artifact_root: str | Path,
    base_path: str | Path | None = None,
) -> Path:
    path = Path(artifact_root)
    if path.is_absolute():
        return path
    return repo_root(base_path) / path


def _validate_shape_id(shape: ProblemShape) -> None:
    expected = canonical_shape_id(
        "gemm",
        {
            "m": shape.m,
            "n": shape.n,
            "k": shape.k,
            "dtype": shape.dtype,
            "layout": shape.layout,
        },
    )
    if shape.shape_id != expected:
        raise ValueError(
            f"shape_id '{shape.shape_id}' does not match canonical GEMM shape ID '{expected}'"
        )
