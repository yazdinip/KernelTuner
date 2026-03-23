import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from kernel_tuner.analysis.reporting import _load_table, _pairwise_speedups, summarize_run
from kernel_tuner.common.config import load_experiment_spec
from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import Manifest
from kernel_tuner.storage import RunStore


def _write_minimal_required_tables(store: RunStore, *, include_profile: bool = False) -> None:
    pd.DataFrame(columns=["config_id", "occupancy_estimate", "register_count", "shared_memory_bytes"]).to_parquet(
        store.run_dir / "compile_signals.parquet",
        index=False,
    )
    pd.DataFrame(
        columns=[
            "measurement_phase",
            "status",
            "shape_id",
            "strategy_id",
            "latency_median_us",
            "throughput_value",
            "config_id",
        ]
    ).to_parquet(
        store.run_dir / "runtime_measurements.parquet",
        index=False,
    )
    pd.DataFrame(
        columns=[
            "strategy_id",
            "selected_config_id",
            "benchmarks_requested",
            "profiles_requested",
            "decision_status",
            "comparison_class",
        ]
    ).to_parquet(
        store.run_dir / "selection_decisions.parquet",
        index=False,
    )
    if include_profile:
        pd.DataFrame(
            columns=["strategy_id", "counter_set_id", "profile_status", "counter_map", "config_id"]
        ).to_parquet(
            store.run_dir / "profile_measurements.parquet",
            index=False,
        )


def test_pairwise_speedups_uses_geometric_mean_of_per_shape_ratios():
    strategy_metrics = pd.DataFrame(
        [
            {
                "strategy_id": "default_config",
                "held_out_latency_mean_us": 15.0,
                "held_out_throughput_mean": 1.0,
                "held_out_measurements": 2,
            },
            {
                "strategy_id": "candidate",
                "held_out_latency_mean_us": 15.0,
                "held_out_throughput_mean": 1.0,
                "held_out_measurements": 2,
            },
        ]
    )
    runtime_measurements = pd.DataFrame(
        [
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": "shape_a",
                "strategy_id": "default_config",
                "latency_median_us": 10.0,
            },
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": "shape_b",
                "strategy_id": "default_config",
                "latency_median_us": 20.0,
            },
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": "shape_a",
                "strategy_id": "candidate",
                "latency_median_us": 5.0,
            },
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": "shape_b",
                "strategy_id": "candidate",
                "latency_median_us": 30.0,
            },
        ]
    )

    comparison = _pairwise_speedups(strategy_metrics, runtime_measurements)
    speedup = comparison.loc[comparison["strategy_id"] == "candidate", "speedup_vs_baseline"].iloc[0]

    expected = math.sqrt((10.0 / 5.0) * (20.0 / 30.0))
    assert speedup == expected


def test_load_table_raises_for_required_missing_artifact(tmp_path):
    store = RunStore(tmp_path, "exp", "run")

    with pytest.raises(FileNotFoundError):
        _load_table(store, "runtime_measurements", required=True)


def test_summarize_run_falls_back_to_manifest_experiment_config(tmp_path):
    store = RunStore(tmp_path / "artifacts", "test_experiment", "run_001")
    manifest = Manifest(
        experiment_id="test_experiment",
        run_id="run_001",
        created_at_utc=datetime.now(timezone.utc),
        environment=capture_environment_metadata("."),
        invocation=capture_invocation_metadata(
            "pytest",
            experiment_config_path=str(Path("configs/experiments/gemm_smoke.example.yaml").resolve()),
        ),
        artifact_files=[],
    )
    store.initialize_manifest(manifest)
    _write_minimal_required_tables(store, include_profile=True)

    summary = summarize_run(store.run_dir)

    assert summary["experiment_id"] == "gemm_smoke"
    assert summary["run_id"] == "run_001"


