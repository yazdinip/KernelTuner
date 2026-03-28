from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pandas as pd

from kernel_tuner.common.config import load_counter_set, load_experiment_spec
from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import CandidateConfig, Manifest, ProfileMeasurement, ProfileStatus
from kernel_tuner.experiments.orchestrator import _profile_shapes
from kernel_tuner.profiling.adapter import ProfileOutcome, _parse_counter_map, profile_candidate, profile_experiment
from kernel_tuner.profiling.compatibility import validate_counter_set


def test_validate_counter_set_requires_kernel_regex_for_reportable(monkeypatch):
    counter_set = load_counter_set(Path("configs/counters/compute_lite.yaml"))
    counter_set.kernel_name_regex = None

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="\n".join(counter_set.counters),
            stderr="",
        ),
    )

    record = validate_counter_set(
        counter_set,
        kernel_family="gemm",
        supports_profiling=True,
        require_reportable_constraints=True,
    )

    assert record.acceptable is False
    assert "kernel_name_regex" in (record.notes or "")


def test_profile_experiment_prefers_valid_candidate(monkeypatch):
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    shape = experiment_spec.shapes[0]
    picked: list[str] = []

    invalid = CandidateConfig(
        experiment_id=experiment_spec.experiment_id,
        kernel_id=experiment_spec.kernels[0],
        shape_id=shape.shape_id,
        config_id="cfg_invalid",
        config={"block_m": 64},
        is_valid=False,
    )
    valid = CandidateConfig(
        experiment_id=experiment_spec.experiment_id,
        kernel_id=experiment_spec.kernels[0],
        shape_id=shape.shape_id,
        config_id="cfg_valid",
        config={"block_m": 128},
        is_valid=True,
    )

    monkeypatch.setattr(
        "kernel_tuner.profiling.adapter.generate_candidate_bundle",
        lambda *args, **kwargs: {
            "records": [invalid, valid],
            "metadata": {},
        },
    )
    monkeypatch.setattr(
        "kernel_tuner.experiments.orchestrator._shape_split",
        lambda spec: ([shape], []),
    )
    monkeypatch.setattr(
        "kernel_tuner.experiments.orchestrator._profile_shapes",
        lambda spec, calibration_shapes: calibration_shapes,
    )

    def fake_profile_candidate(**kwargs):
        picked.append(kwargs["candidate"].config_id)
        measurement = ProfileMeasurement(
            run_id="standalone",
            strategy_id="profile_cli",
            kernel_id=kwargs["kernel_id"],
            shape_id=kwargs["shape"].shape_id,
            config_id=kwargs["candidate"].config_id,
            counter_set_id=kwargs["counter_set"].counter_set_id,
            profile_status=ProfileStatus.SUCCESS,
            counter_map={},
        )
        return ProfileOutcome(measurement=measurement)

    monkeypatch.setattr("kernel_tuner.profiling.adapter.profile_candidate", fake_profile_candidate)

    result = profile_experiment(experiment_spec)

    assert picked == ["cfg_valid"]
    assert result["measurements"][0]["config_id"] == "cfg_valid"


def test_profile_shapes_honors_first_calibration_mode():
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    experiment_spec.profile_policy.shape_sampling_mode = "first_calibration"
    calibration_shapes = list(reversed(experiment_spec.shapes[:3]))

    selected = _profile_shapes(experiment_spec, calibration_shapes)

    assert [shape.shape_id for shape in selected] == [calibration_shapes[0].shape_id]


def test_parse_counter_map_reports_ambiguous_kernel_attribution_as_no_row():
    stdout = "\n".join(
        [
            '"ID","Process ID","Process Name","Host Name","Kernel Name","gpu__time_duration.sum","metric_a"',
            '1,10,"python","host","kernel_a",5.0,1.0',
            '2,10,"python","host","kernel_b",6.0,2.0',
        ]
    )

    counter_map, missing_counters, matched_kernel_name, diagnostics = _parse_counter_map(
        stdout,
        ["metric_a"],
        kernel_name_regex="kernel_",
    )

    assert matched_kernel_name is None
    assert missing_counters == ["metric_a"]
    assert counter_map == {"metric_a": None}
    assert diagnostics["kernel_attribution_status"] == "regex_ambiguous"


def test_profile_candidate_marks_ambiguous_kernel_attribution_as_no_profile_data(monkeypatch):
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    counter_set = load_counter_set(Path("configs/counters/compute_lite.yaml"))
    counter_set.kernel_name_regex = "kernel_"
    shape = experiment_spec.shapes[0]
    candidate = CandidateConfig(
        experiment_id=experiment_spec.experiment_id,
        kernel_id=experiment_spec.kernels[0],
        shape_id=shape.shape_id,
        config_id="cfg_valid",
        config={"block_m": 128},
        is_valid=True,
    )

    ambiguous_stdout = "\n".join(
        [
            '"ID","Process ID","Process Name","Host Name","Kernel Name","gpu__time_duration.sum","sm__warps_active.avg.pct_of_peak_sustained_active"',
            '1,10,"python","host","kernel_a",5.0,1.0',
            '2,10,"python","host","kernel_b",6.0,2.0',
        ]
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=ambiguous_stdout,
            stderr="",
        ),
    )

    outcome = profile_candidate(
        run_id="run_001",
        strategy_id="prune_rank_profiled",
        kernel_id=experiment_spec.kernels[0],
        shape=shape,
        candidate=candidate,
        counter_set=counter_set,
        experiment_spec=experiment_spec,
    )

    assert outcome.measurement.profile_status == ProfileStatus.NO_PROFILE_DATA
    assert outcome.measurement.profiler_metadata["kernel_attribution_status"] == "regex_ambiguous"


def test_profile_candidate_records_missing_counter_failure_reason(monkeypatch):
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    counter_set = load_counter_set(Path("configs/counters/compute_lite.yaml"))
    shape = experiment_spec.shapes[0]
    candidate = CandidateConfig(
        experiment_id=experiment_spec.experiment_id,
        kernel_id=experiment_spec.kernels[0],
        shape_id=shape.shape_id,
        config_id="cfg_valid",
        config={"block_m": 128},
        is_valid=True,
    )

    stdout = "\n".join(
        [
            '"ID","Process ID","Process Name","Host Name","Kernel Name","gpu__time_duration.sum","sm__warps_active.avg.pct_of_peak_sustained_active"',
            '1,10,"python","host","matmul_kernel",5.0,1.0',
        ]
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    )

    outcome = profile_candidate(
        run_id="run_001",
        strategy_id="prune_rank_profiled",
        kernel_id=experiment_spec.kernels[0],
        shape=shape,
        candidate=candidate,
        counter_set=counter_set,
        experiment_spec=experiment_spec,
    )

    assert outcome.measurement.profile_status == ProfileStatus.UNSUPPORTED_COUNTER
    assert outcome.measurement.profiler_metadata["failure_reason"] == "missing_counter_values"
    assert "missing or unsupported counters" in (outcome.measurement.notes or "")
