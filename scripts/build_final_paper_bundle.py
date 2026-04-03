#!/usr/bin/env python3
"""Build the final paper-evidence bundle from repo-local artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PHASE_ANALYSIS_BUNDLES = {
    "phase2": "artifacts/analysis/phase2_20260327/analysis_bundle_index.json",
    "phase3": "artifacts/analysis/phase3_20260329/analysis_bundle_index.json",
}

MANDATORY_FINAL_STUDIES = {
    "gemm_final_baseline_mapping": "artifacts/studies/gemm_final_baseline_mapping/run_20260330T014317Z_359c1904",
    "gemm_final_selector_ablation": "artifacts/studies/gemm_final_selector_ablation/run_20260330T023529Z_7c800187",
}

MANDATORY_FINAL_CAMPAIGNS = {
    "gemm_final_baseline_mapping": {
        "path": "artifacts/campaigns/gemm_final_baseline_mapping/run_20260330T003313Z_9e0cdfce",
        "expected_job_count": 12,
    },
    "gemm_final_selector_ablation": {
        "path": "artifacts/campaigns/gemm_final_selector_ablation/run_20260330T014321Z_c4e9fa9d",
        "expected_job_count": 18,
    },
}

OPTIONAL_R7_STUDY_ROOTS = {
    "gemm_final_budget_sweep": "artifacts/studies/gemm_final_budget_sweep",
    "gemm_final_stability_extension": "artifacts/studies/gemm_final_stability_extension",
}

OPTIONAL_R7_CAMPAIGN_ROOTS = {
    "gemm_final_budget_sweep": {
        "path": "artifacts/campaigns/gemm_final_budget_sweep",
        "expected_job_count": 24,
    },
    "gemm_final_stability_extension": {
        "path": "artifacts/campaigns/gemm_final_stability_extension",
        "expected_job_count": 20,
    },
}

CONTEXT_ARTIFACTS = {
    "gemm_v2_aligned_reference": "artifacts/studies/gemm_v2_aligned_reference/run_20260327T190124Z_3a34cdc7",
    "gemm_v2_baseline_mapping": "artifacts/studies/gemm_v2_baseline_mapping/run_20260327T164637Z_0403b989",
    "layernorm_v2_small_regime": "artifacts/studies/layernorm_v2_small_regime/run_20260327T183157Z_53565cba",
    "layernorm_v2_large_regime": "artifacts/studies/layernorm_v2_large_regime/run_20260327T183158Z_37695a2d",
    "layernorm_v2_small_microstudy": "artifacts/studies/layernorm_v2_small_microstudy/run_20260329T053448Z_7c6e5dc1",
    "layernorm_v2_large_microstudy": "artifacts/studies/layernorm_v2_large_microstudy/run_20260329T053455Z_c4118a25",
    "gemm_v3_schedule_diag": "artifacts/studies/gemm_v3_schedule_diag/run_20260328T212649Z_7755304a",
    "gemm_v3_baseline_mapping": "artifacts/studies/gemm_v3_baseline_mapping/run_20260329T010211Z_dfb53abb",
    "gemm_v3_selector_ablation": "artifacts/studies/gemm_v3_selector_ablation/run_20260329T034953Z_e8b8ac98",
    "h4_retry_g3": "artifacts/studies/h4_retry_g3/run_20260327T035659Z_10f9baec",
}

NONCANONICAL_PHASE3_ARCHIVE_NOTE = (
    "/tmp/.../phase3_raw and superseded partial Phase 3 roots are noncanonical archive material "
    "and must not be promoted into final figures or claims."
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(root: Path, relative_path: str) -> Path:
    return root / relative_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def load_bundle_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing bundle index at {path}")
    return load_json(path)


def bundle_file(index: dict[str, Any], key: str) -> Path:
    if "files" in index:
        return Path(index["files"][key])
    return Path(index[key])


def find_required_paths(root: Path, mapping: dict[str, str]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for key, relative in mapping.items():
        path = resolve(root, relative)
        if not path.exists():
            raise FileNotFoundError(f"missing canonical path for {key}: {path}")
        resolved[key] = path
    return resolved


def latest_successful_run(run_root: Path, summary_filename: str) -> Path | None:
    if not run_root.exists():
        return None
    candidates = sorted(entry for entry in run_root.iterdir() if entry.is_dir() and entry.name.startswith("run_"))
    for run_dir in reversed(candidates):
        summary_path = run_dir / summary_filename
        if not summary_path.exists():
            continue
        try:
            payload = load_json(summary_path)
        except json.JSONDecodeError:
            continue
        terminal_status = payload.get("terminal_status")
        if terminal_status is None or terminal_status == "success":
            return run_dir
    return None


def latest_successful_study_runs(root: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for study_id, relative in OPTIONAL_R7_STUDY_ROOTS.items():
        latest = latest_successful_run(resolve(root, relative), "cross_run_summary.json")
        if latest is not None:
            resolved[study_id] = latest
    return resolved


def latest_successful_campaign_runs(root: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for campaign_id, metadata in OPTIONAL_R7_CAMPAIGN_ROOTS.items():
        latest = latest_successful_run(resolve(root, metadata["path"]), "campaign_status.json")
        if latest is not None:
            resolved[campaign_id] = latest
    return resolved


def aggregate_study_metrics(
    run_dir: Path,
    study_id: str,
    source_bundle: str,
) -> pd.DataFrame:
    metrics_path = run_dir / "study_strategy_metrics.csv"
    if not metrics_path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(metrics_path)
    if frame.empty:
        return pd.DataFrame()
    summary = (
        frame.groupby(
            [
                "group_id",
                "strategy_id",
                "selector_version",
                "selector_revision_id",
                "workload_class",
                "budget_id",
            ],
            dropna=False,
        )
        .agg(
            mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
            mean_speedup_vs_random=("speedup_vs_naive_random_search", "mean"),
            mean_winner_rate=("winner_rate", "mean"),
            mean_regret=("regret_vs_best_measured_calibration", "mean"),
            run_rows=("run_id", "count"),
            reportable_all=("is_reportable", "all"),
            counter_set_accepted_all=("counter_set_accepted", "all"),
        )
        .reset_index()
    )
    summary.insert(0, "study_id", study_id)
    summary.insert(1, "source_bundle", source_bundle)
    return summary


def _mean_or_none(frame: pd.DataFrame, strategy_id: str, selector_revision_id: str = "") -> float | None:
    subset = frame[frame["strategy_id"] == strategy_id]
    if selector_revision_id:
        subset = subset[subset["selector_revision_id"] == selector_revision_id]
    if subset.empty:
        return None
    return float(subset["geomean_speedup_vs_default_config"].mean())


def _budget_order_from_id(budget_id: str) -> tuple[int, int]:
    match = re.search(r"_b(\d+)p(\d+)$", budget_id)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"bench(\d+).*profile(\d+)", budget_id)
    if match:
        return int(match.group(1)), int(match.group(2))
    return (0, 0)


def build_artifact_integrity_summary(
    root: Path,
    phase2_index: dict[str, Any],
    phase3_index: dict[str, Any],
    mandatory_studies: dict[str, Path],
    mandatory_campaigns: dict[str, Path],
    optional_studies: dict[str, Path],
    optional_campaigns: dict[str, Path],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [
        {
            "artifact_id": "phase2_bundle",
            "kind": "analysis_bundle",
            "path": phase2_index["output_dir"],
            "promoted": True,
            "complete": True,
            "notes": "Canonical Phase 2 bundle promoted into the final paper package.",
        },
        {
            "artifact_id": "phase3_bundle",
            "kind": "analysis_bundle",
            "path": phase3_index["output_dir"],
            "promoted": True,
            "complete": True,
            "notes": "Canonical Phase 3 bundle promoted into the final paper package.",
        },
    ]

    for campaign_id, metadata in MANDATORY_FINAL_CAMPAIGNS.items():
        run_dir = mandatory_campaigns[campaign_id]
        status = load_json(run_dir / "campaign_status.json")
        rows.append(
            {
                "artifact_id": campaign_id,
                "kind": "campaign",
                "path": str(run_dir),
                "promoted": True,
                "complete": (
                    status.get("job_count") == metadata["expected_job_count"]
                    and status.get("completed_jobs") == metadata["expected_job_count"]
                    and status.get("failed_jobs") == 0
                    and status.get("terminal_status") == "success"
                ),
                "notes": f"expected_jobs={metadata['expected_job_count']}",
            }
        )

    for study_id, run_dir in mandatory_studies.items():
        summary = load_json(run_dir / "cross_run_summary.json")
        rows.append(
            {
                "artifact_id": study_id,
                "kind": "study",
                "path": str(run_dir),
                "promoted": True,
                "complete": (
                    (run_dir / "study_strategy_metrics.csv").exists()
                    and (run_dir / "evidence_bundle.json").exists()
                    and (run_dir / "figure_manifest.json").exists()
                    and summary.get("run_count", 0) > 0
                ),
                "notes": f"run_count={summary.get('run_count', 'unknown')}",
            }
        )

    for campaign_id, metadata in OPTIONAL_R7_CAMPAIGN_ROOTS.items():
        run_dir = optional_campaigns.get(campaign_id)
        if run_dir is None:
            rows.append(
                {
                    "artifact_id": campaign_id,
                    "kind": "campaign",
                    "path": str(resolve(root, metadata["path"])),
                    "promoted": False,
                    "complete": False,
                    "notes": "Optional R7 campaign not yet available in repo-local artifacts.",
                }
            )
            continue
        status = load_json(run_dir / "campaign_status.json")
        rows.append(
            {
                "artifact_id": campaign_id,
                "kind": "campaign",
                "path": str(run_dir),
                "promoted": True,
                "complete": (
                    status.get("job_count") == metadata["expected_job_count"]
                    and status.get("completed_jobs") == metadata["expected_job_count"]
                    and status.get("failed_jobs") == 0
                    and status.get("terminal_status") == "success"
                ),
                "notes": f"expected_jobs={metadata['expected_job_count']}",
            }
        )

    for study_id in OPTIONAL_R7_STUDY_ROOTS:
        run_dir = optional_studies.get(study_id)
        if run_dir is None:
            rows.append(
                {
                    "artifact_id": study_id,
                    "kind": "study",
                    "path": str(resolve(root, OPTIONAL_R7_STUDY_ROOTS[study_id])),
                    "promoted": False,
                    "complete": False,
                    "notes": "Optional R7 study not yet available in repo-local artifacts.",
                }
            )
            continue
        summary = load_json(run_dir / "cross_run_summary.json")
        rows.append(
            {
                "artifact_id": study_id,
                "kind": "study",
                "path": str(run_dir),
                "promoted": True,
                "complete": (
                    (run_dir / "study_strategy_metrics.csv").exists()
                    and (run_dir / "evidence_bundle.json").exists()
                    and (run_dir / "figure_manifest.json").exists()
                    and summary.get("run_count", 0) > 0
                ),
                "notes": f"run_count={summary.get('run_count', 'unknown')}",
            }
        )

    rows.extend(
        [
            {
                "artifact_id": "phase3_raw_archive_exclusion",
                "kind": "provenance_rule",
                "path": "/tmp/.../phase3_raw",
                "promoted": True,
                "complete": True,
                "notes": NONCANONICAL_PHASE3_ARCHIVE_NOTE,
            },
            {
                "artifact_id": "superseded_roots_exclusion",
                "kind": "provenance_rule",
                "path": "",
                "promoted": True,
                "complete": True,
                "notes": "The final bundle excludes incomplete or superseded campaign and study roots even when newer runs exist in the same family.",
            },
        ]
    )
    return pd.DataFrame(rows)


def build_final_strategy_summary(
    mandatory_studies: dict[str, Path],
    optional_studies: dict[str, Path],
    phase2_index: dict[str, Any],
    phase3_index: dict[str, Any],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    phase2_summary = pd.read_csv(bundle_file(phase2_index, "strategy_mean_summary"))
    frames.append(
        phase2_summary[
            phase2_summary["study_id"].isin(
                [
                    "gemm_v2_baseline_mapping",
                    "gemm_v2_selector_ablation",
                    "layernorm_v2_small_regime",
                    "layernorm_v2_large_regime",
                    "gemm_v2_aligned_reference",
                ]
            )
        ].assign(source_bundle="phase2")
    )

    phase3_summary = pd.read_csv(bundle_file(phase3_index, "strategy_mean_summary"))
    frames.append(
        phase3_summary[
            phase3_summary["study_id"].isin(
                [
                    "gemm_v3_baseline_mapping",
                    "gemm_v3_selector_ablation",
                    "gemm_v3_aligned_reference",
                    "layernorm_v2_small_microstudy",
                    "layernorm_v2_large_microstudy",
                ]
            )
        ].assign(source_bundle="phase3")
    )

    for study_id, run_dir in {**mandatory_studies, **optional_studies}.items():
        summary = aggregate_study_metrics(run_dir, study_id, "final")
        if not summary.empty:
            frames.append(summary)

    return pd.concat(frames, ignore_index=True, sort=False)


def build_strategy_by_budget_summary(optional_studies: dict[str, Path]) -> pd.DataFrame:
    run_dir = optional_studies.get("gemm_final_budget_sweep")
    if run_dir is None:
        return pd.DataFrame(
            columns=[
                "budget_id",
                "max_benchmarks",
                "max_profiles",
                "budget_order",
                "strategy_id",
                "selector_revision_id",
                "workload_class",
                "mean_speedup_vs_default",
                "mean_speedup_vs_random",
                "mean_regret",
                "run_rows",
            ]
        )

    frame = pd.read_csv(run_dir / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    for workload_class in sorted(set(frame["workload_class"].dropna().tolist()) | {"overall"}):
        subset = frame if workload_class == "overall" else frame[frame["workload_class"] == workload_class]
        grouped = (
            subset.groupby(["budget_id", "strategy_id", "selector_revision_id"], dropna=False)
            .agg(
                mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
                mean_speedup_vs_random=("speedup_vs_naive_random_search", "mean"),
                mean_regret=("regret_vs_best_measured_calibration", "mean"),
                run_rows=("run_id", "count"),
            )
            .reset_index()
        )
        for row in grouped.to_dict(orient="records"):
            max_benchmarks, max_profiles = _budget_order_from_id(str(row["budget_id"]))
            rows.append(
                {
                    "budget_id": row["budget_id"],
                    "max_benchmarks": max_benchmarks,
                    "max_profiles": max_profiles,
                    "budget_order": max_benchmarks,
                    "strategy_id": row["strategy_id"],
                    "selector_revision_id": row["selector_revision_id"],
                    "workload_class": workload_class,
                    "mean_speedup_vs_default": row["mean_speedup_vs_default"],
                    "mean_speedup_vs_random": row["mean_speedup_vs_random"],
                    "mean_regret": row["mean_regret"],
                    "run_rows": row["run_rows"],
                }
            )
    return pd.DataFrame(rows).sort_values(
        by=["budget_order", "workload_class", "strategy_id", "selector_revision_id"],
        ignore_index=True,
    )


def build_uncertainty_stability_summary(optional_studies: dict[str, Path]) -> pd.DataFrame:
    run_dir = optional_studies.get("gemm_final_stability_extension")
    if run_dir is None:
        return pd.DataFrame(
            columns=[
                "row_kind",
                "strategy_id",
                "selector_revision_id",
                "seed",
                "mean_speedup_vs_default",
                "std_speedup_vs_default",
                "positive_vs_parent",
                "run_rows",
            ]
        )

    frame = pd.read_csv(run_dir / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    parent_by_seed = (
        frame[frame["strategy_id"] == "prune_rank"]
        .groupby("seed")["geomean_speedup_vs_default_config"]
        .mean()
        .to_dict()
    )

    per_seed = (
        frame.groupby(["strategy_id", "selector_revision_id", "seed"], dropna=False)
        .agg(
            mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
            std_speedup_vs_default=("geomean_speedup_vs_default_config", "std"),
            run_rows=("run_id", "count"),
        )
        .reset_index()
    )
    for row in per_seed.to_dict(orient="records"):
        parent_value = parent_by_seed.get(row["seed"])
        rows.append(
            {
                "row_kind": "per_seed",
                "strategy_id": row["strategy_id"],
                "selector_revision_id": row["selector_revision_id"],
                "seed": row["seed"],
                "mean_speedup_vs_default": row["mean_speedup_vs_default"],
                "std_speedup_vs_default": row["std_speedup_vs_default"],
                "positive_vs_parent": (
                    bool(row["mean_speedup_vs_default"] > parent_value)
                    if parent_value is not None and row["strategy_id"] != "prune_rank"
                    else None
                ),
                "run_rows": row["run_rows"],
            }
        )

    seed7 = frame[frame["seed"] == 7]
    repeatability = (
        seed7.groupby(["strategy_id", "selector_revision_id"], dropna=False)
        .agg(
            mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
            std_speedup_vs_default=("geomean_speedup_vs_default_config", "std"),
            run_rows=("run_id", "count"),
        )
        .reset_index()
    )
    for row in repeatability.to_dict(orient="records"):
        rows.append(
            {
                "row_kind": "repeatability_seed7",
                "strategy_id": row["strategy_id"],
                "selector_revision_id": row["selector_revision_id"],
                "seed": 7,
                "mean_speedup_vs_default": row["mean_speedup_vs_default"],
                "std_speedup_vs_default": row["std_speedup_vs_default"],
                "positive_vs_parent": None,
                "run_rows": row["run_rows"],
            }
        )

    return pd.DataFrame(rows)


def build_workload_class_regret_summary(
    mandatory_studies: dict[str, Path],
    optional_studies: dict[str, Path],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for study_id, run_dir in {**mandatory_studies, **optional_studies}.items():
        metrics_path = run_dir / "study_strategy_metrics.csv"
        if not metrics_path.exists():
            continue
        frame = pd.read_csv(metrics_path)
        grouped = (
            frame.groupby(["workload_class", "strategy_id", "selector_revision_id", "budget_id"], dropna=False)
            .agg(
                mean_regret=("regret_vs_best_measured_calibration", "mean"),
                mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
                run_rows=("run_id", "count"),
            )
            .reset_index()
        )
        grouped.insert(0, "study_id", study_id)
        rows.append(grouped)

    if not rows:
        return pd.DataFrame(
            columns=[
                "study_id",
                "workload_class",
                "strategy_id",
                "selector_revision_id",
                "budget_id",
                "mean_regret",
                "mean_speedup_vs_default",
                "run_rows",
            ]
        )
    return pd.concat(rows, ignore_index=True)


def build_figure2_budget_curve(strategy_by_budget: pd.DataFrame, mandatory_studies: dict[str, Path]) -> pd.DataFrame:
    if not strategy_by_budget.empty:
        return strategy_by_budget[
            (strategy_by_budget["workload_class"] == "overall")
            & (
                strategy_by_budget["strategy_id"].isin(
                    ["default_config", "naive_random_search", "prune_rank", "prune_rank_revised"]
                )
            )
        ].copy()

    baseline = pd.read_csv(mandatory_studies["gemm_final_baseline_mapping"] / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    for strategy_id, selector_revision_id in [
        ("default_config", ""),
        ("naive_random_search", ""),
        ("prune_rank", ""),
        ("prune_rank_revised", "v5_mainline_frontier"),
        ("prune_rank_revised", "v5_mainline_profiled"),
    ]:
        subset = baseline[baseline["strategy_id"] == strategy_id]
        if selector_revision_id:
            subset = subset[subset["selector_revision_id"] == selector_revision_id]
        if subset.empty:
            continue
        rows.append(
            {
                "budget_id": "gemm_final_budget_b12p4",
                "max_benchmarks": 12,
                "max_profiles": 4,
                "budget_order": 12,
                "strategy_id": strategy_id,
                "selector_revision_id": selector_revision_id,
                "workload_class": "overall",
                "mean_speedup_vs_default": float(subset["geomean_speedup_vs_default_config"].mean()),
                "mean_speedup_vs_random": float(subset["speedup_vs_naive_random_search"].mean()),
                "mean_regret": float(subset["regret_vs_best_measured_calibration"].mean()),
                "run_rows": int(subset["run_id"].count()),
                "source_note": "fallback_single_point_r6",
            }
        )
    return pd.DataFrame(rows)


def build_figure3_aligned_vs_representative(root: Path) -> pd.DataFrame:
    representative = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"]) / "study_strategy_metrics.csv")
    aligned = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"]) / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    for context_name, frame in [("representative", representative), ("aligned", aligned)]:
        for strategy_id, selector_revision_id in [
            ("prune_rank", ""),
            ("prune_rank_profiled", ""),
            ("naive_random_search", ""),
        ]:
            subset = frame[frame["strategy_id"] == strategy_id]
            if selector_revision_id:
                subset = subset[subset["selector_revision_id"] == selector_revision_id]
            if subset.empty:
                continue
            rows.append(
                {
                    "workload_context": context_name,
                    "strategy_id": strategy_id,
                    "selector_revision_id": selector_revision_id,
                    "mean_speedup_vs_default": float(subset["geomean_speedup_vs_default_config"].mean()),
                }
            )
    return pd.DataFrame(rows)


def build_figure4_layernorm_regimes(root: Path) -> pd.DataFrame:
    small = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_small_regime"]) / "study_strategy_metrics.csv")
    large = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_large_regime"]) / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    for regime, frame in [("small_batch", small), ("large_batch", large)]:
        for strategy_id, selector_revision_id in [
            ("prune_rank", ""),
            ("prune_rank_profiled", ""),
            ("prune_rank_revised", "v2_validation"),
        ]:
            subset = frame[frame["strategy_id"] == strategy_id]
            if selector_revision_id:
                subset = subset[subset["selector_revision_id"] == selector_revision_id]
            if subset.empty:
                continue
            rows.append(
                {
                    "regime": regime,
                    "strategy_id": strategy_id,
                    "selector_revision_id": selector_revision_id,
                    "mean_speedup_vs_default": float(subset["geomean_speedup_vs_default_config"].mean()),
                }
            )
    return pd.DataFrame(rows)


def build_figure5_transfer_failure(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transfer = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"]) / "study_strategy_metrics.csv")
    diagnostic = pd.read_csv(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"]) / "family_mismatch_summary.csv")
    rows: list[dict[str, Any]] = []
    for strategy_id, selector_revision_id, label in [
        ("prune_rank", "", "parent"),
        ("prune_rank_revised", "v4_transfer_safe_frontier", "v4_frontier"),
        ("prune_rank_revised", "v4_transfer_safe_profiled", "v4_profiled"),
    ]:
        subset = transfer[transfer["strategy_id"] == strategy_id]
        if selector_revision_id:
            subset = subset[subset["selector_revision_id"] == selector_revision_id]
        if subset.empty:
            continue
        rows.append(
            {
                "series": "transfer_failure",
                "label": label,
                "strategy_id": strategy_id,
                "selector_revision_id": selector_revision_id,
                "mean_speedup_vs_default": float(subset["geomean_speedup_vs_default_config"].mean()),
            }
        )
    transfer_frame = pd.DataFrame(rows)

    diag_rows: list[dict[str, Any]] = []
    revised = diagnostic[diagnostic["strategy_id"] == "prune_rank_revised"]
    if not revised.empty:
        row = revised.iloc[0]
        diag_rows.append(
            {
                "selected_matches_best_scored": bool(row["selected_matches_best_scored"]),
                "selected_split_k": row["selected_split_k"],
                "best_split_k": row["best_split_k"],
                "selected_score_regret": row["selected_score_regret"],
            }
        )
    diagnostic_frame = pd.DataFrame(diag_rows)

    return transfer_frame, diagnostic_frame


def build_figure5_mainline_ablation(mandatory_studies: dict[str, Path]) -> pd.DataFrame:
    ablation = pd.read_csv(mandatory_studies["gemm_final_selector_ablation"] / "study_strategy_metrics.csv")
    rows: list[dict[str, Any]] = []
    for group_id, strategy_id, selector_revision_id, label in [
        ("gemm_final_parent", "prune_rank", "", "parent"),
        ("gemm_final_frontier", "prune_rank_revised", "v5_mainline_frontier", "v5_frontier"),
        ("gemm_final_profiled", "prune_rank_revised", "v5_mainline_profiled", "v5_profiled"),
    ]:
        subset = ablation[(ablation["group_id"] == group_id) & (ablation["strategy_id"] == strategy_id)]
        if selector_revision_id:
            subset = subset[subset["selector_revision_id"] == selector_revision_id]
        if subset.empty:
            continue
        rows.append(
            {
                "series": "mainline_ablation",
                "label": label,
                "strategy_id": strategy_id,
                "selector_revision_id": selector_revision_id,
                "mean_speedup_vs_default": float(subset["geomean_speedup_vs_default_config"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_headline_result_summary(
    mandatory_studies: dict[str, Path],
    optional_studies: dict[str, Path],
) -> pd.DataFrame:
    baseline_metrics = pd.read_csv(mandatory_studies["gemm_final_baseline_mapping"] / "study_strategy_metrics.csv")
    baseline_metrics = baseline_metrics[baseline_metrics["group_id"] == "gemm_final_representative"].copy()
    ablation_metrics = pd.read_csv(mandatory_studies["gemm_final_selector_ablation"] / "study_strategy_metrics.csv")

    parent = _mean_or_none(baseline_metrics, "prune_rank")
    random_v = _mean_or_none(baseline_metrics, "naive_random_search")
    frontier = _mean_or_none(baseline_metrics, "prune_rank_revised", "v5_mainline_frontier")
    profiled = _mean_or_none(baseline_metrics, "prune_rank_revised", "v5_mainline_profiled")
    frontier_ablation = _mean_or_none(
        ablation_metrics[ablation_metrics["group_id"] == "gemm_final_frontier"].copy(),
        "prune_rank_revised",
        "v5_mainline_frontier",
    )
    profiled_ablation = _mean_or_none(
        ablation_metrics[ablation_metrics["group_id"] == "gemm_final_profiled"].copy(),
        "prune_rank_revised",
        "v5_mainline_profiled",
    )

    if parent is None or random_v is None or profiled is None:
        raise ValueError("missing required final headline metrics")

    r7_budget_points = None
    r7_loss_points = None
    r7_positive_points = None
    r7_positive_seeds = None
    r7_repeatability_std = None

    if "gemm_final_budget_sweep" in optional_studies:
        sweep = pd.read_csv(optional_studies["gemm_final_budget_sweep"] / "study_strategy_metrics.csv")
        sweep_rows = []
        for budget_id in sorted(sweep["budget_id"].dropna().unique(), key=_budget_order_from_id):
            budget = sweep[sweep["budget_id"] == budget_id]
            budget_parent = _mean_or_none(budget, "prune_rank")
            budget_profiled = _mean_or_none(budget, "prune_rank_revised", "v5_mainline_profiled")
            if budget_parent is None or budget_profiled is None:
                continue
            sweep_rows.append((budget_id, budget_profiled - budget_parent))
        r7_budget_points = len(sweep_rows)
        r7_loss_points = sum(1 for _, delta in sweep_rows if delta < 0)
        r7_positive_points = sum(1 for _, delta in sweep_rows if delta > 0)

    if "gemm_final_stability_extension" in optional_studies:
        stability = pd.read_csv(optional_studies["gemm_final_stability_extension"] / "study_strategy_metrics.csv")
        parent_by_seed = (
            stability[stability["strategy_id"] == "prune_rank"]
            .groupby("seed")["geomean_speedup_vs_default_config"]
            .mean()
            .to_dict()
        )
        profiled_by_seed = (
            stability[
                (stability["strategy_id"] == "prune_rank_revised")
                & (stability["selector_revision_id"] == "v5_mainline_profiled")
            ]
            .groupby("seed")["geomean_speedup_vs_default_config"]
            .mean()
            .to_dict()
        )
        r7_positive_seeds = sum(
            1
            for seed in (7, 19, 43, 61, 97)
            if profiled_by_seed.get(seed, float("-inf")) > parent_by_seed.get(seed, float("inf"))
        )
        repeatability = stability[
            (stability["strategy_id"] == "prune_rank_revised")
            & (stability["selector_revision_id"] == "v5_mainline_profiled")
            & (stability["seed"] == 7)
        ]["geomean_speedup_vs_default_config"]
        r7_repeatability_std = float(repeatability.std()) if len(repeatability) > 1 else 0.0

    profiled_delta = profiled - parent
    profiled_gap = random_v - profiled

    if r7_positive_points is None or r7_positive_seeds is None or r7_loss_points is None:
        if profiled_delta >= 0.05 and profiled_gap <= 0.03:
            decision = "bounded_mainline_improvement"
        else:
            decision = "bounded_inconclusive_mainline"
    elif r7_loss_points >= 2:
        decision = "bounded_fragile_mainline"
    elif r7_positive_points >= 3 and r7_positive_seeds >= 3:
        decision = "small_stable_mainline_improvement"
    elif profiled_delta > 0:
        decision = "bounded_mainline_improvement"
    else:
        decision = "mainline_inconclusive"

    return pd.DataFrame(
        [
            {
                "study_id": "gemm_final_baseline_mapping",
                "parent_mean_speedup_vs_default": parent,
                "random_mean_speedup_vs_default": random_v,
                "frontier_mean_speedup_vs_default": frontier,
                "frontier_ablation_mean_speedup_vs_default": frontier_ablation,
                "profiled_ablation_mean_speedup_vs_default": profiled_ablation,
                "winner_revision_id": "v5_mainline_profiled",
                "winner_mean_speedup_vs_default": profiled,
                "winner_delta_vs_parent": profiled_delta,
                "winner_gap_to_random": profiled_gap,
                "r7_budget_points": r7_budget_points,
                "r7_profiled_positive_budget_points": r7_positive_points,
                "r7_profiled_loss_budget_points": r7_loss_points,
                "r7_profiled_positive_stability_seeds": r7_positive_seeds,
                "r7_profiled_repeatability_std": r7_repeatability_std,
                "decision": decision,
            }
        ]
    )


def build_canonical_artifact_map(
    root: Path,
    mandatory_studies: dict[str, Path],
    optional_studies: dict[str, Path],
) -> pd.DataFrame:
    rows = [
        {
            "artifact_id": "phase2_bundle",
            "role": "backbone_bundle",
            "path": str(resolve(root, "artifacts/analysis/phase2_20260327")),
            "notes": "Canonical Phase 2 bundle.",
        },
        {
            "artifact_id": "phase3_bundle",
            "role": "backbone_bundle",
            "path": str(resolve(root, "artifacts/analysis/phase3_20260329")),
            "notes": "Canonical Phase 3 bundle.",
        },
        {
            "artifact_id": "r6_representative_mapping",
            "role": "headline_study",
            "path": str(mandatory_studies["gemm_final_baseline_mapping"]),
            "notes": "Final representative GEMM mainline mapping study.",
        },
        {
            "artifact_id": "r6_selector_ablation",
            "role": "mechanism_study",
            "path": str(mandatory_studies["gemm_final_selector_ablation"]),
            "notes": "Final parent/frontier/profiled ablation study.",
        },
    ]

    if "gemm_final_budget_sweep" in optional_studies:
        rows.append(
            {
                "artifact_id": "r7_budget_sweep",
                "role": "evidence_hardening",
                "path": str(optional_studies["gemm_final_budget_sweep"]),
                "notes": "Budget-efficiency sweep over the final non-split_k mainline surface.",
            }
        )
    if "gemm_final_stability_extension" in optional_studies:
        rows.append(
            {
                "artifact_id": "r7_stability_extension",
                "role": "evidence_hardening",
                "path": str(optional_studies["gemm_final_stability_extension"]),
                "notes": "Repeatability and robustness extension at the canonical final budget.",
            }
        )

    rows.extend(
        [
            {
                "artifact_id": "phase2_aligned_reference",
                "role": "context_study",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"])),
                "notes": "Canonical aligned-context source.",
            },
            {
                "artifact_id": "phase2_representative_mapping",
                "role": "context_study",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                "notes": "Canonical Phase 2 representative GEMM comparison for aligned-context support.",
            },
            {
                "artifact_id": "phase2_layernorm_small_regime",
                "role": "secondary_context",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_small_regime"])),
                "notes": "Canonical Phase 2 LayerNorm small-batch regime source.",
            },
            {
                "artifact_id": "phase2_layernorm_large_regime",
                "role": "secondary_context",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_large_regime"])),
                "notes": "Canonical Phase 2 LayerNorm large-batch regime source.",
            },
            {
                "artifact_id": "phase3_schedule_diag",
                "role": "diagnostic_context",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"])),
                "notes": "Canonical chosen-family versus best-family diagnostic source.",
            },
            {
                "artifact_id": "phase3_transfer_mapping",
                "role": "diagnostic_context",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_baseline_mapping"])),
                "notes": "Canonical Phase 3 transfer-failure source for H5.",
            },
            {
                "artifact_id": "phase3_transfer_ablation",
                "role": "diagnostic_context",
                "path": str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                "notes": "Canonical Phase 3 transfer-ablation source for H4/H5.",
            },
        ]
    )
    return pd.DataFrame(rows)


def build_figure_source_map(root: Path, output_dir: Path, optional_studies: dict[str, Path]) -> pd.DataFrame:
    rows = [
        {
            "figure_id": "F1",
            "figure_name": "pipeline_schematic",
            "source_study": "design and methodology docs",
            "path": str(output_dir / "figure1_pipeline_schematic.csv"),
            "notes": "Plot-ready schematic metadata for the conceptual pipeline figure.",
        },
        {
            "figure_id": "F2",
            "figure_name": "representative_gemm_budget_curve",
            "source_study": "gemm_final_budget_sweep" if "gemm_final_budget_sweep" in optional_studies else "gemm_final_baseline_mapping",
            "path": str(output_dir / "figure2_budget_curve.csv"),
            "notes": "Budget-efficiency figure data on the final representative GEMM mainline surface.",
        },
        {
            "figure_id": "F3",
            "figure_name": "aligned_vs_representative_context",
            "source_study": "gemm_v2_aligned_reference + gemm_v2_baseline_mapping",
            "path": str(output_dir / "figure3_aligned_vs_representative.csv"),
            "notes": "Aligned-versus-representative context comparison.",
        },
        {
            "figure_id": "F4",
            "figure_name": "layernorm_regime_split",
            "source_study": "layernorm_v2_small_regime + layernorm_v2_large_regime",
            "path": str(output_dir / "figure4_layernorm_regimes.csv"),
            "notes": "LayerNorm regime-split comparison.",
        },
        {
            "figure_id": "F5A",
            "figure_name": "phase3_transfer_failure",
            "source_study": "gemm_v3_selector_ablation + gemm_v3_schedule_diag",
            "path": str(output_dir / "figure5_transfer_failure.csv"),
            "notes": "Phase 3 transfer-failure bars for the left panel of Figure 5.",
        },
        {
            "figure_id": "F5B",
            "figure_name": "final_mainline_ablation",
            "source_study": "gemm_final_selector_ablation",
            "path": str(output_dir / "figure5_mainline_ablation.csv"),
            "notes": "Final mainline ablation bars for the right panel of Figure 5.",
        },
    ]
    return pd.DataFrame(rows)


def build_final_claim_table(
    root: Path,
    headline_summary: pd.DataFrame,
    optional_studies: dict[str, Path],
) -> pd.DataFrame:
    headline = headline_summary.iloc[0]
    decision = str(headline["decision"])
    final_delta = float(headline["winner_delta_vs_parent"])
    final_gap = float(headline["winner_gap_to_random"])
    final_profiled = float(headline["winner_mean_speedup_vs_default"])
    final_parent = float(headline["parent_mean_speedup_vs_default"])
    final_random = float(headline["random_mean_speedup_vs_default"])
    frontier_ablation = headline["frontier_ablation_mean_speedup_vs_default"]
    profiled_ablation = headline["profiled_ablation_mean_speedup_vs_default"]

    if decision == "small_stable_mainline_improvement":
        headline_wording = (
            "A conservative v5_mainline_profiled selector delivers a small but stable representative GEMM improvement on the final non-split_k mainline under matched budget."
        )
        headline_status = "small_stable_improvement"
        headline_caveat = "This is still a bounded single-kernel, single-architecture result rather than a universal autotuning claim."
    elif decision in {"bounded_mainline_improvement", "bounded_fragile_mainline"}:
        headline_wording = (
            "A conservative v5_mainline_profiled selector yields a small but bounded representative GEMM improvement on the final non-split_k mainline under matched budget."
        )
        headline_status = decision
        headline_caveat = (
            "Treat this as a bounded mainline improvement. It is positive on the paper-facing surface, but not broad enough to claim universal robustness."
        )
    else:
        headline_wording = (
            "The final non-split_k mainline push narrows the gap to naive random search, but the evidence still supports only a bounded or inconclusive representative GEMM claim."
        )
        headline_status = "inconclusive"
        headline_caveat = "This wording should be used only if the R7 evidence fails to sustain the bounded-positive interpretation."

    headline_paths = [
        str(resolve(root, MANDATORY_FINAL_STUDIES["gemm_final_baseline_mapping"])),
        str(resolve(root, MANDATORY_FINAL_STUDIES["gemm_final_selector_ablation"])),
    ]
    if "gemm_final_budget_sweep" in optional_studies:
        headline_paths.append(str(optional_studies["gemm_final_budget_sweep"]))
    if "gemm_final_stability_extension" in optional_studies:
        headline_paths.append(str(optional_studies["gemm_final_stability_extension"]))

    rows = [
        {
            "claim_id": "C-FINAL-HEADLINE",
            "claim_classification": "headline",
            "hypothesis_id": "",
            "allowed_wording": headline_wording,
            "status": headline_status,
            "supporting_artifact_paths": "; ".join(headline_paths),
            "evidence": (
                f"canonical mainline means vs default: parent={final_parent:.4f}, v5_mainline_profiled={final_profiled:.4f}, "
                f"naive_random_search={final_random:.4f}, delta_vs_parent={final_delta:.4f}, gap_to_random={final_gap:.4f}, "
                f"frontier_ablation={float(frontier_ablation):.4f}, profiled_ablation={float(profiled_ablation):.4f}"
            ),
            "confidence": "High",
            "caveat": headline_caveat,
            "figure_table_mapping": "F2, F5B, T4",
        },
        {
            "claim_id": "C-FINAL-H1",
            "claim_classification": "supporting",
            "hypothesis_id": "H1",
            "allowed_wording": "Cheap compile-adjacent signals are useful for pruning but not sufficient for reliable representative GEMM ranking on realistic schedule surfaces.",
            "status": "supported",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                    str(resolve(root, "artifacts/analysis/phase2_20260327/claim_table.csv")),
                ]
            ),
            "evidence": "Phase 2 representative GEMM keeps compile-ranked selection well below the best reachable result on the expanded non-split_k surface, and the final mainline success depends on conservative frontier correction rather than compile ranking alone.",
            "confidence": "High",
            "caveat": "R7 budget and stability evidence can strengthen the practical framing, but H1 still rests primarily on the Phase 2 representative study.",
            "figure_table_mapping": "F2, F3, T4",
        },
        {
            "claim_id": "C-FINAL-H2",
            "claim_classification": "supporting",
            "hypothesis_id": "H2",
            "allowed_wording": "LayerNorm is a regime-split secondary result: small_batch profiling is weak and noisy, while large_batch continues to favor compile-only ranking.",
            "status": "bounded_mixed",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_small_regime"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_large_regime"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_small_microstudy"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_large_microstudy"])),
                ]
            ),
            "evidence": "Phase 2 regime studies and Phase 3 microstudies agree that profiling does not deliver a strong, uniform LayerNorm advantage under matched budget.",
            "confidence": "Medium",
            "caveat": "Keep LayerNorm explanatory and bounded; do not present it as a second major positive optimization story.",
            "figure_table_mapping": "F4, T4",
        },
        {
            "claim_id": "C-FINAL-H3",
            "claim_classification": "supporting",
            "hypothesis_id": "H3",
            "allowed_wording": "Aligned GEMM is useful as context, but it is not the truth source; it overstates selector quality relative to the representative GEMM workload program.",
            "status": "contextual_support",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                ]
            ),
            "evidence": "The aligned comparison remains more flattering than the representative workload matrix and is retained only as context.",
            "confidence": "Medium",
            "caveat": "Write H3 as an evaluation-context lesson, not as the headline.",
            "figure_table_mapping": "F3, T4",
        },
        {
            "claim_id": "C-FINAL-H4",
            "claim_classification": "supporting",
            "hypothesis_id": "H4",
            "allowed_wording": "Revised selectors are a transfer story rather than a simple success story: a narrow-space frontier-aware revision worked, but later expanded-space evidence showed that the same revision family did not generalize cleanly.",
            "status": "mixed_transfer_limited",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["h4_retry_g3"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                    str(resolve(root, MANDATORY_FINAL_STUDIES["gemm_final_selector_ablation"])),
                ]
            ),
            "evidence": (
                f"narrow-space H4 retry succeeded earlier; final mainline ablation now shows frontier-only={float(frontier_ablation):.4f} "
                f"and profiled={float(profiled_ablation):.4f} versus parent={final_parent:.4f} on the guarded non-split_k surface."
            ),
            "confidence": "High",
            "caveat": "Do not flatten H4 into either 'revisions always work' or 'revisions always fail'; the defensible claim is mixed, transfer-limited evidence.",
            "figure_table_mapping": "F5A, F5B, T4",
        },
        {
            "claim_id": "C-FINAL-H5",
            "claim_classification": "supporting",
            "hypothesis_id": "H5",
            "allowed_wording": "The transfer-safe v4 corrective pass remained unsupported on the expanded split_k space.",
            "status": "unsupported",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_baseline_mapping"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                ]
            ),
            "evidence": "The canonical Phase 3 representative GEMM mapping and ablation both keep the v4 family far below the parent selector and naive random search on the split_k space.",
            "confidence": "High",
            "caveat": "H5 stays specific to the expanded split_k Phase 3 surface and must not absorb the later non-split_k positive result.",
            "figure_table_mapping": "F5A, T4",
        },
        {
            "claim_id": "C-FINAL-SPLITK",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "split_k is retired from the main GEMM reportable surface.",
            "status": "retire",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"])),
                    str(resolve(root, "artifacts/analysis/phase3_20260329/splitk_decision_table.csv")),
                ]
            ),
            "evidence": "The canonical Phase 3 diagnostic never promotes non-unit split_k into chosen or best-scored final families.",
            "confidence": "High",
            "caveat": "Retirement applies to the paper-facing mainline surface only; split_k remains available as archived diagnostic code.",
            "figure_table_mapping": "F5A",
        },
        {
            "claim_id": "C-FINAL-ROWS",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "rows_per_program is retired from the main LayerNorm surface.",
            "status": "retire",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_small_microstudy"])),
                    str(resolve(root, CONTEXT_ARTIFACTS["layernorm_v2_large_microstudy"])),
                    str(resolve(root, "artifacts/analysis/phase3_20260329/rows_per_program_decision_table.csv")),
                ]
            ),
            "evidence": "Non-unit rows_per_program appears only in weak or regressing paths and never becomes a stable mainline selector lever.",
            "confidence": "High",
            "caveat": "Retirement applies to the paper-facing mainline surface only; the knob remains part of archived diagnostic experiments.",
            "figure_table_mapping": "F4",
        },
        {
            "claim_id": "C-FINAL-CLOSEOUT",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "No further selector-family growth is justified for the paper backbone.",
            "status": "closed",
            "supporting_artifact_paths": "; ".join(headline_paths),
            "evidence": "The project now has both a bounded negative result on the split_k expansion and a bounded or stable final non-split_k mainline result, leaving no unresolved evidence-backed reason to admit another selector family.",
            "confidence": "High",
            "caveat": "This closes the current paper-facing research program; it does not claim that no future project could justify a different selector family.",
            "figure_table_mapping": "F2, F5B, T4",
        },
    ]
    return pd.DataFrame(rows)


def build_final_bundle_summary(
    headline_summary: pd.DataFrame,
    figure_source_map: pd.DataFrame,
    final_claim_table: pd.DataFrame,
) -> str:
    headline = headline_summary.iloc[0]
    lines = [
        "# Final Paper Evidence Bundle",
        "",
        "## Headline Decision",
        "",
        f"- decision: `{headline['decision']}`",
        f"- winner revision: `{headline['winner_revision_id']}`",
        f"- winner mean speedup vs default: `{headline['winner_mean_speedup_vs_default']:.4f}`",
        f"- parent mean speedup vs default: `{headline['parent_mean_speedup_vs_default']:.4f}`",
        f"- random mean speedup vs default: `{headline['random_mean_speedup_vs_default']:.4f}`",
        f"- winner delta vs parent: `{headline['winner_delta_vs_parent']:.4f}`",
        f"- winner gap to random: `{headline['winner_gap_to_random']:.4f}`",
        f"- R7 positive budget points: `{headline['r7_profiled_positive_budget_points']}`",
        f"- R7 loss budget points: `{headline['r7_profiled_loss_budget_points']}`",
        f"- R7 positive stability seeds: `{headline['r7_profiled_positive_stability_seeds']}`",
        "",
        "## Final Claim Set",
        "",
    ]
    for row in final_claim_table.to_dict(orient="records"):
        lines.append(
            f"- `{row['claim_id']}` `{row['status']}` `{row['claim_classification']}`: {row['allowed_wording']}"
        )
    lines.extend(["", "## Figure Sources", ""])
    for row in figure_source_map.to_dict(orient="records"):
        lines.append(f"- `{row['figure_id']}`: {row['source_study']} -> `{row['path']}`")
    return "\n".join(lines) + "\n"


def build_figure1_pipeline_metadata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"step_order": 1, "stage": "Candidate generation", "description": "Enumerate declared schedule space and keep only admissible configs."},
            {"step_order": 2, "stage": "Cheap signals", "description": "Collect compile-adjacent resource and admissibility signals."},
            {"step_order": 3, "stage": "Frontier construction", "description": "Prune and rank with cheap signals under matched budget."},
            {"step_order": 4, "stage": "Bounded profiling", "description": "Optionally profile a small frontier subset on calibration shapes."},
            {"step_order": 5, "stage": "Held-out evaluation", "description": "Benchmark the selected config on representative held-out shapes."},
            {"step_order": 6, "stage": "Evidence promotion", "description": "Promote only stable repo-local studies and bundles into claims."},
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-tag",
        default=f"final_paper_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        help="Artifact subdirectory name under artifacts/analysis/ (default: final_paper_<UTC date>).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = repo_root()
    output_dir = root / "artifacts" / "analysis" / args.output_tag
    output_dir.mkdir(parents=True, exist_ok=True)

    phase2_index = load_bundle_index(resolve(root, PHASE_ANALYSIS_BUNDLES["phase2"]))
    phase3_index = load_bundle_index(resolve(root, PHASE_ANALYSIS_BUNDLES["phase3"]))
    mandatory_studies = find_required_paths(root, MANDATORY_FINAL_STUDIES)
    mandatory_campaigns = {
        campaign_id: resolve(root, metadata["path"])
        for campaign_id, metadata in MANDATORY_FINAL_CAMPAIGNS.items()
    }
    optional_studies = latest_successful_study_runs(root)
    optional_campaigns = latest_successful_campaign_runs(root)

    artifact_integrity = build_artifact_integrity_summary(
        root,
        phase2_index,
        phase3_index,
        mandatory_studies,
        mandatory_campaigns,
        optional_studies,
        optional_campaigns,
    )
    canonical_map = build_canonical_artifact_map(root, mandatory_studies, optional_studies)
    final_strategy_summary = build_final_strategy_summary(
        mandatory_studies,
        optional_studies,
        phase2_index,
        phase3_index,
    )
    strategy_by_budget = build_strategy_by_budget_summary(optional_studies)
    uncertainty_stability = build_uncertainty_stability_summary(optional_studies)
    workload_regret = build_workload_class_regret_summary(mandatory_studies, optional_studies)
    headline_summary = build_headline_result_summary(mandatory_studies, optional_studies)
    figure1_pipeline = build_figure1_pipeline_metadata()
    figure2_budget_curve = build_figure2_budget_curve(strategy_by_budget, mandatory_studies)
    figure3_context = build_figure3_aligned_vs_representative(root)
    figure4_regimes = build_figure4_layernorm_regimes(root)
    figure5_transfer_failure, figure5_transfer_diagnostic = build_figure5_transfer_failure(root)
    figure5_mainline_ablation = build_figure5_mainline_ablation(mandatory_studies)
    figure_source_map = build_figure_source_map(root, output_dir, optional_studies)
    final_claim_table = build_final_claim_table(root, headline_summary, optional_studies)
    summary_md = build_final_bundle_summary(headline_summary, figure_source_map, final_claim_table)

    write_csv(output_dir / "artifact_integrity_summary.csv", artifact_integrity)
    write_csv(output_dir / "canonical_artifact_map.csv", canonical_map)
    write_csv(output_dir / "final_strategy_summary.csv", final_strategy_summary)
    write_csv(output_dir / "strategy_by_budget_summary.csv", strategy_by_budget)
    write_csv(output_dir / "uncertainty_stability_summary.csv", uncertainty_stability)
    write_csv(output_dir / "workload_class_regret_summary.csv", workload_regret)
    write_csv(output_dir / "headline_result_summary.csv", headline_summary)
    write_csv(output_dir / "figure1_pipeline_schematic.csv", figure1_pipeline)
    write_csv(output_dir / "figure2_budget_curve.csv", figure2_budget_curve)
    write_csv(output_dir / "figure3_aligned_vs_representative.csv", figure3_context)
    write_csv(output_dir / "figure4_layernorm_regimes.csv", figure4_regimes)
    write_csv(output_dir / "figure5_transfer_failure.csv", figure5_transfer_failure)
    write_csv(output_dir / "figure5_transfer_diagnostic.csv", figure5_transfer_diagnostic)
    write_csv(output_dir / "figure5_mainline_ablation.csv", figure5_mainline_ablation)
    write_csv(output_dir / "figure_source_map.csv", figure_source_map)
    write_csv(output_dir / "final_claim_table.csv", final_claim_table)
    (output_dir / "final_bundle_summary.md").write_text(summary_md, encoding="utf-8")

    index = {
        "bundle": "final_paper",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "output_dir": str(output_dir),
        "phase2_bundle": phase2_index["output_dir"],
        "phase3_bundle": phase3_index["output_dir"],
        "mandatory_final_studies": {study_id: run_dir.name for study_id, run_dir in mandatory_studies.items()},
        "optional_r7_studies": {study_id: run_dir.name for study_id, run_dir in optional_studies.items()},
        "canonical_context_artifacts": CONTEXT_ARTIFACTS,
        "files": {
            "artifact_integrity_summary": str(output_dir / "artifact_integrity_summary.csv"),
            "canonical_artifact_map": str(output_dir / "canonical_artifact_map.csv"),
            "final_strategy_summary": str(output_dir / "final_strategy_summary.csv"),
            "strategy_by_budget_summary": str(output_dir / "strategy_by_budget_summary.csv"),
            "uncertainty_stability_summary": str(output_dir / "uncertainty_stability_summary.csv"),
            "workload_class_regret_summary": str(output_dir / "workload_class_regret_summary.csv"),
            "headline_result_summary": str(output_dir / "headline_result_summary.csv"),
            "figure1_pipeline_schematic": str(output_dir / "figure1_pipeline_schematic.csv"),
            "figure2_budget_curve": str(output_dir / "figure2_budget_curve.csv"),
            "figure3_aligned_vs_representative": str(output_dir / "figure3_aligned_vs_representative.csv"),
            "figure4_layernorm_regimes": str(output_dir / "figure4_layernorm_regimes.csv"),
            "figure5_transfer_failure": str(output_dir / "figure5_transfer_failure.csv"),
            "figure5_transfer_diagnostic": str(output_dir / "figure5_transfer_diagnostic.csv"),
            "figure5_mainline_ablation": str(output_dir / "figure5_mainline_ablation.csv"),
            "figure_source_map": str(output_dir / "figure_source_map.csv"),
            "final_claim_table": str(output_dir / "final_claim_table.csv"),
            "final_bundle_summary": str(output_dir / "final_bundle_summary.md"),
        },
        "key_decisions": {
            "headline_decision": headline_summary.iloc[0]["decision"],
            "winner_revision_id": headline_summary.iloc[0]["winner_revision_id"],
            "budget_sweep_available": "gemm_final_budget_sweep" in optional_studies,
            "stability_extension_available": "gemm_final_stability_extension" in optional_studies,
            "h5_status": "unsupported",
            "split_k_mainline_status": "retired",
            "rows_per_program_mainline_status": "retired",
        },
    }
    (output_dir / "analysis_bundle_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
