"""Summary generation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

from kernel_tuner.analysis.opportunities import (
    build_bottleneck_signatures,
    build_counter_availability_records,
    build_heuristic_candidates,
    build_opportunity_catalog,
    summarize_opportunity_counts,
)
from kernel_tuner.common.config import (
    counter_set_path,
    kernel_config_path,
    load_counter_set,
    load_experiment_spec,
    load_kernel_spec,
)
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


def _none_if_nan(value: Any) -> Any:
    return None if pd.isna(value) else value


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
    *,
    baseline_strategy_id: str = "default_config",
) -> pd.DataFrame:
    if strategy_metrics.empty or runtime_measurements.empty:
        return pd.DataFrame()
    baseline_row = None
    if baseline_strategy_id in set(strategy_metrics["strategy_id"]):
        baseline_row = strategy_metrics[strategy_metrics["strategy_id"] == baseline_strategy_id].iloc[0]
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


def _held_out_per_shape(runtime_measurements: pd.DataFrame, experiment_spec) -> pd.DataFrame:
    if runtime_measurements.empty:
        return pd.DataFrame()
    held_out = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "held_out")
        & (runtime_measurements["status"] == "success")
    ].copy()
    if held_out.empty:
        return pd.DataFrame()
    shape_meta = {
        shape.shape_id: {
            "workload_class": shape.workload_class or "unlabeled",
        }
        for shape in experiment_spec.shapes
    }
    pivot = held_out.pivot(index="shape_id", columns="strategy_id", values="latency_median_us")
    if "default_config" in pivot.columns:
        baseline = pivot["default_config"]
    else:
        baseline = pivot.iloc[:, 0]
    rows: list[dict[str, Any]] = []
    best_by_shape = pivot.min(axis=1)
    for shape_id in pivot.index:
        for strategy_id in pivot.columns:
            latency = pivot.loc[shape_id, strategy_id]
            if pd.isna(latency):
                continue
            rows.append(
                {
                    "shape_id": shape_id,
                    "workload_class": shape_meta.get(shape_id, {}).get("workload_class"),
                    "strategy_id": strategy_id,
                    "latency_median_us": latency,
                    "speedup_vs_default_config": (
                        baseline.loc[shape_id] / latency if pd.notna(baseline.loc[shape_id]) else None
                    ),
                    "winner_on_shape": latency <= best_by_shape.loc[shape_id] * 1.02,
                }
            )
    return pd.DataFrame(rows)


def _counter_availability_summary(availability: pd.DataFrame) -> dict[str, bool]:
    if availability.empty:
        return {}
    grouped = availability.groupby("strategy_id", dropna=False)["acceptable"].all()
    return {str(strategy_id): bool(value) for strategy_id, value in grouped.to_dict().items()}


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
    source_experiment_path = experiment_spec_path
    if not experiment_spec_path.exists():
        source_experiment_path = None
    if manifest.invocation.experiment_config_path:
        candidate = Path(manifest.invocation.experiment_config_path)
        if candidate.exists():
            source_experiment_path = candidate
    if source_experiment_path is None or not Path(source_experiment_path).exists():
        raise FileNotFoundError(
            f"run directory '{run_path}' is missing experiment_spec.yaml and manifest fallback is unavailable"
        )
    experiment_spec = load_experiment_spec(source_experiment_path)
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], source_experiment_path))

    compile_signals = _load_table(store, "compile_signals")
    runtime_measurements = _load_table(store, "runtime_measurements")
    profile_measurements = _load_table(store, "profile_measurements")
    selection_decisions = _load_table(store, "selection_decisions")

    selection_decisions = _decode_jsonish_columns(selection_decisions, ["score_map", "calibration_metadata"])
    profile_measurements = _decode_jsonish_columns(profile_measurements, ["counter_map", "profiler_metadata"])

    strategies = selection_decisions["strategy_id"].tolist() if "strategy_id" in selection_decisions.columns else []
    best_configs = (
        {
            str(strategy_id): _none_if_nan(selected_config_id)
            for strategy_id, selected_config_id in zip(
                selection_decisions["strategy_id"],
                selection_decisions["selected_config_id"],
                strict=False,
            )
        }
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
    held_out_per_shape = _held_out_per_shape(runtime_measurements, experiment_spec)

    counter_set = None
    if experiment_spec.counter_set_id:
        counter_set = load_counter_set(counter_set_path(experiment_spec.counter_set_id, source_experiment_path))
    requested_counters = counter_set.counters if counter_set else []
    minimum_availability = counter_set.minimum_availability if counter_set else 1.0
    compatibility_path = run_path / "counter_compatibility.json"
    counter_compatibility = {}
    if compatibility_path.exists():
        counter_compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    availability_records = build_counter_availability_records(
        run_id=manifest.run_id,
        profile_measurements=profile_measurements,
        requested_counters=requested_counters,
        minimum_availability=minimum_availability,
    )
    if availability_records:
        store.write_table("counter_availability", availability_records)
        availability_frame = _load_table(store, "counter_availability")
    else:
        availability_frame = pd.DataFrame()

    signature_records = build_bottleneck_signatures(
        run_id=manifest.run_id,
        experiment_spec=experiment_spec,
        compile_signals=compile_signals,
        runtime_measurements=runtime_measurements,
        profile_measurements=profile_measurements,
        selection_decisions=selection_decisions,
    )
    if signature_records:
        store.write_table("bottleneck_signatures", signature_records)
        signatures_frame = _decode_jsonish_columns(
            _load_table(store, "bottleneck_signatures"),
            ["opportunity_tags"],
        )
    else:
        signatures_frame = pd.DataFrame()

    opportunity_catalog = build_opportunity_catalog(signatures_frame)
    heuristic_candidates = build_heuristic_candidates(opportunity_catalog)

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
    if not held_out_per_shape.empty:
        store.write_csv_artifact("held_out_per_shape", held_out_per_shape, filename="held_out_per_shape.csv")
    if not availability_frame.empty:
        store.write_csv_artifact(
            "counter_availability_report",
            availability_frame,
            filename="counter_availability_report.csv",
        )
    if not opportunity_catalog.empty:
        store.write_csv_artifact(
            "opportunity_catalog",
            opportunity_catalog,
            filename="opportunity_catalog.csv",
        )
    store.write_yaml_artifact(
        "heuristic_candidates",
        heuristic_candidates,
        filename="heuristic_candidates.yaml",
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
        {
            str(strategy_id): _none_if_nan(comparison_class)
            for strategy_id, comparison_class in zip(
                selection_decisions["strategy_id"],
                selection_decisions["comparison_class"],
                strict=False,
            )
        }
        if "comparison_class" in selection_decisions.columns
        else {}
    )
    counter_availability_ok = _counter_availability_summary(availability_frame)
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
        and (not counter_compatibility or counter_compatibility.get("acceptable", True))
        and (not counter_availability_ok or all(counter_availability_ok.values()))
    )

    winner_rates = (
        held_out_per_shape.groupby("strategy_id", dropna=False)["winner_on_shape"].mean().to_dict()
        if not held_out_per_shape.empty
        else {}
    )
    selection_stability = (
        [
            {
                "strategy_id": str(row["strategy_id"]),
                "selected_config_id": _none_if_nan(row["selected_config_id"]),
            }
            for row in selection_decisions[["strategy_id", "selected_config_id"]].to_dict(orient="records")
        ]
        if not selection_decisions.empty
        else []
    )

    interpretation_notes: list[str] = []
    if pairwise.empty:
        interpretation_notes.append("No held-out comparison metrics were available.")
    else:
        outperforming = pairwise[pairwise["speedup_vs_baseline"] > 1.0]
        if outperforming.empty:
            interpretation_notes.append("No strategy outperformed the baseline on held-out evaluation.")
        else:
            winners = ", ".join(outperforming["strategy_id"].tolist())
            interpretation_notes.append(f"Held-out speedups exceeded baseline for: {winners}.")
    if availability_frame.empty and experiment_spec.counter_set_id:
        interpretation_notes.append("No usable profiler counter availability rows were recorded.")
    elif not availability_frame.empty and not availability_frame["acceptable"].all():
        interpretation_notes.append("At least one requested profiler counter failed the availability threshold.")

    result = ExperimentResult(
        schema_version=SCHEMA_VERSION,
        experiment_id=experiment_spec.experiment_id,
        run_id=manifest.run_id,
        terminal_status=manifest.status,
        strategies=strategies,
        best_configs=best_configs,
        aggregate_metrics={
            "strategy_metrics": strategy_metrics.to_dict(orient="records"),
            "pairwise_speedups": pairwise.to_dict(orient="records"),
            "runtime_failures": runtime_failures,
            "profile_failures": profile_failures,
            "comparison_class_by_strategy": comparison_class_by_strategy,
            "held_out_shape_count": held_out_shape_count,
            "counter_availability": counter_availability_ok,
            "winner_rates": winner_rates,
            "opportunity_counts": summarize_opportunity_counts(signatures_frame),
            "kernel_family": kernel_spec.family,
            "selector_version": experiment_spec.selector_version,
            "budget_id": experiment_spec.budget_id,
            "counter_set_id": experiment_spec.counter_set_id,
            "seed": experiment_spec.seed,
            "selection_stability": selection_stability,
            "selector_revision_id": experiment_spec.selector_revision_id,
            "repeat_index": manifest.invocation.repeat_index,
            "campaign_id": manifest.invocation.campaign_id,
            "workload_matrix_id": manifest.labels.workload_matrix_id,
        },
        comparison_warnings=manifest.warnings,
        reportability={
            "target": experiment_spec.analysis_settings.reportability_target,
            "is_reportable": is_reportable,
            "comparison_class": "matched_budget" if is_reportable else "non_comparable",
            "counter_set_accepted": bool(counter_compatibility.get("acceptable", True))
            and (all(counter_availability_ok.values()) if counter_availability_ok else True),
            "counter_compatibility": counter_compatibility,
        },
        uncertainty_metrics={
            "interpretation_notes": interpretation_notes,
            "confidence_interval_method": experiment_spec.analysis_settings.confidence_interval_method,
        },
        artifact_locations={
            "run_dir": str(store.run_dir),
            "summary_path": str(store.run_dir / "summary.json"),
            "budget_usage": str(store.run_dir / "budget_usage.csv") if not budget_usage.empty else "",
            "held_out_pairwise": str(store.run_dir / "held_out_pairwise.csv") if not pairwise.empty else "",
            "held_out_per_shape": str(store.run_dir / "held_out_per_shape.csv") if not held_out_per_shape.empty else "",
            "signal_runtime_correlations": (
                str(store.run_dir / "signal_runtime_correlations.csv") if not correlations.empty else ""
            ),
            "counter_availability_report": (
                str(store.run_dir / "counter_availability_report.csv") if not availability_frame.empty else ""
            ),
            "bottleneck_signatures": (
                str(store.run_dir / "bottleneck_signatures.parquet") if not signatures_frame.empty else ""
            ),
            "opportunity_catalog": (
                str(store.run_dir / "opportunity_catalog.csv") if not opportunity_catalog.empty else ""
            ),
            "heuristic_candidates": str(store.run_dir / "heuristic_candidates.yaml"),
            "strategy_speedups_plot": str(store.run_dir / speedup_plot) if speedup_plot else "",
            "counter_compatibility": str(compatibility_path) if compatibility_path.exists() else "",
        },
        run_labels=manifest.labels.model_dump(mode="json"),
    )
    store.write_summary(result)
    return result.model_dump(mode="json")
