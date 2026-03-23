"""Cross-run study comparison."""

from __future__ import annotations

import json
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

from kernel_tuner.analysis.reporting import summarize_run
from kernel_tuner.common.config import (
    experiment_config_path,
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
from kernel_tuner.common.schema import (
    HypothesisClause,
    HypothesisComparator,
    HypothesisMetricRef,
    Manifest,
    ReductionMode,
    RunStatus,
    StudySpec,
)
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
        if not run_payloads:
            raise ValueError("no study runs matched the configured groups and filters")
        strategy_rows = _build_strategy_rows(run_payloads)
        if strategy_rows.empty:
            raise ValueError("no held-out strategy rows were available after loading matched study runs")
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
        evidence_bundle = _build_evidence_bundle(strategy_rows, stability_report, hypothesis_results, run_payloads)
        figure_manifest = _build_figure_manifest(store, plot_path)
        store.write_json_artifact("evidence_bundle", evidence_bundle, filename="evidence_bundle.json")
        store.write_json_artifact("figure_manifest", figure_manifest, filename="figure_manifest.json")

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
                "evidence_bundle": str(store.run_dir / "evidence_bundle.json"),
                "figure_manifest": str(store.run_dir / "figure_manifest.json"),
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


def validate_study_from_path(study_path: str | Path) -> dict[str, object]:
    path = Path(study_path).resolve()
    study_spec = load_study_spec(path)
    resolved_experiments: dict[str, str] = {}
    missing_run_dirs: list[str] = []
    for group in study_spec.run_groups:
        for experiment_id in group.experiment_ids:
            resolved_experiments[experiment_id] = str(experiment_config_path(experiment_id, path))
        for run_dir in group.run_dirs:
            if not Path(run_dir).exists():
                missing_run_dirs.append(run_dir)
    return {
        "study_id": study_spec.study_id,
        "group_count": len(study_spec.run_groups),
        "hypothesis_count": len(study_spec.hypotheses),
        "resolved_experiments": resolved_experiments,
        "missing_run_dirs": missing_run_dirs,
        "all_hypotheses_have_clauses": all(bool(hypothesis.clauses) for hypothesis in study_spec.hypotheses),
    }


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
        "run_labels": summary.get("run_labels") or manifest.labels.model_dump(mode="json"),
        "selection_decisions": selection_decisions,
        "runtime_measurements": runtime_measurements,
        "held_out_per_shape": held_out_per_shape,
        "counter_availability": counter_availability,
        "opportunity_catalog": opportunity_catalog,
    }


def _passes_filters(payload: dict[str, Any], study_spec: StudySpec) -> bool:
    summary = payload["summary"]
    manifest = payload["manifest"]
    labels = payload.get("run_labels") or {}
    group_id = payload["group_id"]
    group = next((item for item in study_spec.run_groups if item.group_id == group_id), None)
    if study_spec.reportability_filter and not summary.get("reportability", {}).get("is_reportable", False):
        return False
    for field, expected in study_spec.environment_filter.items():
        actual = getattr(manifest.environment, field, None)
        if actual != expected:
            return False
    if group is None:
        return True
    if group.kernel_family and labels.get("kernel_family") != group.kernel_family:
        return False
    if group.selector_version and labels.get("selector_version") != group.selector_version:
        return False
    if group.selector_revision_id and labels.get("selector_revision_id") != group.selector_revision_id:
        return False
    if group.counter_set_id and labels.get("counter_set_id") != group.counter_set_id:
        return False
    if group.budget_id and labels.get("budget_id") != group.budget_id:
        return False
    if group.execution_mode and labels.get("execution_mode") != group.execution_mode:
        return False
    if group.seeds and labels.get("seed") not in group.seeds:
        return False
    if group.repeat_indices and labels.get("repeat_index") not in group.repeat_indices:
        return False
    return True


