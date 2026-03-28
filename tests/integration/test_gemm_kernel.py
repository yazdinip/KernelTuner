from pathlib import Path

import pytest

from kernel_tuner.common.config import load_kernel_spec
from kernel_tuner.common.schema import ProblemShape
from kernel_tuner.kernels.registry import resolve_kernel


@pytest.mark.skipif(
    pytest.importorskip("torch").cuda.is_available() is False,
    reason="CUDA is required for Triton kernel validation",
)
def test_gemm_grouped_launch_and_oversized_tiles_validate_correctly():
    spec = load_kernel_spec(Path("configs/kernels/gemm_v2.yaml"))
    kernel = resolve_kernel(spec)
    shape = ProblemShape(
        shape_id="gemm_m128_n128_k64_fp16_rowmajor",
        dimensions={"m": 128, "n": 128, "k": 64},
        dtype="fp16",
        layout="row_major",
        workload_class="smoke",
    )
    config = {
        "block_m": 256,
        "block_n": 256,
        "block_k": 64,
        "group_size_m": 8,
        "num_warps": 4,
        "num_stages": 2,
    }

    valid, reason = kernel.supports_config(shape, config)
    assert valid, reason

    inputs = kernel.make_inputs(shape, seed=7)
    candidate = kernel.run_kernel(inputs, shape, config)
    reference = kernel.reference_impl(inputs, spec.correctness_policy)

    assert kernel.validate_output(candidate, reference, spec.correctness_policy)


@pytest.mark.skipif(
    pytest.importorskip("torch").cuda.is_available() is False,
    reason="CUDA is required for Triton kernel validation",
)
def test_gemm_split_k_executes_correctly():
    spec = load_kernel_spec(Path("configs/kernels/gemm_v3.yaml"))
    kernel = resolve_kernel(spec)
    shape = ProblemShape(
        shape_id="gemm_m128_n128_k128_fp16_rowmajor",
        dimensions={"m": 128, "n": 128, "k": 128},
        dtype="fp16",
        layout="row_major",
        workload_class="smoke",
    )
    config = {
        "block_m": 128,
        "block_n": 128,
        "block_k": 32,
        "group_size_m": 1,
        "num_stages": 2,
        "num_warps": 4,
        "split_k": 2,
    }

    valid, reason = kernel.supports_config(shape, config)
    assert valid, reason

    inputs = kernel.make_inputs(shape, seed=7)
    candidate = kernel.run_kernel(inputs, shape, config)
    reference = kernel.reference_impl(inputs, spec.correctness_policy)

    assert kernel.validate_output(candidate, reference, spec.correctness_policy)


def test_gemm_split_k_rejects_non_divisible_reduction():
    spec = load_kernel_spec(Path("configs/kernels/gemm_v3.yaml"))
    kernel = resolve_kernel(spec)
    shape = ProblemShape(
        shape_id="gemm_m128_n128_k96_fp16_rowmajor",
        dimensions={"m": 128, "n": 128, "k": 96},
        dtype="fp16",
        layout="row_major",
        workload_class="smoke",
    )
    config = {
        "block_m": 128,
        "block_n": 128,
        "block_k": 32,
        "group_size_m": 1,
        "num_stages": 2,
        "num_warps": 4,
        "split_k": 5,
    }

    valid, reason = kernel.supports_config(shape, config)
    assert not valid
    assert reason == "split_k requires a divisible reduction dimension"
