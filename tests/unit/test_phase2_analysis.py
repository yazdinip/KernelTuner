from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from kernel_tuner.analysis.comparison import _build_stability_report, _build_strategy_rows
from kernel_tuner.analysis.opportunities import (
    build_bottleneck_signatures,
    build_counter_availability_records,
    build_opportunity_catalog,
)
from kernel_tuner.common.config import load_experiment_spec, load_kernel_spec
from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import Manifest


def test_counter_availability_records_apply_threshold():
    profile_measurements = pd.DataFrame(
        [
            {
                "strategy_id": "prune_rank_profiled",
                "counter_set_id": "compute_lite",
                "profile_status": "success",
                "counter_map": {"counter_a": 1.0, "counter_b": 2.0},
            },
            {
                "strategy_id": "prune_rank_profiled",
                "counter_set_id": "compute_lite",
                "profile_status": "unsupported_counter",
                "counter_map": {"counter_a": 1.0, "counter_b": None},
            },
        ]
    )

    records = build_counter_availability_records(
        run_id="run_001",
        profile_measurements=profile_measurements,
        requested_counters=["counter_a", "counter_b"],
        minimum_availability=0.9,
    )

    record_map = {record.counter_name: record for record in records}
    assert record_map["counter_a"].acceptable is True
    assert record_map["counter_b"].acceptable is False


def test_build_stability_report_computes_selection_agreement_and_band():
    strategy_rows = pd.DataFrame(
        [
            {
                "group_id": "gemm_representative",
                "kernel_family": "gemm",
                "workload_class": "square_compute",
                "strategy_id": "prune_rank",
                "run_id": "run_a",
                "selected_config_id": "cfg_1",
                "geomean_speedup_vs_default_config": 1.02,
            },
            {
                "group_id": "gemm_representative",
                "kernel_family": "gemm",
                "workload_class": "square_compute",
                "strategy_id": "prune_rank",
                "run_id": "run_b",
                "selected_config_id": "cfg_1",
                "geomean_speedup_vs_default_config": 0.98,
            },
            {
                "group_id": "gemm_representative",
                "kernel_family": "gemm",
                "workload_class": "square_compute",
                "strategy_id": "prune_rank",
                "run_id": "run_c",
                "selected_config_id": "cfg_2",
                "geomean_speedup_vs_default_config": 1.00,
            },
        ]
    )

    report = _build_stability_report(strategy_rows)

    assert len(report) == 1
    row = report.iloc[0]
    assert row["selection_agreement"] == 2 / 3
    assert row["stability_band"] > 0


def test_build_strategy_rows_preserves_kernel_family_and_workload_class():
    experiment_spec = load_experiment_spec(Path("configs/experiments/layernorm_reportable.yaml"))
    kernel_spec = load_kernel_spec(Path("configs/kernels/layernorm.yaml"))
    summary = {
        "run_id": "run_001",
        "reportability": {"is_reportable": True},
    }
    manifest = Manifest(
        experiment_id=experiment_spec.experiment_id,
        run_id="run_001",
        created_at_utc=datetime.now(timezone.utc),
        environment=capture_environment_metadata("."),
        invocation=capture_invocation_metadata("pytest"),
        artifact_files=[],
    )
    selection = pd.DataFrame(
        [
            {"strategy_id": "default_config", "selected_config_id": "cfg_default"},
            {"strategy_id": "prune_rank", "selected_config_id": "cfg_best"},
        ]
    )
    runtime = pd.DataFrame(
        [
            {
                "strategy_id": "default_config",
                "measurement_phase": "calibration",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_default",
                "latency_median_us": 10.0,
            },
            {
                "strategy_id": "prune_rank",
                "measurement_phase": "calibration",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_best",
                "latency_median_us": 9.0,
            },
        ]
    )
    held_out_per_shape = pd.DataFrame(
        [
            {
                "shape_id": experiment_spec.shapes[0].shape_id,
                "workload_class": "small_batch",
                "strategy_id": "default_config",
                "latency_median_us": 10.0,
                "winner_on_shape": False,
            },
            {
                "shape_id": experiment_spec.shapes[0].shape_id,
                "workload_class": "small_batch",
                "strategy_id": "prune_rank",
                "latency_median_us": 8.0,
                "winner_on_shape": True,
            },
        ]
    )

    rows = _build_strategy_rows(
        [
            {
                "group_id": "layernorm_representative",
                "summary": summary,
                "experiment_spec": experiment_spec,
                "kernel_spec": kernel_spec,
                "manifest": manifest,
                "selection_decisions": selection,
                "runtime_measurements": runtime,
                "held_out_per_shape": held_out_per_shape,
                "counter_availability": pd.DataFrame(),
                "opportunity_catalog": pd.DataFrame(),
            }
        ]
    )

    assert set(rows["kernel_family"]) == {"layernorm"}
    assert set(rows["workload_class"]) == {"small_batch"}


def test_opportunity_catalog_contains_expected_template():
    experiment_spec = load_experiment_spec(Path("configs/experiments/gemm_development.yaml"))
    compile_signals = pd.DataFrame(
        [
            {
                "run_id": "run_001",
                "kernel_id": "gemm",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_bad",
                "compile_status": "success",
                "compile_success": True,
                "register_count": 128,
                "shared_memory_bytes": 4096,
                "occupancy_estimate": 0.2,
            }
        ]
    )
    runtime_measurements = pd.DataFrame(
        [
            {
                "strategy_id": "prune_rank_revised",
                "measurement_phase": "calibration",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_bad",
                "latency_median_us": 12.0,
            },
            {
                "strategy_id": "prune_rank_revised",
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_bad",
                "latency_median_us": 12.0,
            },
            {
                "strategy_id": "default_config",
                "measurement_phase": "held_out",
                "status": "success",
                "shape_id": experiment_spec.shapes[0].shape_id,
                "config_id": "cfg_good",
                "latency_median_us": 10.0,
            },
        ]
    )
    profile_measurements = pd.DataFrame(
        [
            {
                "strategy_id": "prune_rank_revised",
                "counter_set_id": "compute_lite",
                "config_id": "cfg_bad",
                "profile_status": "success",
                "counter_map": {
                    "sm__warps_active.avg.pct_of_peak_sustained_active": 10.0,
                    "smsp__inst_executed_pipe_tensor_op_hmma": 1.0,
                },
            }
        ]
    )
    selection_decisions = pd.DataFrame(
        [
            {
                "strategy_id": "prune_rank_revised",
                "selected_config_id": "cfg_bad",
            }
        ]
    )

    signatures = build_bottleneck_signatures(
        run_id="run_001",
        experiment_spec=experiment_spec,
        compile_signals=compile_signals,
        runtime_measurements=runtime_measurements,
        profile_measurements=profile_measurements,
        selection_decisions=selection_decisions,
    )
    frame = pd.DataFrame([record.model_dump(mode="json") for record in signatures])
    catalog = build_opportunity_catalog(frame)

    assert "reduce_num_stages_or_tile_size" in set(catalog["opportunity_tag"])
