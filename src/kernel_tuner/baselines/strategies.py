"""Baseline strategies."""

from __future__ import annotations

import random
import time
from collections import defaultdict
from typing import Callable, Iterable

from kernel_tuner.common.schema import (
    BaselineMode,
    CandidateConfig,
    ComparisonClass,
    RuntimeMeasurement,
    SelectionDecision,
)
from kernel_tuner.config_space.generator import config_dict_from_record
from kernel_tuner.selector.engine import aggregate_runtime_scores

BenchmarkRequest = Callable[[str], list[RuntimeMeasurement]]


def _mode_name(value: str | BaselineMode) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _group_candidates(candidates: Iterable[CandidateConfig]) -> dict[str, list[CandidateConfig]]:
    grouped: dict[str, list[CandidateConfig]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.config_id].append(candidate)
    return dict(grouped)


def run_baseline_mode(
    *,
    run_id: str,
    strategy_id: str,
    baseline_mode: BaselineMode,
    kernel_id: str,
    candidate_records: list[CandidateConfig],
    budgets,
    seed: int,
    default_config: dict[str, int] | None,
    request_benchmark: BenchmarkRequest,
) -> SelectionDecision:
    started = time.perf_counter()
    candidate_groups = _group_candidates(candidate_records)
    ordered_ids = sorted(candidate_groups)
    mode_name = _mode_name(baseline_mode)
    rationale = [f"baseline mode {mode_name}", f"candidate pool size {len(ordered_ids)}"]

    if not ordered_ids:
        return SelectionDecision(
            run_id=run_id,
            strategy_id=strategy_id,
            comparison_class=ComparisonClass.MATCHED_BUDGET,
            selector_mode=mode_name,
            kernel_id=kernel_id,
            shape_scope="calibration",
            ranked_config_ids=[],
            pruned_config_ids=[],
            candidates_considered=0,
            benchmarks_requested=0,
            profiles_requested=0,
            decision_wall_clock_s=time.perf_counter() - started,
            rationale_summary="empty candidate pool",
            decision_status="failed_no_candidates",
        )

    benchmark_ids: list[str]
    if mode_name == BaselineMode.DEFAULT_CONFIG.value:
        if default_config is None:
            return SelectionDecision(
                run_id=run_id,
                strategy_id=strategy_id,
                comparison_class=ComparisonClass.MATCHED_BUDGET,
                selector_mode=mode_name,
                kernel_id=kernel_id,
                shape_scope="calibration",
                ranked_config_ids=[],
                pruned_config_ids=[],
                candidates_considered=len(ordered_ids),
                benchmarks_requested=0,
                profiles_requested=0,
                decision_wall_clock_s=time.perf_counter() - started,
                rationale_summary="kernel spec did not provide a default config",
                decision_status="failed_missing_default_config",
            )
        default_id = next(
            (
                config_id
                for config_id, records in candidate_groups.items()
                if config_dict_from_record(records[0]) == default_config
            ),
            None,
        )
        if default_id is None:
            return SelectionDecision(
                run_id=run_id,
                strategy_id=strategy_id,
                comparison_class=ComparisonClass.MATCHED_BUDGET,
                selector_mode=mode_name,
                kernel_id=kernel_id,
                shape_scope="calibration",
                ranked_config_ids=[],
                pruned_config_ids=[],
                candidates_considered=len(ordered_ids),
                benchmarks_requested=0,
                profiles_requested=0,
                decision_wall_clock_s=time.perf_counter() - started,
                rationale_summary="default config not present in candidate pool",
                decision_status="failed_missing_default_candidate",
            )
        benchmark_ids = [default_id]
        rationale.append("benchmarked only the declared default config")
    elif mode_name == BaselineMode.NAIVE_RANDOM_SEARCH.value:
        rng = random.Random(seed)
        benchmark_ids = ordered_ids[:]
        rng.shuffle(benchmark_ids)
        benchmark_ids = benchmark_ids[: budgets.max_benchmarks]
        rationale.append("sampled a seeded random candidate order")
    elif mode_name == BaselineMode.NAIVE_GRID_SEARCH.value:
        benchmark_ids = ordered_ids[: budgets.max_benchmarks]
        rationale.append("evaluated the first configs in canonical order")
    else:
        return SelectionDecision(
            run_id=run_id,
            strategy_id=strategy_id,
            comparison_class=ComparisonClass.ORACLE_ONLY,
            selector_mode=mode_name,
            kernel_id=kernel_id,
            shape_scope="calibration",
            ranked_config_ids=[],
            pruned_config_ids=[],
            candidates_considered=len(ordered_ids),
            benchmarks_requested=0,
            profiles_requested=0,
            decision_wall_clock_s=time.perf_counter() - started,
            rationale_summary="small-space oracle is not implemented in v1",
            decision_status="unsupported_baseline",
        )

    runtime_records: list[RuntimeMeasurement] = []
    for config_id in benchmark_ids:
        runtime_records.extend(request_benchmark(config_id))
    runtime_scores = aggregate_runtime_scores(runtime_records)
    selected = min(runtime_scores, key=lambda config_id: (runtime_scores[config_id], config_id)) if runtime_scores else None
    budget_limited = any(record.status == RuntimeStatus.SKIPPED_BUDGET for record in runtime_records)
    if selected is None:
        decision_status = "failed_no_successful_measurements"
    else:
        decision_status = "selected_budget_limited" if budget_limited else "selected"
    return SelectionDecision(
        run_id=run_id,
        strategy_id=strategy_id,
        comparison_class=ComparisonClass.MATCHED_BUDGET
        if mode_name != BaselineMode.SMALL_SPACE_ORACLE.value
        else ComparisonClass.ORACLE_ONLY,
        selector_mode=mode_name,
        kernel_id=kernel_id,
        shape_scope="calibration",
        selected_config_id=selected,
        ranked_config_ids=benchmark_ids,
        pruned_config_ids=[],
        candidates_considered=len(ordered_ids),
        benchmarks_requested=len(benchmark_ids),
        profiles_requested=0,
        decision_wall_clock_s=time.perf_counter() - started,
        rationale_summary="; ".join(rationale),
        decision_status=decision_status,
        score_map=runtime_scores,
    )
