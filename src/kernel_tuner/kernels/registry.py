"""Kernel registry."""

from __future__ import annotations

from kernel_tuner.common.schema import KernelSpec
from kernel_tuner.kernels.gemm import GemmKernel
from kernel_tuner.kernels.layernorm import LayerNormKernel


def resolve_kernel(spec: KernelSpec):
    if spec.family == "gemm":
        return GemmKernel(spec=spec)
    if spec.family == "layernorm":
        return LayerNormKernel(spec=spec)
    raise ValueError(f"unsupported kernel family '{spec.family}'")
