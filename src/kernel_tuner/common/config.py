"""Config loading and validation."""

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
