"""Triton GEMM kernel wrapper."""

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
    def matmul_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        acc_ptr,
        m,
        n,
        k,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        stride_acc_m,
        stride_acc_n,
        out_dtype_flag: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_SIZE_M: tl.constexpr,
        SPLIT_K: tl.constexpr,
    ):
        pid = tl.program_id(axis=0)
        pid_split = tl.program_id(axis=1)
        num_pid_m = tl.cdiv(m, BLOCK_M)
        num_pid_n = tl.cdiv(n, BLOCK_N)
        num_pid_in_group = GROUP_SIZE_M * num_pid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_SIZE_M
        group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_SIZE_M)
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        split_k_width = k // SPLIT_K
        offs_k = pid_split * split_k_width + tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn
        accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for _ in range(0, tl.cdiv(split_k_width, BLOCK_K)):
            split_limit = (pid_split + 1) * split_k_width
            a_mask = (offs_m[:, None] < m) & (offs_k[None, :] < split_limit)
            b_mask = (offs_k[:, None] < split_limit) & (offs_n[None, :] < n)
            a = tl.load(a_ptrs, mask=a_mask, other=0.0)
            b = tl.load(b_ptrs, mask=b_mask, other=0.0)
            accumulator += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            offs_k += BLOCK_K

        if out_dtype_flag == 1:
            output = accumulator.to(tl.bfloat16)
        else:
            output = accumulator.to(tl.float16)

        c_mask = (offs_m[:, None] < m) & (offs_n[None, :] < n)
        if SPLIT_K == 1:
            c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
            tl.store(c_ptrs, output, mask=c_mask)
        else:
            acc_ptrs = acc_ptr + offs_m[:, None] * stride_acc_m + offs_n[None, :] * stride_acc_n
            tl.atomic_add(acc_ptrs, accumulator, mask=c_mask)

    return triton, matmul_kernel


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
class GemmKernel:
    spec: KernelSpec

    def make_inputs(self, shape: ProblemShape, *, seed: int, device: str = "cuda") -> dict[str, Any]:
        import torch

        dtype = _dtype_from_name(shape.dtype or "fp16")
        m = shape.dim("m")
        n = shape.dim("n")
        k = shape.dim("k")
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed)
        a = torch.randn((m, k), generator=generator, dtype=torch.float32).to(device=device, dtype=dtype)
        b = torch.randn((k, n), generator=generator, dtype=torch.float32).to(device=device, dtype=dtype)
        out = torch.empty((m, n), device=device, dtype=dtype)
        return {"a": a, "b": b, "out": out}

    def supports_config(self, shape: ProblemShape, config: dict[str, int]) -> tuple[bool, str | None]:
        if shape.dtype not in self.spec.dtype_support:
            return False, f"dtype '{shape.dtype}' not declared in kernel spec"
        required = {"block_m", "block_n", "block_k", "num_warps", "num_stages"}
        missing = required - set(config)
        if missing:
            return False, f"missing config parameters: {sorted(missing)}"
        if config["block_m"] <= 0 or config["block_n"] <= 0 or config["block_k"] <= 0:
            return False, "block sizes must be positive"
        if config["num_warps"] <= 0 or config["num_stages"] <= 0:
            return False, "num_warps and num_stages must be positive"
        group_size_m = config.get("group_size_m", 1)
        if group_size_m <= 0:
            return False, "group_size_m must be positive when provided"
        split_k = config.get("split_k", 1)
        if split_k <= 0:
            return False, "split_k must be positive when provided"
        if shape.dim("k") % split_k != 0:
            return False, "split_k requires a divisible reduction dimension"
        return True, None

    def run_kernel(self, inputs: dict[str, Any], shape: ProblemShape, config: dict[str, int]) -> Any:
        triton, matmul_kernel = _load_triton_components()

        out_dtype_flag = 1 if shape.dtype == "bf16" else 0
        m, n, k = shape.dim("m"), shape.dim("n"), shape.dim("k")
        split_k = config.get("split_k", 1)
        grid = lambda meta: (triton.cdiv(m, meta["BLOCK_M"]) * triton.cdiv(n, meta["BLOCK_N"]), split_k)
        group_size_m = config.get("group_size_m", 1)
        acc_buffer = None
        if split_k > 1:
            import torch

            acc_buffer = torch.zeros((m, n), device=inputs["out"].device, dtype=torch.float32)

        matmul_kernel[grid](
            inputs["a"],
            inputs["b"],
            inputs["out"],
            acc_buffer if acc_buffer is not None else inputs["out"],
            m,
            n,
            k,
            inputs["a"].stride(0),
            inputs["a"].stride(1),
            inputs["b"].stride(0),
            inputs["b"].stride(1),
            inputs["out"].stride(0),
            inputs["out"].stride(1),
            (acc_buffer.stride(0) if acc_buffer is not None else inputs["out"].stride(0)),
            (acc_buffer.stride(1) if acc_buffer is not None else inputs["out"].stride(1)),
            out_dtype_flag=out_dtype_flag,
            BLOCK_M=config["block_m"],
            BLOCK_N=config["block_n"],
            BLOCK_K=config["block_k"],
            GROUP_SIZE_M=group_size_m,
            SPLIT_K=split_k,
            num_warps=config["num_warps"],
            num_stages=config["num_stages"],
        )
        if acc_buffer is not None:
            inputs["out"].copy_(acc_buffer.to(dtype=inputs["out"].dtype))
        return inputs["out"]

    def reference_impl(self, inputs: dict[str, Any], policy: CorrectnessPolicy | None) -> Any:
        import torch

        reference = torch.matmul(inputs["a"].float(), inputs["b"].float())
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
        flops = 2.0 * shape.dim("m") * shape.dim("n") * shape.dim("k")
        throughput = flops / (latency_median_us / 1_000_000.0) / 1_000_000_000_000.0
        return throughput, "TFLOP/s"

    def estimate_signal_defaults(self, shape: ProblemShape, config: dict[str, int]) -> dict[str, float | int]:
        shared_memory = (config["block_m"] * config["block_k"] + config["block_k"] * config["block_n"]) * _dtype_size(
            shape.dtype or "fp16"
        )
        occupancy = min(1.0, 8.0 / float(config["num_warps"]))
        return {
            "shared_memory_bytes": shared_memory,
            "occupancy_estimate": occupancy,
        }

    def compile_metadata(self, inputs: dict[str, Any], shape: ProblemShape, config: dict[str, int]) -> dict[str, Any]:
        """Best-effort metadata extraction from Triton; falls back to heuristics."""
        _, matmul_kernel = _load_triton_components()
        metadata: dict[str, Any] = self.estimate_signal_defaults(shape, config)
        metadata["register_count"] = None
        metadata["signal_backend"] = "heuristic_fallback"
        metadata["occupancy_method"] = "warps_only"
        try:
            group_size_m = config.get("group_size_m", 1)
            compiled = matmul_kernel.warmup(
                inputs["a"],
                inputs["b"],
                inputs["out"],
                inputs["out"],
                shape.dim("m"),
                shape.dim("n"),
                shape.dim("k"),
                inputs["a"].stride(0),
                inputs["a"].stride(1),
                inputs["b"].stride(0),
                inputs["b"].stride(1),
                inputs["out"].stride(0),
                inputs["out"].stride(1),
                inputs["out"].stride(0),
                inputs["out"].stride(1),
                out_dtype_flag=1 if shape.dtype == "bf16" else 0,
                BLOCK_M=config["block_m"],
                BLOCK_N=config["block_n"],
                BLOCK_K=config["block_k"],
                GROUP_SIZE_M=group_size_m,
                SPLIT_K=config.get("split_k", 1),
                num_warps=config["num_warps"],
                num_stages=config["num_stages"],
                grid=(1, config.get("split_k", 1)),
            )
            reg_count = getattr(compiled, "n_regs", None) or getattr(compiled, "n_registers", None)
            if reg_count is not None:
                metadata["register_count"] = int(reg_count)
                metadata["signal_backend"] = "triton_warmup"
        except Exception as exc:  # pragma: no cover - exact Triton metadata API varies
            metadata["notes"] = f"warmup metadata unavailable: {exc}"
        return metadata
