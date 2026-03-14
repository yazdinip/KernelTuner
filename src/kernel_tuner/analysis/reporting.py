"""Summary generation."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
import pandas as pd

from kernel_tuner.common.config import load_experiment_spec
from kernel_tuner.common.schema import ExperimentResult, SCHEMA_VERSION
from kernel_tuner.storage import RunStore

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _load_required_manifest(run_dir: Path):
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"run directory '{run_dir}' is missing manifest.json")
    return RunStore.from_run_dir(run_dir).load_manifest()


def _load_table(store: RunStore, logical_name: str) -> pd.DataFrame:
    path = store.run_dir / f"{logical_name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return store.load_table(logical_name)


def _decode_jsonish_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    decoded = frame.copy()
    for column in columns:
        if column not in decoded.columns:
            continue
        decoded[column] = decoded[column].apply(
            lambda value: json.loads(value) if isinstance(value, str) and value[:1] in {"{", "["} else value
        )
    return decoded


def _strategy_metrics(runtime: pd.DataFrame) -> pd.DataFrame:
    if runtime.empty or "measurement_phase" not in runtime.columns:
        return pd.DataFrame()
    successful = runtime[
        (runtime["measurement_phase"] == "held_out") & (runtime["status"] == "success")
    ].copy()
    if successful.empty:
        return pd.DataFrame()
    grouped = (
        successful.groupby("strategy_id", dropna=False)
        .agg(
            held_out_latency_mean_us=("latency_median_us", "mean"),
            held_out_throughput_mean=("throughput_value", "mean"),
            held_out_measurements=("config_id", "count"),
        )
        .reset_index()
    )
    return grouped


def _pairwise_speedups(
    strategy_metrics: pd.DataFrame,
    runtime_measurements: pd.DataFrame,
) -> pd.DataFrame:
    if strategy_metrics.empty or runtime_measurements.empty:
        return pd.DataFrame()
    baseline_row = None
    if "default_config" in set(strategy_metrics["strategy_id"]):
        baseline_row = strategy_metrics[strategy_metrics["strategy_id"] == "default_config"].iloc[0]
    else:
        baseline_row = strategy_metrics.iloc[0]
    held_out = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "held_out")
        & (runtime_measurements["status"] == "success")
    ].copy()
    if held_out.empty:
        return pd.DataFrame()
    pivot = held_out.pivot(index="shape_id", columns="strategy_id", values="latency_median_us")
    if baseline_row["strategy_id"] not in pivot.columns:
        return pd.DataFrame()

    base = pivot[baseline_row["strategy_id"]]
    speedups: dict[str, float] = {}
    for strategy_id in strategy_metrics["strategy_id"]:
        if strategy_id not in pivot.columns:
            continue
        ratios = (base / pivot[strategy_id]).dropna()
        if ratios.empty:
            continue
        log_mean = sum(math.log(value) for value in ratios) / len(ratios)
        speedups[strategy_id] = math.exp(log_mean)

    comparison = strategy_metrics.copy()
    comparison["speedup_vs_baseline"] = comparison["strategy_id"].map(speedups)
    comparison["baseline_strategy_id"] = baseline_row["strategy_id"]
    return comparison


def _signal_runtime_correlation(
    compile_signals: pd.DataFrame,
    runtime_measurements: pd.DataFrame,
) -> pd.DataFrame:
    if compile_signals.empty or runtime_measurements.empty:
        return pd.DataFrame()
    runtime = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "calibration")
        & (runtime_measurements["status"] == "success")
    ].copy()
    if runtime.empty:
        return pd.DataFrame()
    runtime = (
        runtime.groupby("config_id", dropna=False)
        .agg(calibration_latency_mean_us=("latency_median_us", "mean"))
        .reset_index()
    )
    signals = (
        compile_signals.groupby("config_id", dropna=False)
        .agg(
            occupancy_estimate=("occupancy_estimate", "mean"),
            register_count=("register_count", "mean"),
            shared_memory_bytes=("shared_memory_bytes", "max"),
        )
        .reset_index()
    )
    joined = signals.merge(runtime, on="config_id", how="inner")
    if joined.empty:
        return pd.DataFrame()
    rows = []
    for signal_column in ["occupancy_estimate", "register_count", "shared_memory_bytes"]:
        subset = joined[[signal_column, "calibration_latency_mean_us"]].dropna()
        correlation = None
        if len(subset) >= 2:
            if subset[signal_column].nunique(dropna=True) > 1 and subset["calibration_latency_mean_us"].nunique(dropna=True) > 1:
                correlation = subset[signal_column].corr(subset["calibration_latency_mean_us"])
        rows.append({"signal": signal_column, "pearson_correlation_to_latency": correlation})
    return pd.DataFrame(rows)


def _write_speedup_plot(store: RunStore, comparison: pd.DataFrame) -> str | None:
    if comparison.empty:
        return None
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.bar(comparison["strategy_id"], comparison["speedup_vs_baseline"])
    axis.set_ylabel("Speedup vs baseline")
    axis.set_title("Held-out strategy speedups")
    axis.tick_params(axis="x", rotation=30)
    figure.tight_layout()
    buffer = Path(store.run_dir / "strategy_speedups.png")
    figure.savefig(buffer, format="png")
    plt.close(figure)
    store.write_binary_artifact(
        "strategy_speedups_plot",
        buffer.read_bytes(),
        filename="strategy_speedups.png",
    )
    buffer.unlink(missing_ok=True)
    return "strategy_speedups.png"


def summarize_run(run_dir: str | Path) -> dict[str, object]:
    run_path = Path(run_dir).resolve()
    manifest = _load_required_manifest(run_path)
    store = RunStore.from_run_dir(run_path)
    experiment_spec_path = run_path / "experiment_spec.yaml"
    if not experiment_spec_path.exists():
        raise FileNotFoundError(f"run directory '{run_path}' is missing experiment_spec.yaml")
    experiment_spec = load_experiment_spec(experiment_spec_path)

    compile_signals = _load_table(store, "compile_signals")
    runtime_measurements = _load_table(store, "runtime_measurements")
    profile_measurements = _load_table(store, "profile_measurements")
    selection_decisions = _load_table(store, "selection_decisions")

    selection_decisions = _decode_jsonish_columns(selection_decisions, ["score_map", "calibration_metadata"])
    profile_measurements = _decode_jsonish_columns(profile_measurements, ["counter_map", "profiler_metadata"])

    strategies = selection_decisions["strategy_id"].tolist() if "strategy_id" in selection_decisions.columns else []
    best_configs = (
        dict(zip(selection_decisions["strategy_id"], selection_decisions["selected_config_id"], strict=False))
        if not selection_decisions.empty
        else {}
    )
    budget_usage = (
        selection_decisions[
            [
                "strategy_id",
                "benchmarks_requested",
                "profiles_requested",
                "decision_status",
                "comparison_class",
            ]
        ].copy()
        if not selection_decisions.empty
        else pd.DataFrame(
            columns=[
                "strategy_id",
                "benchmarks_requested",
                "profiles_requested",
                "decision_status",
                "comparison_class",
            ]
        )
    )
    strategy_metrics = _strategy_metrics(runtime_measurements)
    pairwise = _pairwise_speedups(strategy_metrics, runtime_measurements)
    correlations = _signal_runtime_correlation(compile_signals, runtime_measurements)

    if not budget_usage.empty:
        store.write_csv_artifact("budget_usage", budget_usage, filename="budget_usage.csv")
    if not pairwise.empty:
        store.write_csv_artifact("held_out_pairwise", pairwise, filename="held_out_pairwise.csv")
    if not correlations.empty:
        store.write_csv_artifact(
            "signal_runtime_correlations",
            correlations,
            filename="signal_runtime_correlations.csv",
        )
    speedup_plot = _write_speedup_plot(store, pairwise)

    runtime_failures = (
        runtime_measurements["status"].value_counts(dropna=False).to_dict()
        if "status" in runtime_measurements.columns
        else {}
    )
    profile_failures = (
        profile_measurements["profile_status"].value_counts(dropna=False).to_dict()
        if "profile_status" in profile_measurements.columns
        else {}
    )
    comparison_class_by_strategy = (
        dict(zip(selection_decisions["strategy_id"], selection_decisions["comparison_class"], strict=False))
        if "comparison_class" in selection_decisions.columns
        else {}
    )
    held_out_shape_count = (
        int(
            runtime_measurements[
                runtime_measurements.get("measurement_phase") == "held_out"
            ]["shape_id"].nunique()
        )
        if not runtime_measurements.empty
        and "measurement_phase" in runtime_measurements.columns
        and "shape_id" in runtime_measurements.columns
        else 0
    )
    is_reportable = bool(
        experiment_spec.study_kind == "reportable"
        and held_out_shape_count > 0
        and all(value == "matched_budget" for value in comparison_class_by_strategy.values())
    )

    interpretation_notes: list[str] = []
    if pairwise.empty:
        interpretation_notes.append("No held-out comparison metrics were available.")
    else:
        top_row = pairwise.sort_values("speedup_vs_baseline", ascending=False).iloc[0]
        if top_row["strategy_id"] == top_row["baseline_strategy_id"]:
            interpretation_notes.append("No strategy outperformed the baseline on held-out evaluation.")
        else:
            interpretation_notes.append(
                f"{top_row['strategy_id']} produced the strongest held-out speedup versus {top_row['baseline_strategy_id']}."
            )

    result = ExperimentResult(
        experiment_id=manifest.experiment_id,
        run_id=manifest.run_id,
        terminal_status=manifest.status,
        strategies=strategies,
        best_configs=best_configs,
        aggregate_metrics={
            "budget_consumption": budget_usage.to_dict(orient="records"),
            "runtime_comparison_metrics": pairwise.to_dict(orient="records"),
            "held_out_evaluation_metrics": strategy_metrics.to_dict(orient="records"),
            "failure_counts": {
                "runtime": runtime_failures,
                "profiling": profile_failures,
            },
            "interpretation_notes": interpretation_notes,
        },
        comparison_warnings=manifest.warnings,
        reportability={
            "study_kind": experiment_spec.study_kind,
            "is_reportable": is_reportable,
            "comparison_class_by_strategy": comparison_class_by_strategy,
        },
        uncertainty_metrics={
            "held_out_shape_count": held_out_shape_count,
            "successful_runtime_measurements": int(
                len(runtime_measurements[runtime_measurements.get("status") == "success"])
            )
            if not runtime_measurements.empty and "status" in runtime_measurements.columns
            else 0,
            "schema_version": SCHEMA_VERSION,
        },
        artifact_locations={
            "run_dir": str(run_path),
            "summary": "summary.json",
            "budget_usage_csv": "budget_usage.csv" if not budget_usage.empty else "",
            "held_out_pairwise_csv": "held_out_pairwise.csv" if not pairwise.empty else "",
            "signal_runtime_correlations_csv": (
                "signal_runtime_correlations.csv" if not correlations.empty else ""
            ),
            "strategy_speedups_png": speedup_plot or "",
        },
    )
    store.write_summary(result)
    return result.model_dump(mode="json")
