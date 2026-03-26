from kernel_tuner.common.schema import (
    CandidateConfig,
    CompileSignalRecord,
    ComparisonClass,
    MeasurementPhase,
    ProfileMeasurement,
    ProfileStatus,
    RuntimeMeasurement,
    RuntimeStatus,
    SelectorRankingFeature,
    SelectorRevisionSpec,
)
from kernel_tuner.selector.engine import _select_with_tolerance, run_selector_mode


def test_select_with_tolerance_prefers_ranked_order_within_band():
    runtime_scores = {
        "cfg_late_best": 1.00,
        "cfg_early_near_best": 1.015,
        "cfg_far": 1.20,
    }
    ranked_order = ["cfg_early_near_best", "cfg_late_best", "cfg_far"]

    selected = _select_with_tolerance(runtime_scores, ranked_order, relative_tolerance=0.02)

    assert selected == "cfg_early_near_best"


def test_select_with_tolerance_uses_best_when_gap_exceeds_band():
    runtime_scores = {
        "cfg_early": 1.05,
        "cfg_best": 1.00,
    }
    ranked_order = ["cfg_early", "cfg_best"]

    selected = _select_with_tolerance(runtime_scores, ranked_order, relative_tolerance=0.02)

    assert selected == "cfg_best"


def test_revised_selector_can_rerank_compile_frontier_with_config_features():
    candidates = [
        CandidateConfig(
            experiment_id="exp",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_small",
            config={"block_m": 64, "block_n": 64, "block_k": 32, "num_stages": 4, "num_warps": 8},
            is_valid=True,
        ),
        CandidateConfig(
            experiment_id="exp",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_mid",
            config={"block_m": 128, "block_n": 64, "block_k": 32, "num_stages": 4, "num_warps": 8},
            is_valid=True,
        ),
        CandidateConfig(
            experiment_id="exp",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_large_square",
            config={"block_m": 128, "block_n": 128, "block_k": 32, "num_stages": 4, "num_warps": 4},
            is_valid=True,
        ),
    ]
    compile_signals = [
        CompileSignalRecord(
            run_id="run",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_small",
            compile_status="success",
            compile_success=True,
            register_count=55,
            shared_memory_bytes=8192,
            occupancy_estimate=1.0,
        ),
        CompileSignalRecord(
            run_id="run",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_mid",
            compile_status="success",
            compile_success=True,
            register_count=96,
            shared_memory_bytes=12288,
            occupancy_estimate=1.0,
        ),
        CompileSignalRecord(
            run_id="run",
            kernel_id="gemm",
            shape_id="shape_1",
            config_id="cfg_large_square",
            compile_status="success",
            compile_success=True,
            register_count=223,
            shared_memory_bytes=16384,
            occupancy_estimate=1.0,
        ),
    ]
    revision = SelectorRevisionSpec(
        revision_id="frontier_test",
        frontier_ranking_features=[
            SelectorRankingFeature(feature_name="shape_balance", source="config", direction="desc"),
            SelectorRankingFeature(feature_name="tile_area", source="config", direction="desc"),
            SelectorRankingFeature(feature_name="num_stages", source="config", direction="desc"),
            SelectorRankingFeature(feature_name="num_warps", source="config", direction="asc"),
        ],
        ranking_features=[
            SelectorRankingFeature(feature_name="warps_active", source="profile", direction="desc"),
            SelectorRankingFeature(
                feature_name="long_scoreboard_stall",
                source="profile",
                direction="asc",
            ),
        ],
    )

    def request_profile(config_id: str) -> list[ProfileMeasurement]:
        return [
            ProfileMeasurement(
                run_id="run",
                strategy_id="prune_rank_revised",
                kernel_id="gemm",
                shape_id="shape_1",
                config_id=config_id,
                counter_set_id="compute_lite",
                profile_status=ProfileStatus.SUCCESS,
                counter_map={
                    "sm__warps_active.avg.pct_of_peak_sustained_active": 60.0,
                    "smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct": 10.0,
                },
            )
        ]

    latencies = {
        "cfg_small": 90.0,
        "cfg_mid": 80.0,
        "cfg_large_square": 60.0,
    }

    def request_benchmark(config_id: str) -> list[RuntimeMeasurement]:
        latency = latencies[config_id]
        return [
            RuntimeMeasurement(
                run_id="run",
                strategy_id="prune_rank_revised",
                measurement_phase=MeasurementPhase.CALIBRATION,
                kernel_id="gemm",
                shape_id="shape_1",
                config_id=config_id,
                warmup_count=1,
                timed_run_count=1,
                latency_median_us=latency,
                latency_mean_us=latency,
                latency_std_us=0.0,
                latency_p95_us=latency,
                throughput_value=1.0,
                throughput_unit="arb",
                status=RuntimeStatus.SUCCESS,
            )
        ]

    decision = run_selector_mode(
        run_id="run",
        strategy_id="prune_rank_revised",
        selector_mode="prune_rank_revised",
        kernel_id="gemm",
        candidate_records=candidates,
        compile_signals=compile_signals,
        budgets=type("Budget", (), {"max_profiles": 1, "max_benchmarks": 1})(),
        request_benchmark=request_benchmark,
        request_profile=request_profile,
        selector_revision=revision,
    )

    assert decision.comparison_class == ComparisonClass.MATCHED_BUDGET
    assert decision.ranked_config_ids[0] == "cfg_large_square"
    assert decision.selected_config_id == "cfg_large_square"
