"""Counter availability and opportunity-mining helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from kernel_tuner.common.schema import BottleneckSignatureRecord, CounterAvailabilityRecord, ExperimentSpec, ProfileStatus


def _quantile_bucket(series: pd.Series, value: float | None) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return "unknown"
    low = numeric.quantile(0.33)
    high = numeric.quantile(0.66)
    if value <= low:
        return "low"
    if value >= high:
        return "high"
    return "medium"


def build_counter_availability_records(
    *,
    run_id: str,
    profile_measurements: pd.DataFrame,
    requested_counters: list[str],
    minimum_availability: float,
) -> list[CounterAvailabilityRecord]:
    if profile_measurements.empty or not requested_counters:
        return []

    usable = profile_measurements[
        profile_measurements["profile_status"].isin(
            [ProfileStatus.SUCCESS, ProfileStatus.UNSUPPORTED_COUNTER]
        )
    ].copy()
    if usable.empty:
        return []

    records: list[CounterAvailabilityRecord] = []
    for strategy_id, group in usable.groupby("strategy_id", dropna=False):
        total_rows = len(group)
        for counter_name in requested_counters:
            populated_rows = sum(
                isinstance(counter_map, dict) and counter_map.get(counter_name) is not None
                for counter_map in group["counter_map"]
            )
            fraction = populated_rows / total_rows if total_rows else 0.0
            counter_set_id = (
                str(group["counter_set_id"].iloc[0])
                if "counter_set_id" in group.columns and not group.empty
                else "unknown"
            )
            records.append(
                CounterAvailabilityRecord(
                    run_id=run_id,
                    strategy_id=str(strategy_id),
                    counter_set_id=counter_set_id,
                    counter_name=counter_name,
                    populated_rows=populated_rows,
                    total_rows=total_rows,
                    non_null_fraction=fraction,
                    acceptable=fraction >= minimum_availability,
                )
            )
    return records


def build_bottleneck_signatures(
    *,
    run_id: str,
    experiment_spec: ExperimentSpec,
    compile_signals: pd.DataFrame,
    runtime_measurements: pd.DataFrame,
    profile_measurements: pd.DataFrame,
    selection_decisions: pd.DataFrame,
) -> list[BottleneckSignatureRecord]:
    if compile_signals.empty or selection_decisions.empty:
        return []

    shape_metadata = {
        shape.shape_id: {
            "workload_class": shape.workload_class,
        }
        for shape in experiment_spec.shapes
    }
    strategies = selection_decisions["strategy_id"].dropna().tolist()
    compile_base = compile_signals.copy()
    compile_base["key"] = 1
    strategy_frame = pd.DataFrame({"strategy_id": strategies, "key": 1})
    expanded = compile_base.merge(strategy_frame, on="key", how="outer").drop(columns=["key"])

    selection_map = selection_decisions.set_index("strategy_id").to_dict(orient="index")
    calibration = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "calibration")
        & (runtime_measurements["status"] == "success")
    ].copy()
    calibration_mean = (
        calibration.groupby(["strategy_id", "shape_id", "config_id"], dropna=False)["latency_median_us"]
        .mean()
        .rename("calibration_latency_us")
        .reset_index()
    )
    best_calibration = (
        calibration.groupby("shape_id", dropna=False)["latency_median_us"].min().rename("best_calibration_us")
    )
    held_out = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "held_out")
        & (runtime_measurements["status"] == "success")
    ].copy()
    held_out_mean = (
        held_out.groupby(["strategy_id", "shape_id", "config_id"], dropna=False)["latency_median_us"]
        .mean()
        .rename("held_out_latency_us")
        .reset_index()
    )
    best_held_out = held_out.groupby("shape_id", dropna=False)["latency_median_us"].min().rename("best_held_out_us")

    profile_rows: list[dict[str, Any]] = []
    if not profile_measurements.empty:
        for record in profile_measurements.to_dict(orient="records"):
            counter_map = record.get("counter_map") or {}
            profile_rows.append(
                {
                    "strategy_id": record["strategy_id"],
                    "config_id": record["config_id"],
                    "counter_set_id": record["counter_set_id"],
                    "warps_active": counter_map.get("sm__warps_active.avg.pct_of_peak_sustained_active"),
                    "tensor_ops": counter_map.get("smsp__inst_executed_pipe_tensor_op_hmma.avg")
                    or counter_map.get("smsp__inst_executed_pipe_tensor_op_hmma"),
                    "tensor_active_cycles": counter_map.get("smsp__pipe_tensor_op_hmma_cycles_active.avg")
                    or counter_map.get("smsp__pipe_tensor_op_hmma_cycles_active"),
                    "dram_throughput": counter_map.get("dram__throughput.avg.pct_of_peak_sustained_elapsed")
                    or counter_map.get("dram__throughput"),
                    "dram_bytes": counter_map.get("dram__bytes.avg") or counter_map.get("dram__bytes"),
                    "cache_hit_rate": counter_map.get("l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate.pct")
                    or counter_map.get("l1tex__t_sector_pipe_lsu_mem_global_op_ld_hit_rate"),
                    "lg_throttle": counter_map.get("smsp__warp_issue_stalled_lg_throttle_per_warp_active.pct")
                    or counter_map.get("smsp__warp_issue_stalled_lg_throttle_per_warp_active"),
                    "long_scoreboard": counter_map.get("smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct")
                    or counter_map.get("smsp__warp_issue_stalled_long_scoreboard_per_warp_active"),
                    "math_pipe_throttle": counter_map.get("smsp__warp_issue_stalled_math_pipe_throttle_per_warp_active.pct")
                    or counter_map.get("smsp__warp_issue_stalled_math_pipe_throttle_per_warp_active"),
                    "shared_conflict_ld": counter_map.get("l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_ld"),
                    "shared_conflict_st": counter_map.get("l1tex__data_bank_conflicts_pipe_lsu_mem_shared_op_st"),
                    "shared_wavefronts": counter_map.get("l1tex__data_pipe_lsu_wavefronts_mem_shared"),
                }
            )
    profile_frame = pd.DataFrame(profile_rows)
    if not profile_frame.empty:
        profile_frame = (
            profile_frame.groupby(["strategy_id", "config_id"], dropna=False)
            .mean(numeric_only=True)
            .reset_index()
        )

    merged = expanded.merge(calibration_mean, on=["strategy_id", "shape_id", "config_id"], how="left")
    merged = merged.merge(held_out_mean, on=["strategy_id", "shape_id", "config_id"], how="left")
    merged = merged.merge(best_calibration.reset_index(), on="shape_id", how="left")
    merged = merged.merge(best_held_out.reset_index(), on="shape_id", how="left")
    if not profile_frame.empty:
        merged = merged.merge(profile_frame, on=["strategy_id", "config_id"], how="left")

    merged["workload_class"] = merged["shape_id"].map(
        lambda shape_id: shape_metadata.get(shape_id, {}).get("workload_class")
    )
    merged["selected_by_strategy"] = merged.apply(
        lambda row: selection_map.get(row["strategy_id"], {}).get("selected_config_id") == row["config_id"],
        axis=1,
    )
    merged["regret_to_best_measured"] = merged.apply(
        lambda row: (
            (row["calibration_latency_us"] / row["best_calibration_us"]) - 1.0
            if pd.notna(row.get("calibration_latency_us")) and pd.notna(row.get("best_calibration_us"))
            else None
        ),
        axis=1,
    )
    merged["held_out_outcome"] = merged.apply(
        lambda row: _held_out_outcome(row),
        axis=1,
    )

    merged["occupancy_bucket"] = merged["occupancy_estimate"].apply(
        lambda value: _quantile_bucket(merged["occupancy_estimate"], value)
    )
    tensor_signal = merged["tensor_active_cycles"] if "tensor_active_cycles" in merged.columns else pd.Series(dtype=float)
    merged["tensor_util_bucket"] = merged.apply(
        lambda row: _quantile_bucket(tensor_signal, row.get("tensor_active_cycles")),
        axis=1,
    )
    memory_signal = merged["dram_throughput"] if "dram_throughput" in merged.columns else pd.Series(dtype=float)
    merged["memory_pressure_bucket"] = merged.apply(
        lambda row: _quantile_bucket(memory_signal, row.get("dram_throughput")),
        axis=1,
    )
    scoreboard_signal = merged["long_scoreboard"] if "long_scoreboard" in merged.columns else pd.Series(dtype=float)
    merged["scoreboard_bucket"] = merged.apply(
        lambda row: _quantile_bucket(scoreboard_signal, row.get("long_scoreboard")),
        axis=1,
    )
    shared_signal = (
        merged[["shared_conflict_ld", "shared_conflict_st"]].fillna(0).sum(axis=1)
        if {"shared_conflict_ld", "shared_conflict_st"} <= set(merged.columns)
        else pd.Series(dtype=float)
    )
    merged["shared_conflict_total"] = shared_signal
    merged["shared_conflict_bucket"] = merged.apply(
        lambda row: _quantile_bucket(shared_signal, row.get("shared_conflict_total")),
        axis=1,
    )
    merged["compile_feasibility_bucket"] = merged.apply(_compile_bucket, axis=1)
    merged["opportunity_tags"] = merged.apply(
        lambda row: _opportunity_tags(row, merged),
        axis=1,
    )

    return [
        BottleneckSignatureRecord(
            run_id=run_id,
            strategy_id=str(row["strategy_id"]),
            kernel_id=str(row["kernel_id"]),
            shape_id=str(row["shape_id"]),
            config_id=str(row["config_id"]),
            workload_class=(str(row["workload_class"]) if pd.notna(row["workload_class"]) else None),
            occupancy_bucket=str(row["occupancy_bucket"]),
            tensor_util_bucket=str(row["tensor_util_bucket"]),
            memory_pressure_bucket=str(row["memory_pressure_bucket"]),
            scoreboard_bucket=str(row["scoreboard_bucket"]),
            shared_conflict_bucket=str(row["shared_conflict_bucket"]),
            compile_feasibility_bucket=str(row["compile_feasibility_bucket"]),
            selected_by_strategy=bool(row["selected_by_strategy"]),
            held_out_outcome=str(row["held_out_outcome"]),
            regret_to_best_measured=(
                float(row["regret_to_best_measured"])
                if pd.notna(row["regret_to_best_measured"])
                else None
            ),
            opportunity_tags=list(row["opportunity_tags"]),
        )
        for _, row in merged.iterrows()
    ]


def build_opportunity_catalog(signatures: pd.DataFrame) -> pd.DataFrame:
    if signatures.empty or "opportunity_tags" not in signatures.columns:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    exploded = _explode_tags(signatures)
    if exploded.empty or "opportunity_tag" not in exploded.columns:
        return pd.DataFrame()
    for opportunity_tag, subset in exploded.groupby("opportunity_tag", dropna=False):
        action = _recommended_action(str(opportunity_tag))
        rows.append(
            {
                "opportunity_tag": opportunity_tag,
                "occurrences": len(subset),
                "selected_regret_count": int((subset["held_out_outcome"] == "selected_regret").sum()),
                "regret_weight": int(subset["regret_to_best_measured"].dropna().shape[0]),
                "avg_regret_to_best_measured": subset["regret_to_best_measured"].dropna().mean(),
                "kernel_ids": ",".join(sorted(subset["kernel_id"].dropna().unique())),
                "workload_classes": ",".join(sorted(value for value in subset["workload_class"].dropna().unique())),
                "strategy_ids": ",".join(sorted(value for value in subset["strategy_id"].dropna().astype(str).unique())),
                "run_ids": ",".join(sorted(value for value in subset["run_id"].dropna().astype(str).unique())),
                "config_ids": ",".join(sorted(value for value in subset["config_id"].dropna().astype(str).unique())),
                "recommended_actions": "; ".join(action),
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["selected_regret_count", "occurrences", "opportunity_tag"],
        ascending=[False, False, True],
    )


def build_heuristic_candidates(catalog: pd.DataFrame) -> dict[str, Any]:
    if catalog.empty:
        return {"heuristic_candidates": []}
    candidates = []
    for row in catalog.head(8).to_dict(orient="records"):
        candidates.append(
            {
                "opportunity_tag": row["opportunity_tag"],
                "recommended_actions": [item.strip() for item in str(row["recommended_actions"]).split(";") if item.strip()],
                "rationale": {
                    "occurrences": int(row["occurrences"]),
                    "selected_regret_count": int(row["selected_regret_count"]),
                },
            }
        )
    return {"heuristic_candidates": candidates}


def _explode_tags(signatures: pd.DataFrame) -> pd.DataFrame:
    exploded_rows: list[dict[str, Any]] = []
    for row in signatures.to_dict(orient="records"):
        tags = row.get("opportunity_tags") or []
        for tag in tags:
            exploded = dict(row)
            exploded["opportunity_tag"] = tag
            exploded_rows.append(exploded)
    return pd.DataFrame(exploded_rows)


def _compile_bucket(row: pd.Series) -> str:
    if not bool(row.get("compile_success")):
        status = str(row.get("compile_status"))
        if status == "invalid_config":
            return "invalid"
        if status == "compile_failed":
            return "compile_failed"
        return "unusable"
    return "feasible"


def _held_out_outcome(row: pd.Series) -> str:
    held_out_latency = row.get("held_out_latency_us")
    best_held_out = row.get("best_held_out_us")
    if pd.isna(held_out_latency):
        return "not_evaluated"
    if pd.isna(best_held_out):
        return "evaluated"
    if bool(row.get("selected_by_strategy")):
        if held_out_latency <= best_held_out * 1.02:
            return "selected_competitive"
        return "selected_regret"
    return "evaluated_unselected"


def _opportunity_tags(row: pd.Series, merged: pd.DataFrame) -> list[str]:
    tags: list[str] = []
    register_series = pd.to_numeric(merged["register_count"], errors="coerce")
    register_median = register_series.dropna().median() if not register_series.dropna().empty else None

    if row.get("compile_feasibility_bucket") in {"invalid", "compile_failed"}:
        tags.append("structural_prune_failed_region")
    if (
        register_median is not None
        and pd.notna(row.get("register_count"))
        and float(row["register_count"]) >= float(register_median)
        and row.get("occupancy_bucket") == "low"
    ):
        tags.append("reduce_num_stages_or_tile_size")
    if row.get("tensor_util_bucket") == "low" and row.get("memory_pressure_bucket") == "low":
        tags.append("increase_block_k_or_num_warps")
    if row.get("memory_pressure_bucket") == "high" and pd.notna(row.get("cache_hit_rate")) and row.get("cache_hit_rate", 100.0) < 60.0:
        tags.append("increase_tile_reuse_or_vectorize")
    if row.get("scoreboard_bucket") == "high" and pd.notna(row.get("lg_throttle")) and row.get("lg_throttle", 0.0) > 0.0:
        tags.append("increase_pipeline_staging_or_reduce_wave_pressure")
    if row.get("shared_conflict_bucket") == "high":
        tags.append("rework_shared_layout_or_block_shape")
    if bool(row.get("selected_by_strategy")) and row.get("held_out_outcome") == "selected_regret":
        tags.append("selector_revision_candidate")
    return sorted(set(tags))


def _recommended_action(opportunity_tag: str) -> list[str]:
    mapping = {
        "structural_prune_failed_region": [
            "prune failing config regions structurally",
            "tighten shared-memory and validity guards",
        ],
        "reduce_num_stages_or_tile_size": [
            "reduce num_stages",
            "reduce tile size",
        ],
        "increase_block_k_or_num_warps": [
            "increase block_k",
            "increase num_warps",
        ],
        "increase_tile_reuse_or_vectorize": [
            "increase tile reuse",
            "test vectorized load/store variants",
        ],
        "increase_pipeline_staging_or_reduce_wave_pressure": [
            "increase pipeline staging",
            "reduce memory pressure per wave",
        ],
        "rework_shared_layout_or_block_shape": [
            "alter shared-memory tile layout",
            "test a different block shape",
        ],
        "selector_revision_candidate": [
            "penalize this bottleneck signature earlier in ranking",
            "test an opportunity-guided selector revision",
        ],
    }
    return mapping.get(opportunity_tag, ["manual investigation"])


def summarize_opportunity_counts(signatures: pd.DataFrame) -> dict[str, int]:
    if signatures.empty:
        return {}
    counts: Counter[str] = Counter()
    for tags in signatures["opportunity_tags"]:
        for tag in tags or []:
            counts[tag] += 1
    return dict(sorted(counts.items()))
