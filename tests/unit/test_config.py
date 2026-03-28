from pathlib import Path

import pytest

from kernel_tuner.common.config import (
    load_counter_set,
    load_campaign_spec,
    load_experiment_spec,
    load_kernel_spec,
    load_selector_revision_spec,
    load_study_spec,
)


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


def test_load_validation_study_spec():
    spec = load_study_spec(Path("configs/studies/validation_phase.yaml"))
    assert spec.study_id == "validation_phase"
    assert {hypothesis.hypothesis_id for hypothesis in spec.hypotheses} == {"H1", "H2", "H3", "H4"}
    assert all(hypothesis.clauses for hypothesis in spec.hypotheses)


def test_load_campaign_spec():
    spec = load_campaign_spec(Path("configs/campaigns/validation_rounds.yaml"))
    assert spec.campaign_id == "validation_rounds"
    assert len(spec.templates) >= 3


def test_load_selector_revision_spec():
    spec = load_selector_revision_spec(Path("configs/selector_revisions/v2_validation.yaml"))
    assert spec.revision_id == "v2_validation"
    assert spec.ranking_features[0].feature_name == "warps_active"


def test_load_frontier_aware_selector_revision_spec():
    spec = load_selector_revision_spec(Path("configs/selector_revisions/v3_h4_targeted.yaml"))
    assert spec.revision_id == "v3_h4_targeted"
    assert spec.frontier_ranking_features[0].feature_name == "tile_area"


def test_load_layernorm_baselinefix_experiment_spec():
    spec = load_experiment_spec(Path("configs/experiments/layernorm_reportable_g3_baselinefix.yaml"))
    assert spec.experiment_id == "layernorm_reportable_g3_baselinefix"
    assert spec.kernels == ["layernorm_baselinefix"]


def test_load_layernorm_regime_diag_experiment_spec():
    spec = load_experiment_spec(Path("configs/experiments/layernorm_diag_regimes_g3.yaml"))
    assert spec.experiment_id == "layernorm_diag_regimes_g3"
    assert spec.kernels == ["layernorm_regime_diag"]
    assert spec.calibration_split == 1.0
    assert spec.held_out_split == 0.0


def test_load_phase2_kernel_specs():
    gemm_spec = load_kernel_spec(Path("configs/kernels/gemm_v2.yaml"))
    layernorm_spec = load_kernel_spec(Path("configs/kernels/layernorm_v2.yaml"))

    assert gemm_spec.kernel_id == "gemm_v2"
    assert "group_size_m" in gemm_spec.config_parameters
    assert layernorm_spec.kernel_id == "layernorm_v2"
    assert "rows_per_program" in layernorm_spec.config_parameters


def test_load_phase2_counter_set():
    spec = load_counter_set(Path("configs/counters/memory_activity_lite.yaml"))

    assert spec.counter_set_id == "memory_activity_lite"
    assert any(counter.startswith("sm__warps_active") for counter in spec.counters)


def test_load_phase2_selector_revision_ablation():
    spec = load_selector_revision_spec(Path("configs/selector_revisions/v3_frontier_only.yaml"))

    assert spec.revision_id == "v3_frontier_only"
    assert spec.ranking_features == []
    assert spec.frontier_ranking_features[0].feature_name == "tile_area"


def test_load_phase2_experiment_specs():
    gemm_spec = load_experiment_spec(Path("configs/experiments/gemm_v2_reportable.yaml"))
    layernorm_spec = load_experiment_spec(Path("configs/experiments/layernorm_v2_small_reportable.yaml"))

    assert gemm_spec.experiment_id == "gemm_v2_reportable"
    assert gemm_spec.kernels == ["gemm_v2"]
    assert gemm_spec.analysis_settings.reportability_target == "rtx_a6000_pool"
    assert layernorm_spec.experiment_id == "layernorm_v2_small_reportable"
    assert layernorm_spec.kernels == ["layernorm_v2"]
    assert layernorm_spec.counter_set_id == "memory_activity_lite"


def test_load_phase2_study_and_campaign_specs():
    study = load_study_spec(Path("configs/studies/gemm_v2_baseline_mapping.yaml"))
    campaign = load_campaign_spec(Path("configs/campaigns/gemm_v2_selector_ablation.yaml"))

    assert study.study_id == "gemm_v2_baseline_mapping"
    assert {hypothesis.hypothesis_id for hypothesis in study.hypotheses} == {"H1_phase2_gemm", "H4_phase2_gemm"}
    assert campaign.campaign_id == "gemm_v2_selector_ablation"
    assert len(campaign.templates) == 6


def test_load_phase3_kernel_counter_and_selector_specs():
    kernel = load_kernel_spec(Path("configs/kernels/gemm_v3.yaml"))
    counter = load_counter_set(Path("configs/counters/compute_schedule_diag.yaml"))
    frontier = load_selector_revision_spec(Path("configs/selector_revisions/v4_transfer_safe_frontier.yaml"))
    profiled = load_selector_revision_spec(Path("configs/selector_revisions/v4_transfer_safe_profiled.yaml"))

    assert kernel.kernel_id == "gemm_v3"
    assert "split_k" in kernel.config_parameters
    assert counter.counter_set_id == "compute_schedule_diag"
    assert counter.diagnostic_only is True
    assert frontier.revision_id == "v4_transfer_safe_frontier"
    assert profiled.revision_id == "v4_transfer_safe_profiled"


def test_load_phase3_experiment_study_and_campaign_specs():
    experiment = load_experiment_spec(Path("configs/experiments/gemm_v3_reportable.yaml"))
    layernorm = load_experiment_spec(Path("configs/experiments/layernorm_v2_small_microstudy.yaml"))
    study = load_study_spec(Path("configs/studies/gemm_v3_baseline_mapping.yaml"))
    campaign = load_campaign_spec(Path("configs/campaigns/gemm_v3_selector_ablation.yaml"))

    assert experiment.experiment_id == "gemm_v3_reportable"
    assert experiment.kernels == ["gemm_v3"]
    assert experiment.budgets.max_candidates == 648
    assert layernorm.experiment_id == "layernorm_v2_small_microstudy"
    assert layernorm.selector_version == "phase3_layernorm_micro"
    assert {hypothesis.hypothesis_id for hypothesis in study.hypotheses} == {"H1_phase3_gemm", "H5_phase3_gemm"}
    assert campaign.campaign_id == "gemm_v3_selector_ablation"
    assert len(campaign.templates) == 6
