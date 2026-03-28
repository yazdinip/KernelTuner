#!/usr/bin/env python3
"""Build a reusable analysis bundle for the completed Phase 2 studies."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class StudyDef:
    study_id: str
    label: str
    kind: str
    expected_run_count: int
    expected_hypotheses: int
    notes: str


@dataclass(frozen=True)
class CampaignDef:
    campaign_id: str
    label: str
    expected_job_count: int
    notes: str


STUDIES: list[StudyDef] = [
    StudyDef(
        study_id="gemm_v2_baseline_mapping",
        label="Representative GEMM v2 baseline mapping",
        kind="gemm_primary",
        expected_run_count=6,
        expected_hypotheses=2,
        notes="Expanded representative GEMM comparison over the main selector ladder.",
    ),
    StudyDef(
        study_id="gemm_v2_selector_ablation",
        label="Representative GEMM v2 selector ablation",
        kind="gemm_ablation",
        expected_run_count=18,
        expected_hypotheses=0,
        notes="Parent versus frontier-only versus full-v3 ablation on representative GEMM.",
    ),
    StudyDef(
        study_id="layernorm_v2_small_regime",
        label="LayerNorm v2 small-batch regime",
        kind="layernorm_regime",
        expected_run_count=6,
        expected_hypotheses=1,
        notes="Small-batch LayerNorm regime study using memory_activity_lite.",
    ),
    StudyDef(
        study_id="layernorm_v2_large_regime",
        label="LayerNorm v2 large-batch regime",
        kind="layernorm_regime",
        expected_run_count=6,
        expected_hypotheses=1,
        notes="Large-batch LayerNorm regime study using memory_activity_lite.",
    ),
    StudyDef(
        study_id="gemm_v2_aligned_reference",
        label="Aligned GEMM v2 reference",
        kind="gemm_context",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Supporting aligned GEMM reference under the expanded v2 knob space.",
    ),
]

CAMPAIGNS: list[CampaignDef] = [
    CampaignDef(
        campaign_id="gemm_v2_baseline_mapping",
        label="Representative GEMM v2 baseline mapping",
        expected_job_count=6,
        notes="Repeatability plus robustness for the main representative GEMM ladder.",
    ),
    CampaignDef(
        campaign_id="gemm_v2_selector_ablation",
        label="Representative GEMM v2 selector ablation",
        expected_job_count=18,
        notes="Parent/frontier-only/full-v3 ablation jobs.",
    ),
    CampaignDef(
        campaign_id="layernorm_v2_regime_studies",
        label="LayerNorm v2 regime studies",
        expected_job_count=12,
        notes="Small-batch and large-batch LayerNorm regime runs.",
    ),
    CampaignDef(
        campaign_id="gemm_v2_aligned_reference",
        label="Aligned GEMM v2 reference",
        expected_job_count=6,
        notes="Repeatability plus robustness for the supporting aligned workload.",
    ),
]

CONFIG_SOURCE_HINTS = {
    "gemm_v2_baseline_mapping": "artifacts/gemm_v2_reportable",
    "gemm_v2_selector_ablation": {
        "phase2_gemm_v2_parent": "artifacts/gemm_v2_ablation_parent",
        "phase2_gemm_v2_frontier": "artifacts/gemm_v2_ablation_frontier",
        "phase2_gemm_v2_v3": "artifacts/gemm_v2_ablation_v3",
    },
    "layernorm_v2_small_regime": "artifacts/layernorm_v2_small_reportable",
    "layernorm_v2_large_regime": "artifacts/layernorm_v2_large_reportable",
    "gemm_v2_aligned_reference": "artifacts/gemm_v2_aligned_reportable",
}


def latest_run_dir(root: Path) -> Path:
    runs = sorted([path for path in root.glob("run_*") if path.is_dir()], key=lambda path: path.name)
    if not runs:
        raise FileNotFoundError(f"no run directories found under '{root}'")
    return runs[-1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decode_config_map(run_root: Path) -> dict[str, str]:
    if not run_root.exists():
        return {}
    run_dir = latest_run_dir(run_root)
    candidates_path = run_dir / "candidates.parquet"
    if not candidates_path.exists():
        return {}
    frame = pd.read_parquet(candidates_path, columns=["config_id", "config"])
    frame = frame.drop_duplicates(subset=["config_id"]).copy()
    frame["config"] = frame["config"].astype(str)
    return dict(zip(frame["config_id"], frame["config"], strict=False))


def build_campaign_integrity(repo_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for campaign in CAMPAIGNS:
        run_root = repo_root / "artifacts" / "campaigns" / campaign.campaign_id
        run_dir = latest_run_dir(run_root)
        status = load_json(run_dir / "campaign_status.json")
        summary = load_json(run_dir / "campaign_summary.json")
        rows.append(
            {
                "campaign_id": campaign.campaign_id,
                "label": campaign.label,
                "campaign_run_id": status["campaign_run_id"],
                "run_dir": str(run_dir),
                "expected_job_count": campaign.expected_job_count,
                "job_count": status.get("job_count"),
                "completed_jobs": status.get("completed_jobs"),
                "failed_jobs": status.get("failed_jobs"),
                "terminal_status": status.get("terminal_status"),
                "study_result_count": len(status.get("study_results", [])),
                "summary_path": str(run_dir / "campaign_summary.json"),
                "notes": campaign.notes,
                "is_complete": (
                    status.get("job_count") == campaign.expected_job_count
                    and status.get("completed_jobs") == campaign.expected_job_count
                    and status.get("failed_jobs") == 0
                    and status.get("terminal_status") == "success"
                    and summary.get("failed_jobs") == 0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_study_integrity(repo_root: Path) -> tuple[pd.DataFrame, dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    run_dirs: dict[str, Path] = {}
    for study in STUDIES:
        run_root = repo_root / "artifacts" / "studies" / study.study_id
        run_dir = latest_run_dir(run_root)
        run_dirs[study.study_id] = run_dir
        summary = load_json(run_dir / "cross_run_summary.json")
        hypothesis_path = run_dir / "hypothesis_results.csv"
        rows.append(
            {
                "study_id": study.study_id,
                "label": study.label,
                "study_run_id": summary["run_id"],
                "run_dir": str(run_dir),
                "kind": study.kind,
                "expected_run_count": study.expected_run_count,
                "run_count": summary.get("run_count"),
                "group_count": summary.get("group_count"),
                "primary_metric": summary.get("primary_metric"),
                "expected_hypotheses": study.expected_hypotheses,
                "has_hypothesis_results": hypothesis_path.exists(),
                "has_stability_report": (run_dir / "stability_report.csv").exists(),
                "has_strategy_metrics": (run_dir / "study_strategy_metrics.csv").exists(),
                "has_opportunity_catalog": (run_dir / "opportunity_catalog.csv").exists(),
                "has_evidence_bundle": (run_dir / "evidence_bundle.json").exists(),
                "has_figure_manifest": (run_dir / "figure_manifest.json").exists(),
                "notes": study.notes,
                "is_complete": (
                    summary.get("run_count") == study.expected_run_count
                    and (run_dir / "stability_report.csv").exists()
                    and (run_dir / "study_strategy_metrics.csv").exists()
                    and (run_dir / "evidence_bundle.json").exists()
                    and (run_dir / "figure_manifest.json").exists()
                    and (study.expected_hypotheses == 0 or hypothesis_path.exists())
                ),
            }
        )
    return pd.DataFrame(rows), run_dirs


def summarize_strategy_metrics(study_id: str, strategy_metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["group_id", "strategy_id", "selector_version", "selector_revision_id"]
    summary = (
        strategy_metrics.groupby(group_cols, dropna=False)
        .agg(
            kernel_family=("kernel_family", "first"),
            workload_classes=("workload_class", lambda values: ",".join(sorted(set(values)))),
            run_rows=("run_id", "count"),
            mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
            mean_speedup_vs_random=("speedup_vs_naive_random_search", "mean"),
            mean_winner_rate=("winner_rate", "mean"),
            mean_regret=("regret_vs_best_measured_calibration", "mean"),
            reportable=("is_reportable", "all"),
            counter_set_accepted=("counter_set_accepted", "all"),
        )
        .reset_index()
    )
    summary.insert(0, "study_id", study_id)
    return summary


def build_config_snapshot(
    repo_root: Path,
    study_id: str,
    stability_report: pd.DataFrame,
) -> pd.DataFrame:
    source_hint = CONFIG_SOURCE_HINTS[study_id]
    config_maps: dict[str, dict[str, str]] = {}
    if isinstance(source_hint, dict):
        for selector_version, relative_root in source_hint.items():
            config_maps[selector_version] = decode_config_map(repo_root / relative_root)
    else:
        config_maps["*"] = decode_config_map(repo_root / source_hint)

    rows: list[dict[str, Any]] = []
    for record in stability_report.to_dict(orient="records"):
        selector_version = record.get("selector_version")
        config_map = config_maps.get(selector_version) or config_maps.get("*", {})
        rows.append(
            {
                "study_id": study_id,
                "group_id": record.get("group_id"),
                "kernel_family": record.get("kernel_family"),
                "workload_class": record.get("workload_class"),
                "strategy_id": record.get("strategy_id"),
                "selector_version": selector_version,
                "selector_revision_id": record.get("selector_revision_id"),
                "most_common_selected_config_id": record.get("most_common_selected_config_id"),
                "decoded_config": config_map.get(record.get("most_common_selected_config_id"), ""),
                "selection_agreement": record.get("selection_agreement"),
                "metric_median": record.get("metric_median"),
                "stability_band": record.get("stability_band"),
            }
        )
    return pd.DataFrame(rows)


def build_claim_table(strategy_summary: pd.DataFrame, hypothesis_rows: pd.DataFrame) -> pd.DataFrame:
    claims: list[dict[str, Any]] = []

    def first_hypothesis(study_id: str, hypothesis_id: str) -> pd.Series | None:
        subset = hypothesis_rows[
            (hypothesis_rows["study_id"] == study_id) & (hypothesis_rows["hypothesis_id"] == hypothesis_id)
        ]
        if subset.empty:
            return None
        return subset.iloc[0]

    def strategy_mean(study_id: str, group_id: str, strategy_id: str, selector_version: str | None = None) -> float | None:
        subset = strategy_summary[
            (strategy_summary["study_id"] == study_id)
            & (strategy_summary["group_id"] == group_id)
            & (strategy_summary["strategy_id"] == strategy_id)
        ]
        if selector_version is not None:
            subset = subset[subset["selector_version"] == selector_version]
        if subset.empty:
            return None
        return float(subset["mean_speedup_vs_default"].mean())

    h1 = first_hypothesis("gemm_v2_baseline_mapping", "H1_phase2_gemm")
    h4 = first_hypothesis("gemm_v2_baseline_mapping", "H4_phase2_gemm")
    h2_small = first_hypothesis("layernorm_v2_small_regime", "H2_small_regime")
    h2_large = first_hypothesis("layernorm_v2_large_regime", "H2_large_regime")

    claims.append(
        {
            "claim_id": "C-P2-H1",
            "claim": "Cheap compile-ranked GEMM selection still lags the best reachable result on the expanded representative space.",
            "status": h1["status"] if h1 is not None else "missing",
            "supporting_artifacts": "gemm_v2_baseline_mapping",
            "evidence": h1["evidence"] if h1 is not None else "",
            "confidence": "High",
            "caveat": "The best reachable result is delivered by naive_random_search, not by the revised selector.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P2-H4",
            "claim": "The frontier-aware v3 GEMM revision did not generalize to the expanded v2 space.",
            "status": h4["status"] if h4 is not None else "missing",
            "supporting_artifacts": "gemm_v2_baseline_mapping; gemm_v2_selector_ablation",
            "evidence": h4["evidence"] if h4 is not None else "",
            "confidence": "High",
            "caveat": "Both frontier-only and full-v3 collapse onto the same oversized 256x256x32 family.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P2-LN-SMALL",
            "claim": "Small-batch LayerNorm profiling yields only a marginal gain over compile-only ranking.",
            "status": h2_small["status"] if h2_small is not None else "missing",
            "supporting_artifacts": "layernorm_v2_small_regime",
            "evidence": h2_small["evidence"] if h2_small is not None else "",
            "confidence": "Medium",
            "caveat": "The gain exists but is far below the pre-registered +0.02 margin.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P2-LN-LARGE",
            "claim": "Large-batch LayerNorm profiling is currently worse than compile-only ranking.",
            "status": h2_large["status"] if h2_large is not None else "missing",
            "supporting_artifacts": "layernorm_v2_large_regime",
            "evidence": h2_large["evidence"] if h2_large is not None else "",
            "confidence": "High",
            "caveat": "The regime split clarifies the negative result, but it does not yet explain why the profiled choice regresses.",
        }
    )
    rep_prune = strategy_mean("gemm_v2_baseline_mapping", "gemm_v2_representative", "prune_rank", "phase2_gemm_v2")
    aligned_prune = strategy_mean("gemm_v2_aligned_reference", "gemm_v2_aligned", "prune_rank", "phase2_gemm_v2")
    claims.append(
        {
            "claim_id": "C-P2-H3-CONTEXT",
            "claim": "Aligned GEMM remains more flattering than representative GEMM for the compile-ranked selector in the expanded v2 space.",
            "status": "directionally_supported",
            "supporting_artifacts": "gemm_v2_baseline_mapping; gemm_v2_aligned_reference",
            "evidence": f"prune_rank mean speedup vs default: representative={rep_prune:.4f}, aligned={aligned_prune:.4f}",
            "confidence": "Medium",
            "caveat": "This is contextual rather than a separately re-pre-registered phase-2 hypothesis.",
        }
    )
    return pd.DataFrame(claims)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows_"

    columns = list(frame.columns)
    string_rows = []
    for row in frame.itertuples(index=False, name=None):
        string_rows.append(["" if value is None else str(value) for value in row])

    widths = []
    for index, column in enumerate(columns):
        widths.append(max(len(str(column)), *(len(row[index]) for row in string_rows)))

    header = "| " + " | ".join(str(column).ljust(widths[index]) for index, column in enumerate(columns)) + " |"
    divider = "| " + " | ".join("-" * widths[index] for index, _ in enumerate(columns)) + " |"
    rows = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index, _ in enumerate(columns)) + " |"
        for row in string_rows
    ]
    return "\n".join([header, divider, *rows])


def build_markdown_summary(
    campaign_integrity: pd.DataFrame,
    study_integrity: pd.DataFrame,
    strategy_summary: pd.DataFrame,
    config_snapshot: pd.DataFrame,
    claim_table: pd.DataFrame,
) -> str:
    lines: list[str] = []
    lines.append("# Phase 2 Analysis Bundle")
    lines.append("")
    lines.append("Generated from the completed Phase 2 execution chain on March 27, 2026.")
    lines.append("")
    lines.append("## Artifact Integrity")
    lines.append("")
    for row in campaign_integrity.to_dict(orient="records"):
        lines.append(
            f"- `{row['campaign_id']}`: jobs `{row['completed_jobs']}/{row['job_count']}`, "
            f"failed `{row['failed_jobs']}`, terminal `{row['terminal_status']}`, complete `{row['is_complete']}`"
        )
    lines.append("")
    for row in study_integrity.to_dict(orient="records"):
        lines.append(
            f"- `{row['study_id']}`: run_count `{row['run_count']}`, "
            f"group_count `{row['group_count']}`, complete `{row['is_complete']}`"
        )
    lines.append("")
    lines.append("## Main Claims")
    lines.append("")
    for row in claim_table.to_dict(orient="records"):
        lines.append(f"- `{row['claim_id']}` `{row['status']}`: {row['claim']}")
        lines.append(f"  Evidence: {row['evidence']}")
        lines.append(f"  Caveat: {row['caveat']}")
    lines.append("")
    lines.append("## Key Strategy Means")
    lines.append("")
    key_cols = [
        "study_id",
        "group_id",
        "strategy_id",
        "selector_version",
        "selector_revision_id",
        "mean_speedup_vs_default",
        "mean_speedup_vs_random",
        "mean_winner_rate",
        "mean_regret",
    ]
    lines.append(dataframe_to_markdown(strategy_summary[key_cols].sort_values(["study_id", "group_id", "strategy_id"])))
    lines.append("")
    lines.append("## Selected Config Families")
    lines.append("")
    key_configs = config_snapshot[
        config_snapshot["strategy_id"].isin(["naive_random_search", "prune_rank", "prune_rank_profiled", "prune_rank_revised"])
    ][
        [
            "study_id",
            "group_id",
            "workload_class",
            "strategy_id",
            "selector_version",
            "most_common_selected_config_id",
            "decoded_config",
            "selection_agreement",
            "metric_median",
            "stability_band",
        ]
    ]
    lines.append(
        dataframe_to_markdown(key_configs.sort_values(["study_id", "group_id", "strategy_id", "workload_class"]))
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--output-dir",
        default="artifacts/analysis/phase2_20260327",
        help="Output directory for the generated analysis bundle",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    campaign_integrity = build_campaign_integrity(repo_root)
    study_integrity, study_run_dirs = build_study_integrity(repo_root)

    strategy_summaries: list[pd.DataFrame] = []
    config_snapshots: list[pd.DataFrame] = []
    hypothesis_frames: list[pd.DataFrame] = []

    for study in STUDIES:
        run_dir = study_run_dirs[study.study_id]
        strategy_metrics = pd.read_csv(run_dir / "study_strategy_metrics.csv")
        stability_report = pd.read_csv(run_dir / "stability_report.csv")
        strategy_summaries.append(summarize_strategy_metrics(study.study_id, strategy_metrics))
        config_snapshots.append(build_config_snapshot(repo_root, study.study_id, stability_report))

        hypothesis_path = run_dir / "hypothesis_results.csv"
        if hypothesis_path.exists():
            frame = pd.read_csv(hypothesis_path)
            frame.insert(0, "study_id", study.study_id)
            hypothesis_frames.append(frame)

    strategy_summary = pd.concat(strategy_summaries, ignore_index=True)
    config_snapshot = pd.concat(config_snapshots, ignore_index=True)
    hypothesis_rows = (
        pd.concat(hypothesis_frames, ignore_index=True)
        if hypothesis_frames
        else pd.DataFrame(columns=["study_id", "status", "evidence", "hypothesis_id", "description"])
    )
    claim_table = build_claim_table(strategy_summary, hypothesis_rows)

    campaign_integrity.to_csv(output_dir / "campaign_integrity_summary.csv", index=False)
    study_integrity.to_csv(output_dir / "study_integrity_summary.csv", index=False)
    strategy_summary.to_csv(output_dir / "strategy_mean_summary.csv", index=False)
    config_snapshot.to_csv(output_dir / "selected_config_families.csv", index=False)
    hypothesis_rows.to_csv(output_dir / "hypothesis_status_summary.csv", index=False)
    claim_table.to_csv(output_dir / "claim_table.csv", index=False)

    (output_dir / "campaign_integrity_summary.json").write_text(
        campaign_integrity.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "study_integrity_summary.json").write_text(
        study_integrity.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "strategy_mean_summary.json").write_text(
        strategy_summary.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "selected_config_families.json").write_text(
        config_snapshot.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "hypothesis_status_summary.json").write_text(
        hypothesis_rows.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "claim_table.json").write_text(
        claim_table.to_json(orient="records", indent=2), encoding="utf-8"
    )
    (output_dir / "phase2_analysis_summary.md").write_text(
        build_markdown_summary(
            campaign_integrity=campaign_integrity,
            study_integrity=study_integrity,
            strategy_summary=strategy_summary,
            config_snapshot=config_snapshot,
            claim_table=claim_table,
        ),
        encoding="utf-8",
    )

    index = {
        "generated_at_repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "campaign_integrity_summary": str(output_dir / "campaign_integrity_summary.csv"),
        "study_integrity_summary": str(output_dir / "study_integrity_summary.csv"),
        "strategy_mean_summary": str(output_dir / "strategy_mean_summary.csv"),
        "selected_config_families": str(output_dir / "selected_config_families.csv"),
        "hypothesis_status_summary": str(output_dir / "hypothesis_status_summary.csv"),
        "claim_table": str(output_dir / "claim_table.csv"),
        "phase2_analysis_summary": str(output_dir / "phase2_analysis_summary.md"),
    }
    (output_dir / "analysis_bundle_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
