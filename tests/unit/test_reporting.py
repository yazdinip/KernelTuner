from datetime import datetime, timezone
from pathlib import Path
import math

import pandas as pd

from kernel_tuner.analysis.reporting import _pairwise_speedups, summarize_run
from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import Manifest
from kernel_tuner.storage import RunStore


def test_pairwise_speedups_uses_geometric_mean_of_per_shape_ratios():
    strategy_metrics = pd.DataFrame(
        [
            {"strategy_id": "default_config", "held_out_latency_mean_us": 15.0, "held_out_throughput_mean": 1.0, "held_out_measurements": 2},
            {"strategy_id": "candidate", "held_out_latency_mean_us": 15.0, "held_out_throughput_mean": 1.0, "held_out_measurements": 2},
        ]
    )
    runtime_measurements = pd.DataFrame(
        [
            {"measurement_phase": "held_out", "status": "success", "shape_id": "shape_a", "strategy_id": "default_config", "latency_median_us": 10.0},
            {"measurement_phase": "held_out", "status": "success", "shape_id": "shape_b", "strategy_id": "default_config", "latency_median_us": 20.0},
            {"measurement_phase": "held_out", "status": "success", "shape_id": "shape_a", "strategy_id": "candidate", "latency_median_us": 5.0},
            {"measurement_phase": "held_out", "status": "success", "shape_id": "shape_b", "strategy_id": "candidate", "latency_median_us": 30.0},
        ]
    )

    comparison = _pairwise_speedups(strategy_metrics, runtime_measurements)
    speedup = comparison.loc[comparison["strategy_id"] == "candidate", "speedup_vs_baseline"].iloc[0]

    expected = math.sqrt((10.0 / 5.0) * (20.0 / 30.0))
    assert speedup == expected


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

    summary = summarize_run(store.run_dir)

    assert summary["experiment_id"] == "gemm_smoke"
    assert summary["run_id"] == "run_001"
