from pathlib import Path

from kernel_tuner.analysis.comparison import validate_study_from_path
from kernel_tuner.common.config import load_campaign_spec, load_experiment_spec, load_selector_revision_spec
from kernel_tuner.experiments.campaigns import materialize_campaign
from kernel_tuner.experiments.orchestrator import _shape_split
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


def test_validate_study_reports_clause_backed_hypotheses():
    result = validate_study_from_path(Path("configs/studies/validation_phase.yaml"))

    assert result["study_id"] == "validation_phase"
    assert result["all_hypotheses_have_clauses"] is True


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
