"""Triton LayerNorm kernel wrapper."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

from kernel_tuner.common.schema import CorrectnessPolicy, KernelSpec, ProblemShape


@functools.lru_cache(maxsize=1)
def _load_triton_components():
    import triton
    import triton.language as tl

    @triton.jit
    def layer_norm_kernel(
        x_ptr,
        y_ptr,
        stride_x_row,
        stride_y_row,
        hidden_size,
        eps,
        BLOCK_SIZE: tl.constexpr,
    ):
        row = tl.program_id(axis=0)
        cols = tl.arange(0, BLOCK_SIZE)
        x_ptrs = x_ptr + row * stride_x_row + cols
        mask = cols < hidden_size
        x = tl.load(x_ptrs, mask=mask, other=0.0).to(tl.float32)
        mean = tl.sum(x, axis=0) / hidden_size
        centered = tl.where(mask, x - mean, 0.0)
        variance = tl.sum(centered * centered, axis=0) / hidden_size
        inv_std = tl.rsqrt(variance + eps)
        y = centered * inv_std
        y_ptrs = y_ptr + row * stride_y_row + cols
        tl.store(y_ptrs, y.to(tl.float16), mask=mask)

    return triton, layer_norm_kernel


def _dtype_from_name(name: str):
    import torch

    mapping = {
        "fp16": torch.float16,
        "bf16": torch.bfloat16,
    }
    if name not in mapping:
        raise ValueError(f"unsupported dtype '{name}'")
    return mapping[name]


def _dtype_size(name: str) -> int:
    sizes = {"fp16": 2, "bf16": 2}
    if name not in sizes:
        raise ValueError(f"unsupported dtype '{name}'")
    return sizes[name]


@dataclass
class LayerNormKernel:
    spec: KernelSpec

    def make_inputs(self, shape: ProblemShape, *, seed: int, device: str = "cuda") -> dict[str, Any]:
        import torch

        dtype = _dtype_from_name(shape.dtype or "fp16")
        rows = shape.dim("rows")
        hidden = shape.dim("hidden")
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed)
        x = torch.randn((rows, hidden), generator=generator, dtype=torch.float32).to(device=device, dtype=dtype)
        out = torch.empty_like(x)
        return {"x": x, "out": out}

    def supports_config(self, shape: ProblemShape, config: dict[str, int]) -> tuple[bool, str | None]:
        if shape.dtype not in self.spec.dtype_support:
            return False, f"dtype '{shape.dtype}' not declared in kernel spec"
        required = {"block_size", "num_warps", "num_stages"}
        missing = required - set(config)
        if missing:
            return False, f"missing config parameters: {sorted(missing)}"
        if config["block_size"] <= 0 or config["num_warps"] <= 0 or config["num_stages"] <= 0:
            return False, "block_size, num_warps, and num_stages must be positive"
        if config["block_size"] < shape.dim("hidden"):
            return False, "block_size must cover the full hidden dimension in v1"
        if config["block_size"] & (config["block_size"] - 1):
            return False, "block_size must be a power of two"
        return True, None

    def run_kernel(self, inputs: dict[str, Any], shape: ProblemShape, config: dict[str, int]) -> Any:
        _, layer_norm_kernel = _load_triton_components()
        rows = shape.dim("rows")
        hidden = shape.dim("hidden")
        layer_norm_kernel[(rows,)](
            inputs["x"],
            inputs["out"],
            inputs["x"].stride(0),
            inputs["out"].stride(0),
            hidden,
            1e-5,
            BLOCK_SIZE=config["block_size"],
            num_warps=config["num_warps"],
            num_stages=config["num_stages"],
        )
        return inputs["out"]

    def reference_impl(self, inputs: dict[str, Any], policy: CorrectnessPolicy | None) -> Any:
        import torch
        import torch.nn.functional as F

        reference = F.layer_norm(inputs["x"].float(), (inputs["x"].shape[-1],))
        if policy and policy.reference_dtype == "fp32":
            return reference
        return reference.to(dtype=inputs["out"].dtype)

    def validate_output(
        self,
        candidate_output: Any,
        reference_output: Any,
        policy: CorrectnessPolicy | None,
    ) -> bool:
        import torch

        atol = policy.atol if policy else 1e-2
        rtol = policy.rtol if policy else 1e-2
        return bool(torch.allclose(candidate_output.float(), reference_output.float(), atol=atol, rtol=rtol))

    def performance_metric(
        self,
        shape: ProblemShape,
        config: dict[str, int],
        latency_median_us: float,
    ) -> tuple[float | None, str | None]:
        bytes_moved = 3.0 * shape.dim("rows") * shape.dim("hidden") * _dtype_size(shape.dtype or "fp16")
        gb_per_s = bytes_moved / (latency_median_us / 1_000_000.0) / 1_000_000_000.0
        return gb_per_s, "GB/s"

    def estimate_signal_defaults(self, shape: ProblemShape, config: dict[str, int]) -> dict[str, float | int]:
        occupancy = min(1.0, 8.0 / float(config["num_warps"]))
        return {
            "shared_memory_bytes": 0,
            "occupancy_estimate": occupancy,
        }

    def compile_metadata(self, inputs: dict[str, Any], shape: ProblemShape, config: dict[str, int]) -> dict[str, Any]:
        _, layer_norm_kernel = _load_triton_components()
        metadata: dict[str, Any] = self.estimate_signal_defaults(shape, config)
        metadata["register_count"] = None
        metadata["signal_backend"] = "heuristic_fallback"
        metadata["occupancy_method"] = "warps_only"
        try:
            compiled = layer_norm_kernel.warmup(
                inputs["x"],
                inputs["out"],
                inputs["x"].stride(0),
                inputs["out"].stride(0),
                shape.dim("hidden"),
                1e-5,
                BLOCK_SIZE=config["block_size"],
                num_warps=config["num_warps"],
                num_stages=config["num_stages"],
                grid=(1,),
            )
            reg_count = getattr(compiled, "n_regs", None) or getattr(compiled, "n_registers", None)
            if reg_count is not None:
                metadata["register_count"] = int(reg_count)
                metadata["signal_backend"] = "triton_warmup"
        except Exception as exc:  # pragma: no cover - Triton API varies
            metadata["notes"] = f"warmup metadata unavailable: {exc}"
        return metadata
