from pathlib import Path

import pytest

from kernel_tuner.common.config import load_experiment_spec, load_kernel_spec


def test_load_kernel_spec_example():
    spec = load_kernel_spec(Path("configs/kernels/gemm.example.yaml"))
    assert spec.kernel_id == "gemm"
    assert spec.default_config is not None


def test_load_experiment_spec_example():
    spec = load_experiment_spec(Path("configs/experiments/gemm_smoke.example.yaml"))
    assert spec.experiment_id == "gemm_smoke"
    assert spec.shapes[0].shape_id == "gemm_m128_n128_k128_fp16_rowmajor"


def test_reportable_requires_holdout(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "\n".join(
            [
                "experiment_id: bad",
                "study_kind: reportable",
                "kernels: [gemm]",
                "shapes:",
                "  - shape_id: gemm_m128_n128_k128_fp16_row_major",
                "    m: 128",
                "    n: 128",
                "    k: 128",
                "    dtype: fp16",
                "    layout: row_major",
                "selector_modes: [prune_only]",
                "baselines: [default_config]",
                "budgets:",
                "  max_candidates: 24",
                "  max_benchmarks: 12",
                "  max_profiles: 4",
                "  seed: 7",
                "calibration_split: 1.0",
                "held_out_split: 0.0",
                "artifact_root: artifacts",
                "seed: 7",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_experiment_spec(path)
