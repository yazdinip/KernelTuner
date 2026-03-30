from pathlib import Path

import pytest

from kernel_tuner.common.config import load_kernel_spec
from kernel_tuner.common.schema import ProblemShape
from kernel_tuner.kernels.registry import resolve_kernel


@pytest.mark.skipif(
    pytest.importorskip("torch").cuda.is_available() is False,
    reason="CUDA is required for Triton kernel validation",
)
def test_layernorm_block_size_larger_than_hidden_validates_correctly():
    spec = load_kernel_spec(Path("configs/kernels/layernorm.yaml"))
    kernel = resolve_kernel(spec)
    shape = ProblemShape(
        shape_id="layernorm_rows2048_hidden768_fp16_rowmajor",
        dimensions={"rows": 2048, "hidden": 768},
        dtype="fp16",
        layout="row_major",
        workload_class="large_batch",
    )
    config = {"block_size": 4096, "num_warps": 4, "num_stages": 2}

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
def test_layernorm_rows_per_program_validates_correctly():
    spec = load_kernel_spec(Path("configs/kernels/layernorm_v2.yaml"))
    kernel = resolve_kernel(spec)
    shape = ProblemShape(
        shape_id="layernorm_rows128_hidden4096_fp16_rowmajor",
        dimensions={"rows": 128, "hidden": 4096},
        dtype="fp16",
        layout="row_major",
        workload_class="small_batch",
    )
    config = {
        "block_size": 4096,
        "num_warps": 4,
        "num_stages": 2,
        "rows_per_program": 4,
    }

    valid, reason = kernel.supports_config(shape, config)
    assert valid, reason

    inputs = kernel.make_inputs(shape, seed=7)
    candidate = kernel.run_kernel(inputs, shape, config)
    reference = kernel.reference_impl(inputs, spec.correctness_policy)

    assert kernel.validate_output(candidate, reference, spec.correctness_policy)
