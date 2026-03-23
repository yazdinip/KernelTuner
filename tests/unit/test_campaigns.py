import json
from pathlib import Path

import pytest

from kernel_tuner.analysis.comparison import validate_study_from_path
from kernel_tuner.common.config import load_campaign_spec, load_experiment_spec, load_selector_revision_spec
from kernel_tuner.common.schema import (
    AvailabilityFailureMode,
    CounterCompatibilityRecord,
    ProfileSamplingMode,
    StudyKind,
)
from kernel_tuner.experiments.campaigns import _execute_campaign, materialize_campaign
from kernel_tuner.experiments.orchestrator import _profile_shapes, _shape_split, _validate_reportability_contract
from kernel_tuner.selector.engine import run_selector_mode


def test_shape_split_is_stratified_for_reportable_workload_classes():
    spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    calibration, held_out = _shape_split(spec)

    calibration_classes = {shape.workload_class for shape in calibration}
    held_out_classes = {shape.workload_class for shape in held_out}

    assert calibration_classes == held_out_classes
    assert len(held_out) >= spec.reportability_policy.minimum_held_out_shapes


def test_materialize_campaign_creates_run_matrix(tmp_path):
    spec = load_campaign_spec(Path("configs/campaigns/validation_rounds.yaml"))
    spec.artifact_root = str(tmp_path)

    result = materialize_campaign(spec, campaign_path=Path("configs/campaigns/validation_rounds.yaml"))

    status_path = Path(result["run_dir"]) / "campaign_status.json"
    assert status_path.exists()
    assert result["job_count"] == 15


def test_materialize_campaign_preserves_execution_mode_override(tmp_path):
    spec = load_campaign_spec(Path("configs/campaigns/validation_rounds.yaml"))
    spec.artifact_root = str(tmp_path)
    spec.templates = [
        {
            "template_id": "mode_override",
            "experiment_ids": ["gemm_smoke"],
            "execution_mode": "development",
        }
    ]
    spec.studies = []

    result = materialize_campaign(spec, campaign_path=Path("configs/campaigns/validation_rounds.yaml"))

    status_path = Path(result["run_dir"]) / "campaign_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["jobs"][0]["execution_mode"] == "development"


def test_execute_campaign_skips_study_with_missing_required_templates(tmp_path):
    spec = load_campaign_spec(Path("configs/campaigns/validation_rounds.yaml"))
    spec.artifact_root = str(tmp_path)
    spec.templates = spec.templates[:1]
    spec.studies = [
        {
            "study_id": "validation_phase",
            "study_path": "configs/studies/validation_phase.yaml",
            "requires_templates": ["missing_template"],
        }
    ]

    result = materialize_campaign(spec, campaign_path=Path("configs/campaigns/validation_rounds.yaml"))
    run_dir = Path(result["run_dir"])
    status_path = run_dir / "campaign_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    for job in payload["jobs"]:
        job["status"] = "success"
        job["run_dir"] = str(run_dir / "dummy")
    payload["completed_jobs"] = len(payload["jobs"])
    payload["failed_jobs"] = 0
    payload["terminal_status"] = "running"
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    executed = _execute_campaign(run_dir)

    assert executed["terminal_status"] == "success"
    refreshed = json.loads(status_path.read_text(encoding="utf-8"))
    assert refreshed["study_results"] == [
        {
            "study_id": "validation_phase",
            "status": "skipped_requires_templates",
            "missing_templates": ["missing_template"],
        }
    ]


def test_validate_study_reports_clause_backed_hypotheses():
    result = validate_study_from_path(Path("configs/studies/validation_phase.yaml"))

    assert result["study_id"] == "validation_phase"
    assert result["all_hypotheses_have_clauses"] is True


def test_validate_reportability_contract_allows_diagnostic_downgrade():
    spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    spec.study_kind = StudyKind.REPORTABLE
    spec.profile_policy.availability_failure_mode = AvailabilityFailureMode.DOWNGRADE_TO_DIAGNOSTIC
    calibration, held_out = _shape_split(spec)
    compatibility = CounterCompatibilityRecord(
        counter_set_id="shared_diag",
        kernel_family="gemm",
        requested_counter_count=4,
        available_counter_count=4,
        missing_counters=[],
        availability_fraction=1.0,
        acceptable=False,
        diagnostic_only=True,
        kernel_family_allowed=True,
        validation_backend="test",
        notes="diagnostic-only",
    )

    warnings = _validate_reportability_contract(spec, calibration, held_out, compatibility)

    assert len(warnings) == 1
    assert "downgrading this run to diagnostic/non-comparable evidence" in warnings[0]


def test_validate_reportability_contract_fails_when_downgrade_not_allowed():
    spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    spec.study_kind = StudyKind.REPORTABLE
    spec.profile_policy.availability_failure_mode = AvailabilityFailureMode.FAIL_RUN
    calibration, held_out = _shape_split(spec)
    compatibility = CounterCompatibilityRecord(
        counter_set_id="shared_diag",
        kernel_family="gemm",
        requested_counter_count=4,
        available_counter_count=4,
        missing_counters=[],
        availability_fraction=1.0,
        acceptable=False,
        diagnostic_only=True,
        kernel_family_allowed=True,
        validation_backend="test",
        notes="diagnostic-only",
    )

    with pytest.raises(RuntimeError, match="not acceptable for reportable use"):
        _validate_reportability_contract(spec, calibration, held_out, compatibility)


def test_profile_shapes_supports_all_calibration_mode():
    spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    spec.profile_policy.shape_sampling_mode = ProfileSamplingMode.ALL_CALIBRATION
    spec.profile_policy.max_shapes_per_config = None
    calibration, _ = _shape_split(spec)

    selected = _profile_shapes(spec, calibration)

    assert [shape.shape_id for shape in selected] == [shape.shape_id for shape in calibration]


def test_profile_shapes_supports_explicit_shape_ids():
    spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    calibration, _ = _shape_split(spec)
    explicit = [calibration[0].shape_id, calibration[-1].shape_id]
    spec.profile_policy.shape_sampling_mode = ProfileSamplingMode.EXPLICIT_SHAPE_IDS
    spec.profile_policy.explicit_shape_ids = explicit
    spec.profile_policy.max_shapes_per_config = None

    selected = _profile_shapes(spec, calibration)

    assert [shape.shape_id for shape in selected] == explicit


def test_revision_backed_selector_uses_external_ranking_spec():
    revision = load_selector_revision_spec(Path("configs/selector_revisions/v2_validation.yaml"))

    decision = run_selector_mode(
        run_id="run_001",
        strategy_id="prune_rank_revised",
        selector_mode="prune_rank_revised",
        kernel_id="gemm",
        candidate_records=[],
        compile_signals=[],
        budgets=type("Budget", (), {"max_profiles": 2, "max_benchmarks": 2})(),
        request_benchmark=lambda config_id: [],
        request_profile=lambda config_id: [],
        selector_revision=revision,
    )

    assert decision.decision_status == "failed_no_candidates"