def _build_strategy_rows(run_payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for payload in run_payloads:
        summary = payload["summary"]
        experiment_spec = payload["experiment_spec"]
        labels = payload.get("run_labels") or {}
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
        workload_classes = sorted(held_out["workload_class"].dropna().unique())
        if not workload_classes:
            continue
        for workload_class in workload_classes:
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
                        "selector_revision_id": experiment_spec.selector_revision_id,
                        "counter_set_id": experiment_spec.counter_set_id,
                        "budget_id": experiment_spec.budget_id,
                        "seed": experiment_spec.seed,
                        "repeat_index": labels.get("repeat_index"),
                        "campaign_id": labels.get("campaign_id"),
                        "round_id": labels.get("round_id"),
                        "reportability_mode": labels.get("reportability_mode"),
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
        by=["group_id", "kernel_family", "workload_class", "strategy_id", "seed", "repeat_index", "run_id"],
        ascending=[True, True, True, True, True, True, True],
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
    working = strategy_rows.copy()
    for column in ["selector_version", "selector_revision_id", "counter_set_id", "budget_id"]:
        if column not in working.columns:
            working[column] = None
    rows: list[dict[str, Any]] = []
    grouped = working.groupby(
        [
            "group_id",
            "kernel_family",
            "workload_class",
            "strategy_id",
            "selector_version",
            "selector_revision_id",
            "counter_set_id",
            "budget_id",
        ],
        dropna=False,
    )
    for (
        group_id,
        kernel_family,
        workload_class,
        strategy_id,
        selector_version,
        selector_revision_id,
        counter_set_id,
        budget_id,
    ), subset in grouped:
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
                "selector_version": selector_version,
                "selector_revision_id": selector_revision_id,
                "counter_set_id": counter_set_id,
                "budget_id": budget_id,
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
        result = _evaluate_one_hypothesis(hypothesis, strategy_rows, stability_report)
        result["hypothesis_id"] = hypothesis.hypothesis_id
        result["description"] = hypothesis.description
        rows.append(result)
    return pd.DataFrame(rows)


def _evaluate_one_hypothesis(
    hypothesis,
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
) -> dict[str, Any]:
    if strategy_rows.empty:
        return {"status": "inconclusive", "evidence": "no study rows available"}
    if not hypothesis.clauses:
        return {"status": "inconclusive", "evidence": "hypothesis has no clauses"}

    clause_results = [_evaluate_clause(clause, strategy_rows, stability_report) for clause in hypothesis.clauses]
    if any(item["status"] == "inconclusive" for item in clause_results):
        return {
            "status": "inconclusive",
            "evidence": "; ".join(item["evidence"] for item in clause_results),
        }
    supported = all(item["supported"] for item in clause_results)
    return {
        "status": "supported" if supported else "unsupported",
        "evidence": "; ".join(item["evidence"] for item in clause_results),
    }


def _evaluate_clause(
    clause: HypothesisClause,
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
) -> dict[str, Any]:
    left_value = _metric_value(clause.left, strategy_rows, stability_report)
    if left_value is None:
        return {"status": "inconclusive", "supported": False, "evidence": "missing left-hand metric value"}
    if clause.right is not None:
        right_value = _metric_value(clause.right, strategy_rows, stability_report)
        if right_value is None:
            return {"status": "inconclusive", "supported": False, "evidence": "missing right-hand metric value"}
    else:
        right_value = clause.right_constant
    supported = _compare_hypothesis_values(left_value, right_value, clause.comparator, clause.minimum_delta)
    comparator_name = clause.comparator.value if hasattr(clause.comparator, "value") else str(clause.comparator)
    delta = left_value - right_value
    evidence = (
        f"{clause.left.metric}={left_value:.4f} "
        f"{comparator_name} "
        f"{right_value:.4f} with minimum_delta={clause.minimum_delta:.4f} "
        f"(observed_delta={delta:.4f})"
    )
    return {"status": "ok", "supported": supported, "evidence": evidence}


def _metric_value(
    metric_ref: HypothesisMetricRef,
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
) -> float | None:
    source_name = metric_ref.source.value if hasattr(metric_ref.source, "value") else str(metric_ref.source)
    frame = strategy_rows if source_name == "strategy_rows" else stability_report
    if frame.empty or metric_ref.metric not in frame.columns:
        return None
    subset = frame.copy()
    for field in [
        "group_id",
        "strategy_id",
        "kernel_family",
        "workload_class",
        "selector_version",
        "selector_revision_id",
        "counter_set_id",
        "budget_id",
    ]:
        expected = getattr(metric_ref, field)
        if expected is not None and field in subset.columns:
            subset = subset[subset[field] == expected]
    values = pd.to_numeric(subset[metric_ref.metric], errors="coerce").dropna()
    if values.empty:
        return None
    if metric_ref.reduction == ReductionMode.MEAN:
        return float(values.mean())
    if metric_ref.reduction == ReductionMode.MEDIAN:
        return float(values.median())
    if metric_ref.reduction == ReductionMode.MIN:
        return float(values.min())
    if metric_ref.reduction == ReductionMode.MAX:
        return float(values.max())
    return None


def _compare_hypothesis_values(
    left: float,
    right: float,
    comparator: HypothesisComparator,
    minimum_delta: float,
) -> bool:
    name = comparator.value if hasattr(comparator, "value") else str(comparator)
    if name == HypothesisComparator.GREATER_THAN.value:
        return left > right + minimum_delta
    if name == HypothesisComparator.GREATER_THAN_OR_EQUAL.value:
        return left >= right + minimum_delta
    if name == HypothesisComparator.LESS_THAN.value:
        return left < right + minimum_delta
    if name == HypothesisComparator.LESS_THAN_OR_EQUAL.value:
        return left <= right + minimum_delta
    raise ValueError(f"unsupported hypothesis comparator '{comparator}'")


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
    combined["weighted_regret_sum"] = (
        pd.to_numeric(combined.get("avg_regret_to_best_measured"), errors="coerce").fillna(0.0)
        * pd.to_numeric(combined.get("regret_weight"), errors="coerce").fillna(0.0)
    )
    aggregated = (
        combined.groupby("opportunity_tag", dropna=False)
        .agg(
            occurrences=("occurrences", "sum"),
            selected_regret_count=("selected_regret_count", "sum"),
            regret_weight=("regret_weight", "sum"),
            weighted_regret_sum=("weighted_regret_sum", "sum"),
            avg_regret_to_best_measured=("avg_regret_to_best_measured", "mean"),
            kernel_ids=("kernel_ids", lambda values: ",".join(sorted({item for value in values for item in str(value).split(",") if item}))),
            workload_classes=("workload_classes", lambda values: ",".join(sorted({item for value in values for item in str(value).split(",") if item}))),
            strategy_ids=("strategy_ids", lambda values: ",".join(sorted({item for value in values for item in str(value).split(",") if item}))),
            run_ids=("run_ids", lambda values: ",".join(sorted({item for value in values for item in str(value).split(",") if item}))),
            config_ids=("config_ids", lambda values: ",".join(sorted({item for value in values for item in str(value).split(",") if item}))),
            recommended_actions=("recommended_actions", lambda values: "; ".join(sorted(set(values)))),
        )
        .reset_index()
        .sort_values(by=["selected_regret_count", "occurrences", "opportunity_tag"], ascending=[False, False, True])
    )
    aggregated["avg_regret_to_best_measured"] = aggregated.apply(
        lambda row: (
            row["weighted_regret_sum"] / row["regret_weight"]
            if row["regret_weight"] and not pd.isna(row["regret_weight"])
            else row["avg_regret_to_best_measured"]
        ),
        axis=1,
    )
    aggregated = aggregated.drop(columns=["weighted_regret_sum"])
    return aggregated


def _strategy_summary(strategy_rows: pd.DataFrame) -> list[dict[str, Any]]:
    if strategy_rows.empty:
        return []
    rows: list[dict[str, Any]] = []
    grouped = strategy_rows.groupby(
        [
            "group_id",
            "kernel_family",
            "workload_class",
            "strategy_id",
            "selector_version",
            "selector_revision_id",
            "counter_set_id",
            "budget_id",
        ],
        dropna=False,
    )
    for keys, subset in grouped:
        (
            group_id,
            kernel_family,
            workload_class,
            strategy_id,
            selector_version,
            selector_revision_id,
            counter_set_id,
            budget_id,
        ) = keys
        primary_values = pd.to_numeric(subset["geomean_speedup_vs_default_config"], errors="coerce").dropna()
        ci_low, ci_high = _bootstrap_interval(primary_values.tolist())
        rows.append(
            {
                "group_id": group_id,
                "kernel_family": kernel_family,
                "workload_class": workload_class,
                "strategy_id": strategy_id,
                "selector_version": selector_version,
                "selector_revision_id": selector_revision_id,
                "counter_set_id": counter_set_id,
                "budget_id": budget_id,
                "run_count": int(subset["run_id"].nunique()),
                "geomean_speedup_vs_default_config": float(primary_values.mean()) if not primary_values.empty else None,
                "primary_metric_ci_low": ci_low,
                "primary_metric_ci_high": ci_high,
                "speedup_vs_naive_random_search": float(subset["speedup_vs_naive_random_search"].dropna().mean())
                if subset["speedup_vs_naive_random_search"].dropna().size
                else None,
                "speedup_vs_naive_grid_search": float(subset["speedup_vs_naive_grid_search"].dropna().mean())
                if subset["speedup_vs_naive_grid_search"].dropna().size
                else None,
                "winner_rate": float(subset["winner_rate"].dropna().mean()) if subset["winner_rate"].dropna().size else None,
                "regret_vs_best_measured_calibration": (
                    float(subset["regret_vs_best_measured_calibration"].dropna().mean())
                    if subset["regret_vs_best_measured_calibration"].dropna().size
                    else None
                ),
            }
        )
    return rows


def _bootstrap_interval(values: list[float], *, samples: int = 200, alpha: float = 0.05) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(0)
    estimates: list[float] = []
    for _ in range(samples):
        draw = [values[rng.randrange(len(values))] for _ in range(len(values))]
        estimates.append(sum(draw) / len(draw))
    estimates.sort()
    low_index = max(0, int((alpha / 2.0) * len(estimates)) - 1)
    high_index = min(len(estimates) - 1, int((1.0 - (alpha / 2.0)) * len(estimates)) - 1)
    return estimates[low_index], estimates[high_index]


def _build_evidence_bundle(
    strategy_rows: pd.DataFrame,
    stability_report: pd.DataFrame,
    hypothesis_results: pd.DataFrame,
    run_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    opportunity_catalog = _aggregate_opportunities(run_payloads)
    return {
        "run_count": len(run_payloads),
        "runs": [
            {
                "group_id": payload["group_id"],
                "run_id": payload["summary"]["run_id"],
                "experiment_id": payload["experiment_spec"].experiment_id,
                "run_dir": str(payload["run_dir"]),
                "run_labels": payload.get("run_labels") or {},
            }
            for payload in run_payloads
        ],
        "strategy_summary": _strategy_summary(strategy_rows),
        "stability_report": stability_report.to_dict(orient="records"),
        "hypothesis_results": hypothesis_results.to_dict(orient="records"),
        "opportunity_catalog": opportunity_catalog.to_dict(orient="records"),
    }


def _build_figure_manifest(store: RunStore, comparison_plot: str | None) -> dict[str, Any]:
    return {
        "figures": [
            {
                "figure_id": "comparison_primary_metric",
                "path": str(store.run_dir / comparison_plot) if comparison_plot else "",
                "supports_claim": "Cross-run primary metric by kernel and strategy",
            }
        ]
    }


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
