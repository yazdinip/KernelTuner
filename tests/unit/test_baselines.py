from types import SimpleNamespace

from kernel_tuner.baselines.strategies import run_baseline_mode
from kernel_tuner.common.schema import (
    BaselineMode,
    CandidateConfig,
    ComparisonClass,
    MeasurementPhase,
    RuntimeMeasurement,
    RuntimeStatus,
)


def _candidate(config_id: str, shape_id: str = "gemm_m128_n128_k128_fp16_rowmajor") -> CandidateConfig:
    return CandidateConfig(
        experiment_id="exp",
        kernel_id="gemm",
        shape_id=shape_id,
        config_id=config_id,
        config={"block_m": 64, "block_n": 64, "block_k": 32, "num_warps": 4, "num_stages": 2},
        is_valid=True,
    )


def _measurement(config_id: str, status: RuntimeStatus, latency: float | None) -> RuntimeMeasurement:
    return RuntimeMeasurement(
        run_id="run_001",
        strategy_id="baseline",
        measurement_phase=MeasurementPhase.CALIBRATION,
        kernel_id="gemm",
        shape_id="gemm_m128_n128_k128_fp16_rowmajor",
        config_id=config_id,
        warmup_count=1,
        timed_run_count=1,
        latency_median_us=latency,
        latency_mean_us=latency,
        latency_std_us=0.0 if latency is not None else None,
        latency_p95_us=latency,
        throughput_value=None,
        throughput_unit=None,
        status=status,
        timing_backend="cuda_events",
    )


def test_run_baseline_mode_marks_budget_limited_without_name_error():
    candidates = [_candidate("cfg_a"), _candidate("cfg_b")]
    budgets = SimpleNamespace(max_benchmarks=2)

    def request_benchmark(config_id: str):
        if config_id == "cfg_a":
            return [_measurement(config_id, RuntimeStatus.SUCCESS, 10.0)]
        return [_measurement(config_id, RuntimeStatus.SKIPPED_BUDGET, None)]

    decision = run_baseline_mode(
        run_id="run_001",
        strategy_id="naive_grid_search",
        baseline_mode=BaselineMode.NAIVE_GRID_SEARCH,
        kernel_id="gemm",
        candidate_records=candidates,
        budgets=budgets,
        seed=7,
        default_config=None,
        request_benchmark=request_benchmark,
    )

    assert decision.comparison_class == ComparisonClass.MATCHED_BUDGET
    assert decision.selected_config_id == "cfg_a"
    assert decision.decision_status == "selected_budget_limited"
