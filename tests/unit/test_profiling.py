from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pandas as pd

from kernel_tuner.common.config import load_counter_set, load_experiment_spec
from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import CandidateConfig, Manifest, ProfileMeasurement, ProfileStatus
from kernel_tuner.profiling.adapter import ProfileOutcome, profile_experiment
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
        "kernel_tuner.profiling.adapter.generate_candidate_records",
        lambda *args, **kwargs: [invalid, valid],
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
