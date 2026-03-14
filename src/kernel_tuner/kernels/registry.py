"""Kernel registry."""

from __future__ import annotations

from kernel_tuner.common.schema import KernelSpec


def resolve_kernel(spec: KernelSpec):
    if spec.family != "gemm":
        raise ValueError(f"unsupported kernel family '{spec.family}'")
    return spec
