import os
from pathlib import Path
from subprocess import CompletedProcess

from kernel_tuner.common.config import load_counter_set
from kernel_tuner.common.provenance import resolve_tool_path
from kernel_tuner.profiling.compatibility import validate_counter_set


def test_validate_counter_set_matches_suffixed_metrics_against_query_output(monkeypatch):
    counter_set = load_counter_set(Path("configs/counters/compute_lite.yaml"))

    def fake_run(*args, **kwargs):
        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="\n".join(
                [
                    "sm__warps_active",
                    "smsp__inst_executed",
                    "smsp__inst_executed_pipe_tensor_op_hmma",
                    "smsp__pipe_tensor_op_hmma_cycles_active",
                    "smsp__warp_issue_stalled_math_pipe_throttle_per_warp_active",
                    "smsp__warp_issue_stalled_long_scoreboard_per_warp_active",
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr("kernel_tuner.profiling.compatibility.subprocess.run", fake_run)

    record = validate_counter_set(counter_set, kernel_family="gemm")

    assert record.available_counter_count == len(counter_set.counters)
    assert record.availability_fraction == 1.0
    assert record.acceptable is True
    assert record.missing_counters == []


def test_shared_diag_uses_queryable_suffix_metrics():
    counter_set = load_counter_set(Path("configs/counters/shared_diag.yaml"))

    assert counter_set.counters == [
        "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld.avg",
        "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st.avg",
        "l1tex__data_pipe_lsu_wavefronts_mem_shared.avg",
        "smsp__warp_issue_stalled_short_scoreboard_per_warp_active.pct",
    ]


def test_default_calibration_uses_queryable_suffix_metrics():
    counter_set = load_counter_set(Path("configs/counters/default_calibration.yaml"))

    assert counter_set.counters == [
        "smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct",
        "sm__warps_active.avg.pct_of_peak_sustained_active",
        "smsp__inst_executed.sum",
    ]


def test_resolve_tool_path_prefers_cuda_home_bin(tmp_path, monkeypatch):
    cuda_bin = tmp_path / "cuda" / "bin"
    cuda_bin.mkdir(parents=True)
    ncu = cuda_bin / "ncu"
    ncu.write_text("")
    monkeypatch.setenv("CUDA_HOME", str(tmp_path / "cuda"))
    monkeypatch.setattr("kernel_tuner.common.provenance.which", lambda name: None)

    assert resolve_tool_path("ncu") == str(ncu)


def test_validate_counter_set_records_missing_metrics_in_notes(monkeypatch):
    counter_set = load_counter_set(Path("configs/counters/compute_lite.yaml"))

    monkeypatch.setattr(
        "kernel_tuner.profiling.compatibility.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="\n".join(
                [
                    "sm__warps_active",
                    "smsp__inst_executed",
                ]
            ),
            stderr="",
        ),
    )

    record = validate_counter_set(counter_set, kernel_family="gemm")

    assert record.acceptable is False
    assert record.validation_backend == "ncu_query_metrics"
    assert "missing or unsupported queried metrics" in (record.notes or "")
    assert "smsp__inst_executed_pipe_tensor_op_hmma.avg" in (record.notes or "")
