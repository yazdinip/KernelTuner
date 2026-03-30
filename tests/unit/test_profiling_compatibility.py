from pathlib import Path
from subprocess import CompletedProcess

from kernel_tuner.common.config import load_counter_set
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