def test_summarize_run_marks_budget_limited_runs_non_reportable(tmp_path):
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_reportable.yaml"))
    store = RunStore(tmp_path, experiment_spec.experiment_id, "run_001")
    manifest = Manifest(
        experiment_id=experiment_spec.experiment_id,
        run_id="run_001",
        created_at_utc=datetime.now(timezone.utc),
        environment=capture_environment_metadata("."),
        invocation=capture_invocation_metadata(
            "pytest",
            experiment_config_path=str(Path("configs/experiments/gemm_reportable.yaml").resolve()),
        ),
        artifact_files=[],
    )
    store.initialize_manifest(manifest)
    store.write_experiment_spec(experiment_spec)

    pd.DataFrame(
        [
            {
                "kernel_id": experiment_spec.kernels[0],
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_a",
                "compile_status": "success",
                "compile_success": True,
                "occupancy_estimate": 0.5,
                "register_count": 64,
                "shared_memory_bytes": 1024,
            }
        ]
    ).to_parquet(store.run_dir / "compile_signals.parquet", index=False)
    pd.DataFrame(
        [
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "strategy_id": "default_config",
                "latency_median_us": 10.0,
                "throughput_value": 1.0,
                "config_id": "cfg_default",
            },
            {
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "strategy_id": "prune_rank",
                "latency_median_us": 9.0,
                "throughput_value": 1.0,
                "config_id": "cfg_a",
            },
        ]
    ).to_parquet(store.run_dir / "runtime_measurements.parquet", index=False)
    pd.DataFrame(
        [
            {
                "strategy_id": "prune_rank",
                "counter_set_id": experiment_spec.counter_set_id,
                "profile_status": "success",
                "counter_map": '{"sm__warps_active.avg.pct_of_peak_sustained_active": 1.0}',
                "config_id": "cfg_a",
            }
        ]
    ).to_parquet(store.run_dir / "profile_measurements.parquet", index=False)
    pd.DataFrame(
        [
            {
                "strategy_id": "default_config",
                "selected_config_id": "cfg_default",
                "benchmarks_requested": 1,
                "profiles_requested": 0,
                "decision_status": "selected",
                "comparison_class": "matched_budget",
            },
            {
                "strategy_id": "prune_rank",
                "selected_config_id": "cfg_a",
                "benchmarks_requested": 1,
                "profiles_requested": 1,
                "decision_status": "selected_budget_limited",
                "comparison_class": "matched_budget",
            },
        ]
    ).to_parquet(store.run_dir / "selection_decisions.parquet", index=False)
    (store.run_dir / "counter_compatibility.json").write_text(
        '{"acceptable": true, "counter_set_id": "compute_lite"}',
        encoding="utf-8",
    )

    summary = summarize_run(store.run_dir)

    assert summary["reportability"]["is_reportable"] is False
    assert summary["reportability"]["budget_limited_decision_present"] is True


def test_summarize_run_marks_counter_set_unaccepted_when_compatibility_fails(tmp_path):
    experiment_path = Path("configs/experiments/gemm_reportable.yaml").resolve()
    experiment_spec = load_experiment_spec(experiment_path)
    store = RunStore(tmp_path / "artifacts", "test_experiment", "run_compat")
    manifest = Manifest(
        experiment_id="test_experiment",
        run_id="run_compat",
        created_at_utc=datetime.now(timezone.utc),
        environment=capture_environment_metadata("."),
        invocation=capture_invocation_metadata(
            "pytest",
            experiment_config_path=str(experiment_path),
        ),
        artifact_files=[],
    )
    store.initialize_manifest(manifest)
    store.write_experiment_spec(experiment_spec)
    _write_minimal_required_tables(store, include_profile=True)
    store.write_json_artifact(
        "counter_compatibility",
        {
            "counter_set_id": "shared_diag",
            "acceptable": False,
            "diagnostic_only": True,
        },
        filename="counter_compatibility.json",
    )

    summary = summarize_run(store.run_dir)

    assert summary["reportability"]["counter_set_accepted"] is False
