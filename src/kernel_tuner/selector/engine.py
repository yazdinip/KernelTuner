"""Selector engine."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from kernel_tuner.benchmark.harness import benchmark_candidate
from kernel_tuner.common.config import (
    counter_set_path,
    kernel_config_path,
    load_counter_set,
    load_kernel_spec,
    load_selector_revision_spec,
    selector_revision_path,
)
from kernel_tuner.common.schema import (
    CandidateConfig,
    ComparisonClass,
    CompileSignalRecord,
    ExperimentSpec,
    MeasurementPhase,
    ProfileMeasurement,
    ProfileStatus,
    RuntimeMeasurement,
    RuntimeStatus,
    SelectionDecision,
    SelectorRevisionSpec,
    SelectorMode,
)
from kernel_tuner.config_space.generator import generate_candidate_records
from kernel_tuner.kernels.registry import resolve_kernel
from kernel_tuner.profiling.adapter import profile_candidate
from kernel_tuner.signals.collector import collect_compile_signals

BenchmarkRequest = Callable[[str], list[RuntimeMeasurement]]
ProfileRequest = Callable[[str], list[ProfileMeasurement]]


def _mode_name(value: str | SelectorMode) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _group_candidates(candidates: Iterable[CandidateConfig]) -> dict[str, list[CandidateConfig]]:
    grouped: dict[str, list[CandidateConfig]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.config_id].append(candidate)
    return dict(grouped)


def _aggregate_compile_signals(
    signal_records: Iterable[CompileSignalRecord],
) -> dict[str, dict[str, float | int | bool | None]]:
    grouped: dict[str, list[CompileSignalRecord]] = defaultdict(list)
    for record in signal_records:
        grouped[record.config_id].append(record)

    aggregated: dict[str, dict[str, float | int | bool | None]] = {}
    for config_id, records in grouped.items():
        occupancies = [record.occupancy_estimate for record in records if record.occupancy_estimate is not None]
        register_counts = [record.register_count for record in records if record.register_count is not None]
        shared_memory = [record.shared_memory_bytes for record in records if record.shared_memory_bytes is not None]
        aggregated[config_id] = {
            "compile_success": all(record.compile_success for record in records),
            "occupancy_estimate": (sum(occupancies) / len(occupancies)) if occupancies else None,
            "register_count": (sum(register_counts) / len(register_counts)) if register_counts else None,
            "shared_memory_bytes": max(shared_memory) if shared_memory else None,
        }
    return aggregated


def _compile_rank_key(config_id: str, aggregate: dict[str, float | int | bool | None]) -> tuple[object, ...]:
    return (
        0 if aggregate.get("compile_success") else 1,
        -(aggregate.get("occupancy_estimate") or -1.0),
        aggregate.get("register_count") if aggregate.get("register_count") is not None else float("inf"),
        aggregate.get("shared_memory_bytes")
        if aggregate.get("shared_memory_bytes") is not None
        else float("inf"),
        config_id,
    )


def _prune_candidates(
    candidate_groups: dict[str, list[CandidateConfig]],
    signal_summary: dict[str, dict[str, float | int | bool | None]],
) -> tuple[list[str], list[str], dict[str, str]]:
    remaining: list[str] = []
    pruned: list[str] = []
    reasons: dict[str, str] = {}
    for config_id in sorted(candidate_groups):
        candidates = candidate_groups[config_id]
        aggregate = signal_summary.get(config_id, {})
        if any(not candidate.is_valid for candidate in candidates):
            pruned.append(config_id)
            reasons[config_id] = "invalid_config"
            continue
        if not aggregate.get("compile_success", False):
            pruned.append(config_id)
            reasons[config_id] = "compile_failed"
            continue
        shared_memory = aggregate.get("shared_memory_bytes")
        if isinstance(shared_memory, (int, float)) and shared_memory > 100_000:
            pruned.append(config_id)
            reasons[config_id] = "shared_memory_limit"
            continue
        occupancy = aggregate.get("occupancy_estimate")
        if isinstance(occupancy, (int, float)) and occupancy < 0.2:
            pruned.append(config_id)
            reasons[config_id] = "poor_occupancy"
            continue
        remaining.append(config_id)
    ranked = sorted(remaining, key=lambda config_id: _compile_rank_key(config_id, signal_summary[config_id]))
    return ranked, pruned, reasons


def aggregate_runtime_scores(
    runtime_records: Iterable[RuntimeMeasurement],
) -> dict[str, float]:
    success_records = [record for record in runtime_records if record.status == RuntimeStatus.SUCCESS]
    by_shape: dict[str, dict[str, float]] = defaultdict(dict)
    for record in success_records:
        if record.latency_median_us is None:
            continue
        by_shape[record.shape_id][record.config_id] = record.latency_median_us

    shape_best = {
        shape_id: min(configs.values())
        for shape_id, configs in by_shape.items()
        if configs
    }
    scores: dict[str, float] = {}
    config_ids = {record.config_id for record in success_records}
    for config_id in config_ids:
        ratios: list[float] = []
        for shape_id, best_latency in shape_best.items():
            if config_id not in by_shape[shape_id]:
                ratios = []
                break
            ratios.append(by_shape[shape_id][config_id] / best_latency)
        if ratios:
            scores[config_id] = sum(ratios) / len(ratios)
    return scores


def _select_with_tolerance(
    runtime_scores: dict[str, float],
    preference_order: list[str],
    *,
    relative_tolerance: float = 0.02,
) -> str | None:
    if not runtime_scores:
        return None
    best_score = min(runtime_scores.values())
    allowed = {
        config_id
        for config_id, score in runtime_scores.items()
        if score <= best_score * (1.0 + relative_tolerance)
    }
    for config_id in preference_order:
        if config_id in allowed:
            return config_id
    return min(runtime_scores, key=lambda config_id: (runtime_scores[config_id], config_id))


def _counter_value(counter_map: dict[str, float | None], *names: str) -> float | None:
    for name in names:
        value = counter_map.get(name)
        if value is not None:
            return value
    return None


def _aggregate_profile_metrics(
    profile_records: Iterable[ProfileMeasurement],
) -> dict[str, dict[str, float | None]]:
    grouped: dict[str, list[ProfileMeasurement]] = defaultdict(list)
    for record in profile_records:
        grouped[record.config_id].append(record)

    metrics: dict[str, dict[str, float | None]] = {}
    for config_id, records in grouped.items():
        usable = [
            record
            for record in records
            if record.profile_status in {ProfileStatus.SUCCESS, ProfileStatus.UNSUPPORTED_COUNTER}
        ]
        if not usable:
            metrics[config_id] = {
                "warps_active": None,
                "long_scoreboard_stall": None,
                "tensor_ops": None,
                "dram_throughput": None,
                "lg_throttle": None,
                "shared_conflicts": None,
            }
            continue
        warps = [
            _counter_value(record.counter_map, "sm__warps_active.avg.pct_of_peak_sustained_active")
            for record in usable
            if _counter_value(record.counter_map, "sm__warps_active.avg.pct_of_peak_sustained_active") is not None
        ]
        stalls = [
            _counter_value(
                record.counter_map,
                "smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct",
                "smsp__warp_issue_stalled_long_scoreboard_per_warp_active",
                "smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.avg",
            )
            for record in usable
            if _counter_value(
                record.counter_map,
                "smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct",
                "smsp__warp_issue_stalled_long_scoreboard_per_warp_active",
                "smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.avg",
            )
            is not None
        ]
        tensor_ops = [
            _counter_value(
                record.counter_map,
                "smsp__inst_executed_pipe_tensor_op_hmma.avg",
                "smsp__inst_executed_pipe_tensor_op_hmma",
            )
            for record in usable
            if _counter_value(
                record.counter_map,
                "smsp__inst_executed_pipe_tensor_op_hmma.avg",
                "smsp__inst_executed_pipe_tensor_op_hmma",
            )
            is not None
        ]
        dram_throughput = [
            _counter_value(
                record.counter_map,
                "dram__throughput.avg.pct_of_peak_sustained_elapsed",
                "dram__throughput",
            )
            for record in usable
            if _counter_value(
                record.counter_map,
                "dram__throughput.avg.pct_of_peak_sustained_elapsed",
                "dram__throughput",
            )
            is not None
        ]
        lg_throttle = [
            _counter_value(
                record.counter_map,
                "smsp__warp_issue_stalled_lg_throttle_per_warp_active.pct",
                "smsp__warp_issue_stalled_lg_throttle_per_warp_active",
            )
            for record in usable
            if _counter_value(
                record.counter_map,
                "smsp__warp_issue_stalled_lg_throttle_per_warp_active.pct",
                "smsp__warp_issue_stalled_lg_throttle_per_warp_active",
            )
            is not None
        ]
        shared_conflicts = [
            sum(
                value
                for value in [
                    _counter_value(record.counter_map, "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld"),
                    _counter_value(record.counter_map, "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st"),
                ]
                if value is not None
            )
            for record in usable
            if _counter_value(
                record.counter_map,
                "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld",
                "l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st",
            )
            is not None
        ]
        metrics[config_id] = {
            "warps_active": (sum(warps) / len(warps)) if warps else None,
            "long_scoreboard_stall": (sum(stalls) / len(stalls)) if stalls else None,
            "tensor_ops": (sum(tensor_ops) / len(tensor_ops)) if tensor_ops else None,
            "dram_throughput": (sum(dram_throughput) / len(dram_throughput)) if dram_throughput else None,
            "lg_throttle": (sum(lg_throttle) / len(lg_throttle)) if lg_throttle else None,
            "shared_conflicts": (sum(shared_conflicts) / len(shared_conflicts)) if shared_conflicts else None,
        }
    return metrics


def _profile_rank_key(
    config_id: str,
    profile_metrics: dict[str, dict[str, float | None]],
) -> tuple[object, ...]:
    metrics = profile_metrics.get(config_id, {})
    return (
        -(metrics.get("warps_active") or -1.0),
        metrics.get("long_scoreboard_stall")
        if metrics.get("long_scoreboard_stall") is not None
        else float("inf"),
        config_id,
    )


def _revised_profile_rank_key(
    config_id: str,
    profile_metrics: dict[str, dict[str, float | None]],
    compile_summary: dict[str, dict[str, float | int | bool | None]],
) -> tuple[object, ...]:
    profile = profile_metrics.get(config_id, {})
    compile_metrics = compile_summary.get(config_id, {})
    return (
        -(profile.get("warps_active") or -1.0),
        -(profile.get("tensor_ops") or -1.0),
        profile.get("long_scoreboard_stall")
        if profile.get("long_scoreboard_stall") is not None
        else float("inf"),
        profile.get("lg_throttle") if profile.get("lg_throttle") is not None else float("inf"),
        profile.get("shared_conflicts") if profile.get("shared_conflicts") is not None else float("inf"),
        compile_metrics.get("register_count")
        if compile_metrics.get("register_count") is not None
        else float("inf"),
        config_id,
    )


def _metric_value(
    *,
    config_id: str,
    feature_name: str,
    source: str,
    compile_summary: dict[str, dict[str, float | int | bool | None]],
    profile_metrics: dict[str, dict[str, float | None]],
) -> float | int | bool | None:
    if source == "compile":
        return compile_summary.get(config_id, {}).get(feature_name)
    if source == "profile":
        return profile_metrics.get(config_id, {}).get(feature_name)
    raise ValueError(f"unsupported selector feature source '{source}'")


def _compare_rule(value: float | int | bool | None, comparator: str, threshold: float) -> bool:
    if value is None:
        return False
    numeric = float(value)
    if comparator == "lt":
        return numeric < threshold
    if comparator == "lte":
        return numeric <= threshold
    if comparator == "gt":
        return numeric > threshold
    if comparator == "gte":
        return numeric >= threshold
    if comparator == "eq":
        return numeric == threshold
    if comparator == "ne":
        return numeric != threshold
    raise ValueError(f"unsupported prune comparator '{comparator}'")


def _revision_rank_key(
    config_id: str,
    selector_revision: SelectorRevisionSpec,
    compile_summary: dict[str, dict[str, float | int | bool | None]],
    profile_metrics: dict[str, dict[str, float | None]],
) -> tuple[object, ...]:
    key: list[object] = []
    for feature in selector_revision.ranking_features:
        value = _metric_value(
            config_id=config_id,
            feature_name=feature.feature_name,
            source=feature.source,
            compile_summary=compile_summary,
            profile_metrics=profile_metrics,
        )
        if value is None:
            fallback: float = (
                feature.missing_value
                if feature.missing_value is not None
                else (float("-inf") if feature.direction == "desc" else float("inf"))
            )
            key.append(fallback)
            continue
        numeric = float(value)
        key.append(-numeric if feature.direction == "desc" else numeric)
    key.append(config_id)
    return tuple(key)


def _apply_revision_prunes(
    config_ids: list[str],
    selector_revision: SelectorRevisionSpec,
    compile_summary: dict[str, dict[str, float | int | bool | None]],
    profile_metrics: dict[str, dict[str, float | None]],
) -> tuple[list[str], dict[str, str]]:
    surviving: list[str] = []
    reasons: dict[str, str] = {}
    for config_id in config_ids:
        pruned = False
        for rule in selector_revision.prune_rules:
            value = _metric_value(
                config_id=config_id,
                feature_name=rule.feature_name,
                source=rule.source,
                compile_summary=compile_summary,
                profile_metrics=profile_metrics,
            )
            if _compare_rule(value, rule.comparator, rule.threshold):
                reasons[config_id] = rule.prune_reason
                pruned = True
                break
        if not pruned:
            surviving.append(config_id)
    return surviving, reasons


def run_selector_mode(
    *,
    run_id: str,
    strategy_id: str,
    selector_mode: SelectorMode,
    kernel_id: str,
    candidate_records: list[CandidateConfig],
    compile_signals: list[CompileSignalRecord],
    budgets,
    request_benchmark: BenchmarkRequest,
    request_profile: ProfileRequest | None = None,
    selector_revision: SelectorRevisionSpec | None = None,
) -> SelectionDecision:
    started = time.perf_counter()
    candidate_groups = _group_candidates(candidate_records)
    compile_summary = _aggregate_compile_signals(compile_signals)
    ranked_ids, pruned_ids, prune_reasons = _prune_candidates(candidate_groups, compile_summary)
    requested_mode = _mode_name(selector_mode)
    actual_mode = requested_mode
    rationale = [f"started with {len(candidate_groups)} candidate configs", f"pruned {len(pruned_ids)} configs"]

    if not ranked_ids:
        return SelectionDecision(
            run_id=run_id,
            strategy_id=strategy_id,
            comparison_class=ComparisonClass.MATCHED_BUDGET,
            selector_mode=actual_mode,
            requested_selector_mode=requested_mode,
            kernel_id=kernel_id,
            shape_scope="calibration",
            ranked_config_ids=[],
            pruned_config_ids=pruned_ids,
            candidates_considered=len(candidate_groups),
            benchmarks_requested=0,
            profiles_requested=0,
            decision_wall_clock_s=time.perf_counter() - started,
            rationale_summary="no candidates survived pruning",
            decision_status="failed_no_candidates",
            calibration_metadata={"prune_reasons": prune_reasons},
        )

    if requested_mode == SelectorMode.PRUNE_ONLY.value:
        selected = ranked_ids[0]
        rationale.append("selected first surviving candidate in compile-rank order")
        return SelectionDecision(
            run_id=run_id,
            strategy_id=strategy_id,
            comparison_class=ComparisonClass.MATCHED_BUDGET,
            selector_mode=actual_mode,
            requested_selector_mode=requested_mode,
            kernel_id=kernel_id,
            shape_scope="calibration",
            selected_config_id=selected,
            ranked_config_ids=ranked_ids,
            pruned_config_ids=pruned_ids,
            candidates_considered=len(candidate_groups),
            benchmarks_requested=0,
            profiles_requested=0,
            decision_wall_clock_s=time.perf_counter() - started,
            rationale_summary="; ".join(rationale),
            decision_status="selected_without_benchmark",
            calibration_metadata={"prune_reasons": prune_reasons},
        )

    profiled_records: list[ProfileMeasurement] = []
    benchmark_order = list(ranked_ids)
    if requested_mode in {
        SelectorMode.PRUNE_RANK_PROFILED.value,
        SelectorMode.PRUNE_RANK_REVISED.value,
    }:
        if request_profile is None:
            actual_mode = SelectorMode.PRUNE_RANK.value
            rationale.append("downgraded to prune_rank because no profile requester was supplied")
        else:
            profiled_ids = ranked_ids[: budgets.max_profiles]
            for config_id in profiled_ids:
                profiled_records.extend(request_profile(config_id))
            profile_metrics = _aggregate_profile_metrics(profiled_records)
            successful_profile_ids = [
                config_id
                for config_id in profiled_ids
                if any(
                    record.profile_status in {ProfileStatus.SUCCESS, ProfileStatus.UNSUPPORTED_COUNTER}
                    and record.config_id == config_id
                    for record in profiled_records
                )
            ]
            if not successful_profile_ids:
                actual_mode = SelectorMode.PRUNE_RANK.value
                rationale.append("downgraded to prune_rank because no successful profile records were available")
            else:
                if requested_mode == SelectorMode.PRUNE_RANK_REVISED.value:
                    if selector_revision is None:
                        actual_mode = SelectorMode.PRUNE_RANK_PROFILED.value
                        rationale.append(
                            "downgraded to prune_rank_profiled because no selector revision was supplied"
                        )
                        reordered_profiled = sorted(
                            successful_profile_ids,
                            key=lambda config_id: _profile_rank_key(config_id, profile_metrics),
                        )
                    else:
                        surviving_profiled, revision_prunes = _apply_revision_prunes(
                            successful_profile_ids,
                            selector_revision,
                            compile_summary,
                            profile_metrics,
                        )
                        pruned_ids.extend(sorted(revision_prunes))
                        prune_reasons.update(revision_prunes)
                        if not surviving_profiled:
                            actual_mode = SelectorMode.PRUNE_RANK_PROFILED.value
                            rationale.append(
                                "downgraded to prune_rank_profiled because revision pruned all profiled configs"
                            )
                            reordered_profiled = sorted(
                                successful_profile_ids,
                                key=lambda config_id: _profile_rank_key(config_id, profile_metrics),
                            )
                        else:
                            reordered_profiled = sorted(
                                surviving_profiled,
                                key=lambda config_id: _revision_rank_key(
                                    config_id,
                                    selector_revision,
                                    compile_summary,
                                    profile_metrics,
                                ),
                            )
                            rationale.append(
                                f"profile-reordered {len(reordered_profiled)} configs using revision '{selector_revision.revision_id}'"
                            )
                else:
                    reordered_profiled = sorted(
                        successful_profile_ids,
                        key=lambda config_id: _profile_rank_key(config_id, profile_metrics),
                    )
                    rationale.append(
                        f"profile-reordered {len(reordered_profiled)} configs using warps_active and long_scoreboard"
                    )
                remainder = [config_id for config_id in ranked_ids if config_id not in reordered_profiled]
                benchmark_order = reordered_profiled + remainder

    benchmark_ids = benchmark_order[: budgets.max_benchmarks]
    runtime_records: list[RuntimeMeasurement] = []
    for config_id in benchmark_ids:
        runtime_records.extend(request_benchmark(config_id))

    runtime_scores = aggregate_runtime_scores(runtime_records)
    selected = _select_with_tolerance(runtime_scores, benchmark_order)
    budget_limited = any(
        record.status == RuntimeStatus.SKIPPED_BUDGET for record in runtime_records
    ) or any(record.profile_status == ProfileStatus.SKIPPED_BUDGET for record in profiled_records)
    if selected is None:
        decision_status = "failed_no_successful_measurements"
        rationale.append("no successful calibration measurements were available")
    else:
        decision_status = "selected_budget_limited" if budget_limited else "selected"
        rationale.append(
            f"benchmarked {len(benchmark_ids)} configs and selected the best score within a 2% tie band"
        )

    return SelectionDecision(
        run_id=run_id,
        strategy_id=strategy_id,
        comparison_class=ComparisonClass.MATCHED_BUDGET,
        selector_mode=actual_mode,
        requested_selector_mode=requested_mode,
        kernel_id=kernel_id,
        shape_scope="calibration",
        selected_config_id=selected,
        ranked_config_ids=benchmark_order,
        pruned_config_ids=pruned_ids,
        candidates_considered=len(candidate_groups),
        benchmarks_requested=len(benchmark_ids),
        profiles_requested=len(
            {record.config_id for record in profiled_records if record.profile_status != ProfileStatus.SKIPPED_BUDGET}
        ),
        decision_wall_clock_s=time.perf_counter() - started,
        rationale_summary="; ".join(rationale),
        decision_status=decision_status,
        score_map=runtime_scores,
        calibration_metadata={"prune_reasons": prune_reasons},
    )


def select_for_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    from kernel_tuner.experiments.orchestrator import _profile_shapes, _shape_split

    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
    kernel = resolve_kernel(kernel_spec)
    calibration_shapes, _ = _shape_split(experiment_spec)
    calibration_shape_ids = {shape.shape_id for shape in calibration_shapes}
    profile_shapes = _profile_shapes(experiment_spec, calibration_shapes)
    candidate_records = [
        candidate
        for candidate in generate_candidate_records(experiment_spec, experiment_path=experiment_path)
        if candidate.shape_id in calibration_shape_ids
    ]
    compile_signals = []
    for index, shape in enumerate(calibration_shapes):
        shape_candidates = [
            candidate
            for candidate in candidate_records
            if candidate.shape_id == shape.shape_id
        ]
        compile_signals.extend(
            collect_compile_signals(
                run_id="standalone",
                kernel=kernel,
                shape=shape,
                candidates=shape_candidates,
                seed=experiment_spec.seed + index,
            )
        )
    benchmark_cache: dict[str, list[RuntimeMeasurement]] = {}
    profile_cache: dict[str, list[ProfileMeasurement]] = {}

    def request_benchmark(config_id: str) -> list[RuntimeMeasurement]:
        if config_id not in benchmark_cache:
            measurements: list[RuntimeMeasurement] = []
            for index, shape in enumerate(calibration_shapes):
                candidate = next(
                    candidate
                    for candidate in candidate_records
                    if candidate.config_id == config_id and candidate.shape_id == shape.shape_id
                )
                measurements.append(
                    benchmark_candidate(
                        run_id="standalone",
                        strategy_id=_mode_name(experiment_spec.selector_modes[0]),
                        kernel=kernel,
                        shape=shape,
                        candidate=candidate,
                        settings=experiment_spec.benchmark_settings,
                        seed=experiment_spec.seed + index,
                        measurement_phase=MeasurementPhase.CALIBRATION,
                        measurement_order_index=index,
                    ).measurement
                )
            benchmark_cache[config_id] = measurements
        return benchmark_cache[config_id]

    def request_profile(config_id: str) -> list[ProfileMeasurement]:
        if config_id not in profile_cache:
            if not experiment_spec.counter_set_id:
                return []
            counter_set = load_counter_set(counter_set_path(experiment_spec.counter_set_id, experiment_path))
            measurements: list[ProfileMeasurement] = []
            for shape in profile_shapes:
                candidate = next(
                    candidate
                    for candidate in candidate_records
                    if candidate.config_id == config_id and candidate.shape_id == shape.shape_id
                )
                measurements.append(
                    profile_candidate(
                        run_id="standalone",
                        strategy_id=_mode_name(experiment_spec.selector_modes[0]),
                        kernel_id=kernel_spec.kernel_id,
                        shape=shape,
                        candidate=candidate,
                        counter_set=counter_set,
                        experiment_spec=experiment_spec,
                        experiment_path=experiment_path,
                    ).measurement
                )
            profile_cache[config_id] = measurements
        return profile_cache[config_id]

    selector_revision = None
    if experiment_spec.selector_revision_id:
        selector_revision = load_selector_revision_spec(
            selector_revision_path(experiment_spec.selector_revision_id, experiment_path)
        )

    decision = run_selector_mode(
        run_id="standalone",
        strategy_id=_mode_name(experiment_spec.selector_modes[0]),
        selector_mode=experiment_spec.selector_modes[0],
        kernel_id=kernel_spec.kernel_id,
        candidate_records=candidate_records,
        compile_signals=compile_signals,
        budgets=experiment_spec.budgets,
        request_benchmark=request_benchmark,
        request_profile=request_profile if experiment_spec.counter_set_id else None,
        selector_revision=selector_revision,
    )
    return decision.model_dump(mode="json")
