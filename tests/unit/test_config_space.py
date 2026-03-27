from pathlib import Path

import pytest

from kernel_tuner.common.config import load_experiment_spec
from kernel_tuner.config_space import generate_candidate_configs
from kernel_tuner.config_space.generator import CandidateSpaceOverflowError, generate_candidate_bundle


def test_generate_candidate_configs_example():
    spec = load_experiment_spec(Path("configs/experiments/gemm_smoke.example.yaml"))
    result = generate_candidate_configs(spec, experiment_path=Path("configs/experiments/gemm_smoke.example.yaml"))
    assert result["candidate_count"] == 24
    assert result["generation_metadata"]["raw_config_count"] == 24
    assert result["generation_metadata"]["valid_config_count"] == 24
    assert result["generation_metadata"]["overflowed"] is False
    config_ids = [record["config_id"] for record in result["records"]]
    assert len(config_ids) == len(set(config_ids))


def test_generate_candidate_bundle_raises_on_valid_space_overflow(tmp_path):
    experiment_path = tmp_path / "gemm_overflow.yaml"
    experiment_path.write_text(
        "\n".join(
            [
                "experiment_id: gemm_overflow",
                "study_kind: development",
                "kernels: [gemm]",
                "shapes:",
                "  - shape_id: gemm_m128_n128_k128_fp16_rowmajor",
                "    dimensions: {m: 128, n: 128, k: 128}",
                "    dtype: fp16",
                "    layout: row_major",
                "    workload_class: smoke",
                "selector_modes: [prune_only]",
                "baselines: [default_config]",
                "budgets:",
                "  max_candidates: 23",
                "  max_benchmarks: 8",
                "  max_profiles: 4",
                "  wall_clock_limit_s: 300",
                "calibration_split: 1.0",
                "held_out_split: 0.0",
                "artifact_root: artifacts",
                "counter_set_id: default_calibration",
                "seed: 7",
            ]
        ),
        encoding="utf-8",
    )
    spec = load_experiment_spec(experiment_path)

    with pytest.raises(CandidateSpaceOverflowError) as exc_info:
        generate_candidate_bundle(spec, experiment_path=experiment_path)

    assert exc_info.value.metadata["raw_config_count"] == 24
    assert exc_info.value.metadata["valid_config_count"] == 24
    assert exc_info.value.metadata["max_candidates"] == 23
