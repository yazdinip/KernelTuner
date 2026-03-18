"""Cross-run study comparison."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

from kernel_tuner.analysis.reporting import summarize_run
from kernel_tuner.common.config import (
    kernel_config_path,
    load_experiment_spec,
    load_kernel_spec,
    load_study_spec,
    repo_root,
    resolve_artifact_root,
)
from kernel_tuner.common.ids import make_run_id
from kernel_tuner.common.provenance import (
    capture_environment_metadata,
    capture_invocation_metadata,
    capture_slurm_metadata,
)
from kernel_tuner.common.schema import Manifest, RunStatus, StudySpec
from kernel_tuner.storage import RunStore

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def compare_runs(
    study_spec: StudySpec,
    *,
    study_path: str | Path | None = None,
) -> dict[str, object]:
    artifact_root = resolve_artifact_root(study_spec.output_root, study_path)
    run_id = make_run_id()
    store = RunStore(artifact_root, study_spec.study_id, run_id)
    environment = capture_environment_metadata(Path.cwd())
    manifest = Manifest(
        experiment_id=study_spec.study_id,
        run_id=run_id,
        created_at_utc=datetime.now(timezone.utc),
        git_commit=environment.git_commit,
        git_branch=environment.git_branch,
        git_dirty=environment.git_dirty,
        environment=environment,
        invocation=capture_invocation_metadata(
            "ktune compare-runs",
            study_config_path=str(Path(study_path).resolve()) if study_path else None,
        ),
        slurm=capture_slurm_metadata(),
        artifact_files=[],
        status=RunStatus.CREATED,
        warnings=[],
    )
    store.initialize_manifest(manifest)
    try:
        run_payloads = _resolve_run_payloads(study_spec, study_path)
        strategy_rows = _build_strategy_rows(run_payloads)
        stability_report = _build_stability_report(strategy_rows)
        hypothesis_results = _evaluate_hypotheses(study_spec, strategy_rows, stability_report)
        opportunity_catalog = _aggregate_opportunities(run_payloads)

        if not strategy_rows.empty:
            store.write_csv_artifact("study_strategy_metrics", strategy_rows, filename="study_strategy_metrics.csv")
        if not stability_report.empty:
            store.write_csv_artifact("stability_report", stability_report, filename="stability_report.csv")
        if not hypothesis_results.empty:
            store.write_csv_artifact("hypothesis_results", hypothesis_results, filename="hypothesis_results.csv")
        if not opportunity_catalog.empty:
            store.write_csv_artifact("opportunity_catalog", opportunity_catalog, filename="opportunity_catalog.csv")
        plot_path = _write_comparison_plot(store, strategy_rows)

        summary = {
            "study_id": study_spec.study_id,
            "run_id": run_id,
            "run_count": len(run_payloads),
            "group_count": len(study_spec.run_groups),
            "primary_metric": study_spec.primary_metric,
            "secondary_metrics": study_spec.secondary_metrics,
            "group_by": study_spec.group_by,
            "strategy_summary": _strategy_summary(strategy_rows),
            "hypothesis_summary": hypothesis_results.to_dict(orient="records"),
            "artifact_locations": {
                "run_dir": str(store.run_dir),
                "strategy_metrics": str(store.run_dir / "study_strategy_metrics.csv") if not strategy_rows.empty else "",
                "stability_report": str(store.run_dir / "stability_report.csv") if not stability_report.empty else "",
                "hypothesis_results": str(store.run_dir / "hypothesis_results.csv") if not hypothesis_results.empty else "",
                "opportunity_catalog": str(store.run_dir / "opportunity_catalog.csv") if not opportunity_catalog.empty else "",
                "comparison_plot": str(store.run_dir / plot_path) if plot_path else "",
            },
        }
        store.write_json_artifact("cross_run_summary", summary, filename="cross_run_summary.json")
        store.finalize(RunStatus.SUCCESS)
        return {
            "study_id": study_spec.study_id,
            "run_id": run_id,
            "run_dir": str(store.run_dir),
            "cross_run_summary": str(store.run_dir / "cross_run_summary.json"),
        }
    except Exception as exc:
        store.finalize(RunStatus.FAILED, warnings=[str(exc)])
        raise


def compare_runs_from_path(study_path: str | Path) -> dict[str, object]:
    path = Path(study_path).resolve()
    return compare_runs(load_study_spec(path), study_path=path)


def _resolve_run_payloads(study_spec: StudySpec, study_path: str | Path | None) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    seen_run_dirs: set[Path] = set()
    for group in study_spec.run_groups:
        for run_dir in _resolve_group_run_dirs(group, study_spec, study_path):
            if run_dir in seen_run_dirs:
                continue
            seen_run_dirs.add(run_dir)
            payload = _load_run_payload(run_dir, group.group_id)
            if _passes_filters(payload, study_spec):
                payloads.append(payload)
    return payloads


def _resolve_group_run_dirs(group, study_spec: StudySpec, study_path: str | Path | None) -> list[Path]:
    paths: list[Path] = []
    for explicit in group.run_dirs:
        paths.append(Path(explicit).resolve())

    if group.experiment_ids:
        source_override = os.environ.get("KTUNE_SOURCE_ARTIFACT_ROOT")
        source_root_value = source_override or study_spec.comparison_rules.get("artifact_root", "artifacts")
        source_path = Path(source_root_value)
        artifact_root = (
            source_path.resolve()
            if source_path.is_absolute()
            else (repo_root(study_path) / source_path).resolve()
        )
        for experiment_id in group.experiment_ids:
            experiment_root = artifact_root / experiment_id
            if not experiment_root.exists():
                continue
            run_dirs = sorted(
                [path for path in experiment_root.iterdir() if path.is_dir()],
                key=lambda path: path.name,
            )
            if group.include_latest_runs:
                run_dirs = run_dirs[-group.include_latest_runs :]
            paths.extend(run_dirs)
    return paths


def _load_run_payload(run_dir: Path, group_id: str) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest = RunStore.from_run_dir(run_dir).load_manifest()
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        summarize_run(run_dir)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_experiment_path = run_dir / "experiment_spec.yaml"
    if manifest.invocation.experiment_config_path:
        candidate = Path(manifest.invocation.experiment_config_path)
        if candidate.exists():
            source_experiment_path = candidate
    experiment_spec = load_experiment_spec(source_experiment_path)
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], source_experiment_path))
    selection_decisions = _read_parquet_if_exists(run_dir / "selection_decisions.parquet")
    runtime_measurements = _read_parquet_if_exists(run_dir / "runtime_measurements.parquet")
    held_out_per_shape = _read_csv_if_exists(run_dir / "held_out_per_shape.csv")
    counter_availability = _read_csv_if_exists(run_dir / "counter_availability_report.csv")
    opportunity_catalog = _read_csv_if_exists(run_dir / "opportunity_catalog.csv")
    return {
        "group_id": group_id,
        "run_dir": run_dir,
        "summary": summary,
        "experiment_spec": experiment_spec,
        "kernel_spec": kernel_spec,
        "manifest": manifest,
        "selection_decisions": selection_decisions,
        "runtime_measurements": runtime_measurements,
        "held_out_per_shape": held_out_per_shape,
        "counter_availability": counter_availability,
        "opportunity_catalog": opportunity_catalog,
    }


def _passes_filters(payload: dict[str, Any], study_spec: StudySpec) -> bool:
    summary = payload["summary"]
    manifest = payload["manifest"]
    if study_spec.reportability_filter and not summary.get("reportability", {}).get("is_reportable", False):
        return False
    for field, expected in study_spec.environment_filter.items():
        actual = getattr(manifest.environment, field, None)
        if actual != expected:
            return False
    return True


def _build_strategy_rows(run_payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for payload in run_payloads:
        summary = payload["summary"]
        experiment_spec = payload["experiment_spec"]
        held_out = payload["held_out_per_shape"]
        selection = payload["selection_decisions"]
        counter_availability = payload["counter_availability"]
        if held_out.empty:
            continue
        selection_map = (
            selection.set_index("strategy_id").to_dict(orient="index")
            if not selection.empty and "strategy_id" in selection.columns
            else {}
        )
        counter_summary = (
            counter_availability.groupby("strategy_id")["non_null_fraction"].mean().to_dict()
            if not counter_availability.empty
            else {}
        )
        accepted_summary = (
            counter_availability.groupby("strategy_id")["acceptable"].all().to_dict()
            if not counter_availability.empty
            else {}
        )
        for workload_class in sorted(held_out["workload_class"].dropna().unique()):
            subset = held_out[held_out["workload_class"] == workload_class].copy()
            pivot = subset.pivot(index="shape_id", columns="strategy_id", values="latency_median_us")
            for strategy_id in pivot.columns:
                rows.append(
                    {
                        "group_id": payload["group_id"],
                        "run_id": summary["run_id"],
                        "experiment_id": experiment_spec.experiment_id,
                        "study_kind": experiment_spec.study_kind,
                        "kernel_family": payload["kernel_spec"].family,
                        "workload_class": workload_class,
                        "strategy_id": strategy_id,
                        "selector_version": experiment_spec.selector_version,
                        "counter_set_id": experiment_spec.counter_set_id,
                        "budget_id": experiment_spec.budget_id,
                        "seed": experiment_spec.seed,
                        "selected_config_id": selection_map.get(strategy_id, {}).get("selected_config_id"),
                        "geomean_speedup_vs_default_config": _speedup_to_baseline(pivot, strategy_id, "default_config"),
                        "speedup_vs_naive_random_search": _speedup_to_baseline(pivot, strategy_id, "naive_random_search"),
                        "speedup_vs_naive_grid_search": _speedup_to_baseline(pivot, strategy_id, "naive_grid_search"),
                        "winner_rate": float(subset[subset["strategy_id"] == strategy_id]["winner_on_shape"].mean()),
                        "regret_vs_best_measured_calibration": _selected_regret(
                            payload["runtime_measurements"],
                            strategy_id,
                            selection_map.get(strategy_id, {}).get("selected_config_id"),
                        ),
                        "counter_availability": counter_summary.get(strategy_id),
                        "counter_set_accepted": accepted_summary.get(strategy_id),
                        "is_reportable": summary.get("reportability", {}).get("is_reportable", False),
                    }
                )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(
        by=["group_id", "kernel_family", "workload_class", "strategy_id", "run_id"],
        ascending=[True, True, True, True, True],
    )


def _speedup_to_baseline(pivot: pd.DataFrame, strategy_id: str, baseline_id: str) -> float | None:
    if strategy_id not in pivot.columns or baseline_id not in pivot.columns:
        return None
    ratios = (pivot[baseline_id] / pivot[strategy_id]).dropna()
    if ratios.empty:
        return None
    return math.exp(sum(math.log(value) for value in ratios) / len(ratios))


def _selected_regret(runtime_measurements: pd.DataFrame, strategy_id: str, selected_config_id: str | None) -> float | None:
    if runtime_measurements.empty or selected_config_id is None:
        return None
    calibration = runtime_measurements[
        (runtime_measurements["measurement_phase"] == "calibration")
        & (runtime_measurements["status"] == "success")
    ].copy()
    if calibration.empty:
        return None
    strategy_rows = calibration[
        (calibration["strategy_id"] == strategy_id)
        & (calibration["config_id"] == selected_config_id)
    ].copy()
    if strategy_rows.empty:
        return None
    best = calibration.groupby("shape_id")["latency_median_us"].min()
    ratios: list[float] = []
    for _, row in strategy_rows.iterrows():
        best_latency = best.get(row["shape_id"])
        if best_latency is None or best_latency <= 0:
            continue
        ratios.append((row["latency_median_us"] / best_latency) - 1.0)
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def _build_stability_report(strategy_rows: pd.DataFrame) -> pd.DataFrame:
    if strategy_rows.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    grouped = strategy_rows.groupby(["group_id", "kernel_family", "workload_class", "strategy_id"], dropna=False)
    for (group_id, kernel_family, workload_class, strategy_id), subset in grouped:
        selected_counts = subset["selected_config_id"].value_counts(dropna=False)
        most_common_selected = selected_counts.index[0] if not selected_counts.empty else None
        agreement = (selected_counts.iloc[0] / len(subset)) if not selected_counts.empty else None
        values = subset["geomean_speedup_vs_default_config"].dropna()
        stability_band = None
        if not values.empty and values.median() != 0:
            stability_band = (values.max() - values.min()) / values.median()
        rows.append(
            {
                "group_id": group_id,
                "kernel_family": kernel_family,
                "workload_class": workload_class,
                "strategy_id": strategy_id,
                "run_count": len(subset),
                "most_common_selected_config_id": most_common_selected,
                "selection_agreement": agreement,
                "metric_min": values.min() if not values.empty else None,
                "metric_max": values.max() if not values.empty else None,
                "metric_median": values.median() if not values.empty else None,
                "stability_band": stability_band,
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["group_id", "kernel_family", "workload_class", "strategy_id"],
        ascending=[True, True, True, True],
    )


def _evaluate_hypotheses(
    study_spec: StudySpec,
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for hypothesis in study_spec.hypotheses:
        result = _evaluate_one_hypothesis(hypothesis.hypothesis_id, strategy_rows, stability_report)
        result["hypothesis_id"] = hypothesis.hypothesis_id
        result["description"] = hypothesis.description
        rows.append(result)
    return pd.DataFrame(rows)


def _evaluate_one_hypothesis(
    hypothesis_id: str,
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
) -> dict[str, Any]:
    hypothesis_id = hypothesis_id.upper()
    if strategy_rows.empty:
        return {"status": "inconclusive", "evidence": "no study rows available"}

    if hypothesis_id == "H1":
        gemm = strategy_rows[strategy_rows["kernel_family"] == "gemm"]
        if gemm.empty:
            return {"status": "inconclusive", "evidence": "no GEMM rows available"}
        prune_only = gemm[gemm["strategy_id"] == "prune_only"]["geomean_speedup_vs_default_config"].dropna()
        prune_rank = gemm[gemm["strategy_id"] == "prune_rank"]["geomean_speedup_vs_default_config"].dropna()
        rank_stability = stability_report[
            (stability_report["kernel_family"] == "gemm")
            & (stability_report["strategy_id"] == "prune_rank")
        ]["stability_band"].dropna()
        if prune_only.empty or prune_rank.empty or rank_stability.empty:
            return {"status": "inconclusive", "evidence": "missing prune_only/prune_rank GEMM evidence"}
        supported = prune_rank.mean() >= prune_only.mean() and rank_stability.mean() > 0.05
        return {
            "status": "supported" if supported else "unsupported",
            "evidence": (
                f"prune_rank_mean={prune_rank.mean():.4f}, prune_only_mean={prune_only.mean():.4f}, "
                f"prune_rank_stability_band={rank_stability.mean():.4f}"
            ),
        }

    if hypothesis_id == "H2":
        gemm_gain = _mean_strategy_gain(strategy_rows, "gemm", "prune_rank_profiled", "prune_rank")
        layernorm_gain = _mean_strategy_gain(strategy_rows, "layernorm", "prune_rank_profiled", "prune_rank")
        if gemm_gain is None or layernorm_gain is None:
            return {"status": "inconclusive", "evidence": "missing GEMM or LayerNorm profiled-vs-compile evidence"}
        supported = layernorm_gain > gemm_gain + 0.02
        return {
            "status": "supported" if supported else "unsupported",
            "evidence": f"layernorm_gain={layernorm_gain:.4f}, gemm_gain={gemm_gain:.4f}",
        }

    if hypothesis_id == "H3":
        aligned = strategy_rows[strategy_rows["group_id"].str.contains("aligned|current", case=False, regex=True)]
        representative = strategy_rows[
            strategy_rows["group_id"].str.contains("representative|expanded", case=False, regex=True)
        ]
        aligned_metric = _mean_strategy_value(aligned, "prune_rank")
        representative_metric = _mean_strategy_value(representative, "prune_rank")
        if aligned_metric is None or representative_metric is None:
            return {"status": "inconclusive", "evidence": "missing aligned or representative GEMM comparison groups"}
        supported = aligned_metric > representative_metric + 0.02
        return {
            "status": "supported" if supported else "unsupported",
            "evidence": (
                f"aligned_prune_rank={aligned_metric:.4f}, "
                f"representative_prune_rank={representative_metric:.4f}"
            ),
        }

    if hypothesis_id == "H4":
        base_metric = _mean_strategy_value(strategy_rows, "prune_rank")
        revised_metric = _mean_strategy_value(strategy_rows, "prune_rank_revised")
        if base_metric is None or revised_metric is None:
            return {"status": "inconclusive", "evidence": "missing prune_rank or prune_rank_revised rows"}
        supported = revised_metric > base_metric + 0.02
        return {
            "status": "supported" if supported else "unsupported",
            "evidence": f"prune_rank_revised={revised_metric:.4f}, prune_rank={base_metric:.4f}",
        }

    return {"status": "inconclusive", "evidence": "unknown hypothesis id"}


def _mean_strategy_gain(
    frame: pd.DataFrame,
    kernel_family: str,
    improved: str,
    baseline: str,
) -> float | None:
    subset = frame[frame["kernel_family"] == kernel_family]
    improved_metric = _mean_strategy_value(subset, improved)
    baseline_metric = _mean_strategy_value(subset, baseline)
    if improved_metric is None or baseline_metric is None:
        return None
    return improved_metric - baseline_metric


def _mean_strategy_value(frame: pd.DataFrame, strategy_id: str) -> float | None:
    if frame.empty:
        return None
    values = frame[frame["strategy_id"] == strategy_id]["geomean_speedup_vs_default_config"].dropna()
    if values.empty:
        return None
    return float(values.mean())


def _aggregate_opportunities(run_payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for payload in run_payloads:
        frame = payload["opportunity_catalog"]
        if frame.empty:
            continue
        decorated = frame.copy()
        decorated["group_id"] = payload["group_id"]
        decorated["run_id"] = payload["summary"]["run_id"]
        decorated["experiment_id"] = payload["experiment_spec"].experiment_id
        rows.append(decorated)
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    aggregated = (
        combined.groupby("opportunity_tag", dropna=False)
        .agg(
            occurrences=("occurrences", "sum"),
            selected_regret_count=("selected_regret_count", "sum"),
            avg_regret_to_best_measured=("avg_regret_to_best_measured", "mean"),
            recommended_actions=("recommended_actions", lambda values: "; ".join(sorted(set(values)))),
        )
        .reset_index()
        .sort_values(by=["selected_regret_count", "occurrences", "opportunity_tag"], ascending=[False, False, True])
    )
    return aggregated


def _strategy_summary(strategy_rows: pd.DataFrame) -> list[dict[str, Any]]:
    if strategy_rows.empty:
        return []
    aggregated = (
        strategy_rows.groupby(["group_id", "kernel_family", "workload_class", "strategy_id"], dropna=False)
        .agg(
            run_count=("run_id", "nunique"),
            geomean_speedup_vs_default_config=("geomean_speedup_vs_default_config", "mean"),
            speedup_vs_naive_random_search=("speedup_vs_naive_random_search", "mean"),
            speedup_vs_naive_grid_search=("speedup_vs_naive_grid_search", "mean"),
            winner_rate=("winner_rate", "mean"),
            regret_vs_best_measured_calibration=("regret_vs_best_measured_calibration", "mean"),
        )
        .reset_index()
    )
    return aggregated.to_dict(orient="records")


def _write_comparison_plot(store: RunStore, strategy_rows: pd.DataFrame) -> str | None:
    if strategy_rows.empty:
        return None
    aggregate = (
        strategy_rows.groupby(["kernel_family", "strategy_id"], dropna=False)["geomean_speedup_vs_default_config"]
        .mean()
        .reset_index()
    )
    figure, axis = plt.subplots(figsize=(9, 4))
    x_labels = [f"{row.kernel_family}:{row.strategy_id}" for row in aggregate.itertuples()]
    axis.bar(x_labels, aggregate["geomean_speedup_vs_default_config"])
    axis.set_ylabel("Geomean speedup vs default")
    axis.set_title("Cross-run primary metric by kernel and strategy")
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    buffer = store.run_dir / "comparison_primary_metric.png"
    figure.savefig(buffer, format="png")
    plt.close(figure)
    store.write_binary_artifact(
        "comparison_primary_metric_plot",
        buffer.read_bytes(),
        filename="comparison_primary_metric.png",
    )
    buffer.unlink(missing_ok=True)
    return "comparison_primary_metric.png"


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_parquet_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)
