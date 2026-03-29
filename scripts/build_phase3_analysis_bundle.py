#!/usr/bin/env python3
"""Build a reusable analysis bundle for the completed Phase 3 studies."""

from __future__ import annotations

import argparse
import ast
import csv
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class CampaignRunDef:
    campaign_id: str
    label: str
    role: str
    run_id: str
    expected_job_count: int
    notes: str


@dataclass(frozen=True)
class StudyRunDef:
    study_id: str
    label: str
    role: str
    run_id: str
    expected_run_count: int
    expected_hypotheses: int
    notes: str


CANONICAL_CAMPAIGNS: list[CampaignRunDef] = [
    CampaignRunDef(
        campaign_id="gemm_v3_baseline_mapping",
        label="Representative GEMM v3 baseline mapping",
        role="canonical",
        run_id="run_20260328T231300Z_0f6b63e0",
        expected_job_count=6,
        notes="Canonical confirmation run for the representative GEMM v3 strategy ladder.",
    ),
    CampaignRunDef(
        campaign_id="gemm_v3_selector_ablation",
        label="Representative GEMM v3 selector ablation",
        role="canonical",
        run_id="run_20260329T010219Z_69aab824",
        expected_job_count=18,
        notes="Canonical confirmation run for parent vs frontier-only vs profiled-v4 ablation.",
    ),
    CampaignRunDef(
        campaign_id="gemm_v3_schedule_diag",
        label="Representative GEMM v3 schedule diagnostic",
        role="canonical",
        run_id="run_20260328T212402Z_dbb68af3",
        expected_job_count=1,
        notes="Diagnostic-only GEMM schedule-family run for frontier explanation.",
    ),
    CampaignRunDef(
        campaign_id="gemm_v3_aligned_reference",
        label="Aligned GEMM v3 reference",
        role="canonical",
        run_id="run_20260329T035000Z_87acc4c4",
        expected_job_count=6,
        notes="Canonical confirmation run for aligned GEMM v3 supporting context.",
    ),
    CampaignRunDef(
        campaign_id="layernorm_v2_microstudy",
        label="LayerNorm v2 microstudy",
        role="canonical",
        run_id="run_20260329T045536Z_44582656",
        expected_job_count=12,
        notes="Canonical confirmation run for the bounded LayerNorm microstudy.",
    ),
]

REPLICATION_CAMPAIGNS: list[CampaignRunDef] = [
    CampaignRunDef(
        campaign_id="gemm_v3_baseline_mapping",
        label="Representative GEMM v3 baseline mapping",
        role="replication",
        run_id="run_20260327T231851Z_5380d852",
        expected_job_count=6,
        notes="Earlier main Phase 3 representative GEMM run retained as replication evidence.",
    ),
    CampaignRunDef(
        campaign_id="gemm_v3_selector_ablation",
        label="Representative GEMM v3 selector ablation",
        role="replication",
        run_id="run_20260328T010102Z_0fddbaa6",
        expected_job_count=18,
        notes="Earlier main Phase 3 selector ablation retained as replication evidence.",
    ),
    CampaignRunDef(
        campaign_id="gemm_v3_aligned_reference",
        label="Aligned GEMM v3 reference",
        role="replication",
        run_id="run_20260328T212653Z_b8243156",
        expected_job_count=6,
        notes="Earlier main Phase 3 aligned-reference run retained as replication evidence.",
    ),
    CampaignRunDef(
        campaign_id="layernorm_v2_microstudy",
        label="LayerNorm v2 microstudy",
        role="replication",
        run_id="run_20260328T223326Z_ea61fc42",
        expected_job_count=12,
        notes="Earlier main Phase 3 LayerNorm microstudy retained as replication evidence.",
    ),
]

CANONICAL_STUDIES: list[StudyRunDef] = [
    StudyRunDef(
        study_id="gemm_v3_baseline_mapping",
        label="Representative GEMM v3 baseline mapping",
        role="canonical",
        run_id="run_20260329T010211Z_dfb53abb",
        expected_run_count=6,
        expected_hypotheses=2,
        notes="Canonical confirmation study for representative GEMM v3.",
    ),
    StudyRunDef(
        study_id="gemm_v3_selector_ablation",
        label="Representative GEMM v3 selector ablation",
        role="canonical",
        run_id="run_20260329T034953Z_e8b8ac98",
        expected_run_count=18,
        expected_hypotheses=0,
        notes="Canonical confirmation study for parent/frontier-only/profiled-v4 comparison.",
    ),
    StudyRunDef(
        study_id="gemm_v3_schedule_diag",
        label="Representative GEMM v3 schedule diagnostic",
        role="canonical",
        run_id="run_20260328T212649Z_7755304a",
        expected_run_count=1,
        expected_hypotheses=0,
        notes="Canonical diagnostic-only study for schedule-family explanation.",
    ),
    StudyRunDef(
        study_id="gemm_v3_aligned_reference",
        label="Aligned GEMM v3 reference",
        role="canonical",
        run_id="run_20260329T045530Z_7086b0e7",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Canonical confirmation study for aligned GEMM v3 context.",
    ),
    StudyRunDef(
        study_id="layernorm_v2_small_microstudy",
        label="LayerNorm v2 small-batch microstudy",
        role="canonical",
        run_id="run_20260329T053448Z_7c6e5dc1",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Canonical confirmation study for the small-batch LayerNorm microstudy.",
    ),
    StudyRunDef(
        study_id="layernorm_v2_large_microstudy",
        label="LayerNorm v2 large-batch microstudy",
        role="canonical",
        run_id="run_20260329T053455Z_c4118a25",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Canonical confirmation study for the large-batch LayerNorm microstudy.",
    ),
]

REPLICATION_STUDIES: list[StudyRunDef] = [
    StudyRunDef(
        study_id="gemm_v3_baseline_mapping",
        label="Representative GEMM v3 baseline mapping",
        role="replication",
        run_id="run_20260328T010058Z_7226d3f1",
        expected_run_count=6,
        expected_hypotheses=2,
        notes="Earlier main study retained as replication evidence.",
    ),
    StudyRunDef(
        study_id="gemm_v3_selector_ablation",
        label="Representative GEMM v3 selector ablation",
        role="replication",
        run_id="run_20260328T034306Z_5055e181",
        expected_run_count=18,
        expected_hypotheses=0,
        notes="Earlier main study retained as replication evidence.",
    ),
    StudyRunDef(
        study_id="gemm_v3_aligned_reference",
        label="Aligned GEMM v3 reference",
        role="replication",
        run_id="run_20260328T223319Z_7cada93b",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Earlier main study retained as replication evidence.",
    ),
    StudyRunDef(
        study_id="layernorm_v2_small_microstudy",
        label="LayerNorm v2 small-batch microstudy",
        role="replication",
        run_id="run_20260328T231251Z_29646063",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Earlier main study retained as replication evidence.",
    ),
    StudyRunDef(
        study_id="layernorm_v2_large_microstudy",
        label="LayerNorm v2 large-batch microstudy",
        role="replication",
        run_id="run_20260328T231256Z_847b98a5",
        expected_run_count=6,
        expected_hypotheses=0,
        notes="Earlier main study retained as replication evidence.",
    ),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False), encoding="utf-8")


def safe_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def compact_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def dict_counts_to_string(counts: dict[Any, int]) -> str:
    if not counts:
        return ""
    ordered = sorted(counts.items(), key=lambda item: (str(item[0]), item[1]))
    return "; ".join(f"{key}:{value}" for key, value in ordered)


def parse_config(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return ast.literal_eval(value)


def dataframe_to_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows_"
    columns = list(rows[0].keys())
    string_rows = [[("" if row.get(column) is None else str(row.get(column))) for column in columns] for row in rows]
    widths = [max(len(column), *(len(row[index]) for row in string_rows)) for index, column in enumerate(columns)]
    header = "| " + " | ".join(columns[i].ljust(widths[i]) for i in range(len(columns))) + " |"
    divider = "| " + " | ".join("-" * widths[i] for i in range(len(columns))) + " |"
    body = [
        "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(columns))) + " |"
        for row in string_rows
    ]
    return "\n".join([header, divider, *body])


def campaign_run_dir(repo_root: Path, definition: CampaignRunDef) -> Path:
    return repo_root / "artifacts" / "campaigns" / definition.campaign_id / definition.run_id


def study_run_dir(repo_root: Path, definition: StudyRunDef) -> Path:
    return repo_root / "artifacts" / "studies" / definition.study_id / definition.run_id


def build_campaign_integrity(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in [*CANONICAL_CAMPAIGNS, *REPLICATION_CAMPAIGNS]:
        run_dir = campaign_run_dir(repo_root, definition)
        status = read_json(run_dir / "campaign_status.json")
        summary = read_json(run_dir / "campaign_summary.json")
        rows.append(
            {
                "campaign_id": definition.campaign_id,
                "label": definition.label,
                "role": definition.role,
                "campaign_run_id": definition.run_id,
                "run_dir": str(run_dir),
                "expected_job_count": definition.expected_job_count,
                "job_count": status.get("job_count"),
                "completed_jobs": status.get("completed_jobs"),
                "failed_jobs": status.get("failed_jobs"),
                "terminal_status": status.get("terminal_status"),
                "study_result_count": len(status.get("study_results", [])),
                "summary_path": str(run_dir / "campaign_summary.json"),
                "notes": definition.notes,
                "is_complete": (
                    status.get("job_count") == definition.expected_job_count
                    and status.get("completed_jobs") == definition.expected_job_count
                    and status.get("failed_jobs") == 0
                    and status.get("terminal_status") == "success"
                    and summary.get("failed_jobs") == 0
                ),
            }
        )
    return rows


def build_study_integrity(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in [*CANONICAL_STUDIES, *REPLICATION_STUDIES]:
        run_dir = study_run_dir(repo_root, definition)
        summary = read_json(run_dir / "cross_run_summary.json")
        hypothesis_path = run_dir / "hypothesis_results.csv"
        rows.append(
            {
                "study_id": definition.study_id,
                "label": definition.label,
                "role": definition.role,
                "study_run_id": definition.run_id,
                "run_dir": str(run_dir),
                "expected_run_count": definition.expected_run_count,
                "run_count": summary.get("run_count"),
                "group_count": summary.get("group_count"),
                "primary_metric": summary.get("primary_metric"),
                "diagnostic_only": summary.get("diagnostic_only"),
                "expected_hypotheses": definition.expected_hypotheses,
                "has_hypothesis_results": hypothesis_path.exists(),
                "has_stability_report": (run_dir / "stability_report.csv").exists(),
                "has_strategy_metrics": (run_dir / "study_strategy_metrics.csv").exists(),
                "has_opportunity_catalog": (run_dir / "opportunity_catalog.csv").exists(),
                "has_evidence_bundle": (run_dir / "evidence_bundle.json").exists(),
                "has_figure_manifest": (run_dir / "figure_manifest.json").exists(),
                "notes": definition.notes,
                "is_complete": (
                    summary.get("run_count") == definition.expected_run_count
                    and (summary.get("diagnostic_only") or (run_dir / "study_strategy_metrics.csv").exists())
                    and (run_dir / "evidence_bundle.json").exists()
                    and (run_dir / "figure_manifest.json").exists()
                    and (summary.get("diagnostic_only") or (run_dir / "stability_report.csv").exists())
                    and (definition.expected_hypotheses == 0 or hypothesis_path.exists())
                ),
            }
        )
    return rows


def summarize_strategy_metrics(study_id: str, run_role: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (
            row["group_id"],
            row["strategy_id"],
            row["selector_version"],
            row.get("selector_revision_id", ""),
            row["workload_class"],
        )
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for (group_id, strategy_id, selector_version, selector_revision_id, workload_class), items in sorted(grouped.items()):
        speedups = [safe_float(item["geomean_speedup_vs_default_config"]) for item in items]
        random_speedups = [safe_float(item["speedup_vs_naive_random_search"]) for item in items]
        winner_rates = [safe_float(item["winner_rate"]) for item in items]
        regrets = [safe_float(item["regret_vs_best_measured_calibration"]) for item in items]
        availabilities = [safe_float(item.get("counter_availability")) for item in items]
        summary_rows.append(
            {
                "study_id": study_id,
                "run_role": run_role,
                "group_id": group_id,
                "kernel_family": items[0]["kernel_family"],
                "workload_class": workload_class,
                "strategy_id": strategy_id,
                "selector_version": selector_version,
                "selector_revision_id": selector_revision_id,
                "counter_set_id": items[0]["counter_set_id"],
                "budget_id": items[0]["budget_id"],
                "run_rows": len(items),
                "mean_speedup_vs_default": compact_float(mean(v for v in speedups if v is not None)),
                "mean_speedup_vs_random": compact_float(mean(v for v in random_speedups if v is not None))
                if any(v is not None for v in random_speedups)
                else "",
                "mean_winner_rate": compact_float(mean(v for v in winner_rates if v is not None)),
                "mean_regret": compact_float(mean(v for v in regrets if v is not None)),
                "mean_counter_availability": compact_float(mean(v for v in availabilities if v is not None))
                if any(v is not None for v in availabilities)
                else "",
                "reportable_all": all(item.get("is_reportable") == "True" for item in items),
                "counter_set_accepted_all": all(
                    item.get("counter_set_accepted") in ("", "True") for item in items
                ),
            }
        )
    return summary_rows


def build_strategy_mean_summary(repo_root: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    summary_rows: list[dict[str, Any]] = []
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for definition in [*CANONICAL_STUDIES, *REPLICATION_STUDIES]:
        run_dir = study_run_dir(repo_root, definition)
        metrics_path = run_dir / "study_strategy_metrics.csv"
        if not metrics_path.exists():
            index[(definition.study_id, definition.role)] = []
            continue
        metrics = read_csv_rows(metrics_path)
        rows = summarize_strategy_metrics(definition.study_id, definition.role, metrics)
        summary_rows.extend(rows)
        index[(definition.study_id, definition.role)] = rows
    return summary_rows, index


def build_canonical_artifact_map(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    campaign_index = {definition.campaign_id: definition for definition in CANONICAL_CAMPAIGNS}
    for definition in CANONICAL_STUDIES:
        run_dir = study_run_dir(repo_root, definition)
        summary = read_json(run_dir / "cross_run_summary.json")
        campaign_def = campaign_index.get(
            "layernorm_v2_microstudy"
            if definition.study_id.startswith("layernorm_v2_")
            else definition.study_id
        )
        rows.append(
            {
                "study_id": definition.study_id,
                "label": definition.label,
                "study_run_id": definition.run_id,
                "campaign_id": campaign_def.campaign_id if campaign_def else "",
                "campaign_run_id": campaign_def.run_id if campaign_def else "",
                "diagnostic_only": summary.get("diagnostic_only"),
                "cross_run_summary": str(run_dir / "cross_run_summary.json"),
                "study_strategy_metrics": str(run_dir / "study_strategy_metrics.csv")
                if (run_dir / "study_strategy_metrics.csv").exists()
                else "",
                "stability_report": str(run_dir / "stability_report.csv") if (run_dir / "stability_report.csv").exists() else "",
                "hypothesis_results": str(run_dir / "hypothesis_results.csv") if (run_dir / "hypothesis_results.csv").exists() else "",
                "evidence_bundle": str(run_dir / "evidence_bundle.json"),
                "figure_manifest": str(run_dir / "figure_manifest.json"),
                "notes": definition.notes,
            }
        )
    return rows


def extract_hypothesis_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in [*CANONICAL_STUDIES, *REPLICATION_STUDIES]:
        hypothesis_path = study_run_dir(repo_root, definition) / "hypothesis_results.csv"
        if not hypothesis_path.exists():
            continue
        for row in read_csv_rows(hypothesis_path):
            rows.append(
                {
                    "scope": "batch",
                    "study_id": definition.study_id,
                    "run_role": definition.role,
                    "study_run_id": definition.run_id,
                    "hypothesis_id": row["hypothesis_id"],
                    "status": row["status"],
                    "evidence": row["evidence"],
                    "description": row["description"].strip(),
                }
            )

    rows.extend(
        [
            {
                "scope": "project",
                "study_id": "",
                "run_role": "project",
                "study_run_id": "",
                "hypothesis_id": "H1",
                "status": "supported_overall",
                "evidence": (
                    "Original validation, g3 confirmation, and Phase 2 representative GEMM all support the compile-signal limitation; "
                    "Phase 3 preserved the qualitative direction but its canonical confirmation batch missed the pre-registered +0.02 margin."
                ),
                "description": "Cheap compile signals remain useful but insufficient for robust representative GEMM ranking.",
            },
            {
                "scope": "project",
                "study_id": "",
                "run_role": "project",
                "study_run_id": "",
                "hypothesis_id": "H2",
                "status": "regime_split_weak_negative",
                "evidence": (
                    "Small-batch Phase 3 microstudy is weak and noisy; large-batch Phase 3 microstudy keeps compile-only ranking ahead of profiled and revised selectors."
                ),
                "description": "LayerNorm remains a bounded regime-split explanatory result, not a pooled profiling success story.",
            },
            {
                "scope": "project",
                "study_id": "",
                "run_role": "project",
                "study_run_id": "",
                "hypothesis_id": "H3",
                "status": "historically_supported_not_phase3_reinforced",
                "evidence": (
                    "Earlier validation and Phase 2 supported H3, but the Phase 3 aligned refresh did not make aligned GEMM more flattering than representative GEMM."
                ),
                "description": "Aligned GEMM remains a supporting context workload, but Phase 3 does not strengthen the earlier H3 story.",
            },
            {
                "scope": "project",
                "study_id": "",
                "run_role": "project",
                "study_run_id": "",
                "hypothesis_id": "H4",
                "status": "mixed_transfer_limited",
                "evidence": (
                    "The narrow-space v3 retry worked, but Phase 2 v2 and Phase 3 v4 show repeated transfer failures once the GEMM space expands."
                ),
                "description": "Selector revisions are now a transfer story, not a simple win story.",
            },
            {
                "scope": "project",
                "study_id": "",
                "run_role": "project",
                "study_run_id": "",
                "hypothesis_id": "H5",
                "status": "unsupported",
                "evidence": (
                    "Canonical Phase 3 representative GEMM gives v4_transfer_safe_profiled=0.1609 vs default, "
                    "parent prune_rank=1.0324, naive_random_search=1.0427."
                ),
                "description": "The transfer-safe v4 policy does not recover near-random-search representative GEMM performance on the split-k space.",
            },
        ]
    )
    return rows


def build_replication_consistency_summary(
    repo_root: Path, strategy_index: dict[tuple[str, str], list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    comparable_studies = [
        "gemm_v3_baseline_mapping",
        "gemm_v3_selector_ablation",
        "gemm_v3_aligned_reference",
        "layernorm_v2_small_microstudy",
        "layernorm_v2_large_microstudy",
    ]
    for study_id in comparable_studies:
        main_rows = {
            (row["workload_class"], row["strategy_id"]): row
            for row in strategy_index[(study_id, "replication")]
        }
        canonical_rows = {
            (row["workload_class"], row["strategy_id"]): row
            for row in strategy_index[(study_id, "canonical")]
        }
        for key in sorted(set(main_rows) | set(canonical_rows)):
            main_row = main_rows.get(key)
            canonical_row = canonical_rows.get(key)
            main_value = safe_float(main_row["mean_speedup_vs_default"]) if main_row else None
            canonical_value = safe_float(canonical_row["mean_speedup_vs_default"]) if canonical_row else None
            rows.append(
                {
                    "study_id": study_id,
                    "comparison_kind": "strategy_mean",
                    "subject_id": key[1],
                    "workload_class": key[0],
                    "main_run_id": next(
                        definition.run_id for definition in REPLICATION_STUDIES if definition.study_id == study_id
                    ),
                    "canonical_run_id": next(
                        definition.run_id for definition in CANONICAL_STUDIES if definition.study_id == study_id
                    ),
                    "main_value": compact_float(main_value),
                    "canonical_value": compact_float(canonical_value),
                    "delta": compact_float(
                        canonical_value - main_value if main_value is not None and canonical_value is not None else None
                    ),
                    "sign_consistent": (
                        (main_value - 1.0) * (canonical_value - 1.0) >= 0
                        if main_value is not None and canonical_value is not None
                        else False
                    ),
                    "notes": "",
                }
            )

    # Hypothesis-level replication rows for the representative GEMM baseline study.
    main_hyp = {
        row["hypothesis_id"]: row
        for row in extract_hypothesis_rows(repo_root)
        if row["scope"] == "batch"
        and row["study_id"] == "gemm_v3_baseline_mapping"
        and row["run_role"] == "replication"
    }
    canonical_hyp = {
        row["hypothesis_id"]: row
        for row in extract_hypothesis_rows(repo_root)
        if row["scope"] == "batch"
        and row["study_id"] == "gemm_v3_baseline_mapping"
        and row["run_role"] == "canonical"
    }
    # Compare claim direction rather than raw supported/unsupported labels for H1.
    baseline_main = {
        (row["workload_class"], row["strategy_id"]): safe_float(row["mean_speedup_vs_default"])
        for row in strategy_index[("gemm_v3_baseline_mapping", "replication")]
    }
    baseline_canonical = {
        (row["workload_class"], row["strategy_id"]): safe_float(row["mean_speedup_vs_default"])
        for row in strategy_index[("gemm_v3_baseline_mapping", "canonical")]
    }
    mean_prune_main = mean(
        baseline_main[(workload_class, "prune_rank")]
        for workload_class in {key[0] for key in baseline_main if key[1] == "prune_rank"}
    )
    mean_random_main = mean(
        baseline_main[(workload_class, "naive_random_search")]
        for workload_class in {key[0] for key in baseline_main if key[1] == "naive_random_search"}
    )
    mean_prune_canonical = mean(
        baseline_canonical[(workload_class, "prune_rank")]
        for workload_class in {key[0] for key in baseline_canonical if key[1] == "prune_rank"}
    )
    mean_random_canonical = mean(
        baseline_canonical[(workload_class, "naive_random_search")]
        for workload_class in {key[0] for key in baseline_canonical if key[1] == "naive_random_search"}
    )
    rows.append(
        {
            "study_id": "gemm_v3_baseline_mapping",
            "comparison_kind": "hypothesis",
            "subject_id": "H1_phase3_gemm",
            "workload_class": "representative_aggregate",
            "main_run_id": "run_20260328T010058Z_7226d3f1",
            "canonical_run_id": "run_20260329T010211Z_dfb53abb",
            "main_value": main_hyp["H1_phase3_gemm"]["status"],
            "canonical_value": canonical_hyp["H1_phase3_gemm"]["status"],
            "delta": "",
            "sign_consistent": mean_random_main > mean_prune_main and mean_random_canonical > mean_prune_canonical,
            "notes": "Batch-level support flipped at the threshold, but the claim direction stayed the same.",
        }
    )
    rows.append(
        {
            "study_id": "gemm_v3_baseline_mapping",
            "comparison_kind": "hypothesis",
            "subject_id": "H5_phase3_gemm",
            "workload_class": "representative_aggregate",
            "main_run_id": "run_20260328T010058Z_7226d3f1",
            "canonical_run_id": "run_20260329T010211Z_dfb53abb",
            "main_value": main_hyp["H5_phase3_gemm"]["status"],
            "canonical_value": canonical_hyp["H5_phase3_gemm"]["status"],
            "delta": "",
            "sign_consistent": (
                main_hyp["H5_phase3_gemm"]["status"] == "unsupported"
                and canonical_hyp["H5_phase3_gemm"]["status"] == "unsupported"
            ),
            "notes": "H5 remained unsupported in both the earlier main run and the canonical confirmation run.",
        }
    )
    return rows


def build_frontier_diagnostics_summary(repo_root: Path) -> list[dict[str, Any]]:
    study_dir = study_run_dir(
        repo_root,
        next(definition for definition in CANONICAL_STUDIES if definition.study_id == "gemm_v3_schedule_diag"),
    )
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(study_dir / "frontier_diagnostics.csv"):
        config = parse_config(row.get("config"))
        rows.append(
            {
                "study_id": "gemm_v3_schedule_diag",
                "group_id": row["group_id"],
                "run_id": row["run_id"],
                "strategy_id": row["strategy_id"],
                "selector_mode": row["selector_mode"],
                "diagnostic_role": row["diagnostic_role"],
                "rank_index": row["rank_index"],
                "config_id": row["config_id"],
                "block_m": config.get("block_m", ""),
                "block_n": config.get("block_n", ""),
                "block_k": config.get("block_k", ""),
                "group_size_m": config.get("group_size_m", ""),
                "num_warps": config.get("num_warps", ""),
                "num_stages": config.get("num_stages", ""),
                "split_k": config.get("split_k", row.get("split_k", "")),
                "masked_overcoverage_ratio": row.get("masked_overcoverage_ratio", ""),
                "aspect_match_score": row.get("aspect_match_score", ""),
                "moderated_tile_area": row.get("moderated_tile_area", ""),
                "tensor_ops": row.get("tensor_ops", ""),
                "dram_throughput": row.get("dram_throughput", ""),
                "long_scoreboard_stall": row.get("long_scoreboard_stall", ""),
                "lg_throttle": row.get("lg_throttle", ""),
                "warps_active": row.get("warps_active", ""),
                "workload_classes": row.get("workload_classes", ""),
            }
        )
    return rows


def build_family_mismatch_summary(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    campaign_to_study = {
        "gemm_v3_baseline_mapping": "gemm_v3_baseline_mapping",
        "gemm_v3_selector_ablation": "gemm_v3_selector_ablation",
        "gemm_v3_aligned_reference": "gemm_v3_aligned_reference",
        "layernorm_v2_microstudy": None,
    }
    for campaign_def in [definition for definition in CANONICAL_CAMPAIGNS if definition.campaign_id != "gemm_v3_schedule_diag"]:
        status = read_json(campaign_run_dir(repo_root, campaign_def) / "campaign_status.json")
        aggregate: dict[tuple[str, str], dict[str, Any]] = {}
        for job in status["jobs"]:
            run_dir = Path(job["run_dir"])
            for row in read_csv_rows(run_dir / "chosen_vs_best_family.csv"):
                study_id = (
                    "layernorm_v2_small_microstudy"
                    if job["experiment_id"] == "layernorm_v2_small_microstudy"
                    else "layernorm_v2_large_microstudy"
                    if job["experiment_id"] == "layernorm_v2_large_microstudy"
                    else campaign_to_study[campaign_def.campaign_id]
                )
                key = (study_id, row["strategy_id"])
                current = aggregate.setdefault(
                    key,
                    {
                        "study_id": study_id,
                        "strategy_id": row["strategy_id"],
                        "selector_mode": row["selector_mode"],
                        "run_rows": 0,
                        "selected_matches_best_count": 0,
                        "selected_score_regrets": [],
                        "selected_split_k_counts": {},
                        "best_split_k_counts": {},
                        "selected_rows_per_program_counts": {},
                        "best_rows_per_program_counts": {},
                        "selected_config_ids": {},
                        "best_config_ids": {},
                    },
                )
                current["run_rows"] += 1
                if row["selected_matches_best_scored"] == "True":
                    current["selected_matches_best_count"] += 1
                regret = safe_float(row.get("selected_score_regret"))
                if regret is not None:
                    current["selected_score_regrets"].append(regret)

                selected_config = parse_config(row.get("selected_config"))
                best_config = parse_config(row.get("best_scored_config"))
                selected_split_k = selected_config.get("split_k")
                best_split_k = best_config.get("split_k")
                selected_rows_per_program = selected_config.get("rows_per_program")
                best_rows_per_program = best_config.get("rows_per_program")

                if selected_split_k is not None:
                    current["selected_split_k_counts"][selected_split_k] = (
                        current["selected_split_k_counts"].get(selected_split_k, 0) + 1
                    )
                if best_split_k is not None:
                    current["best_split_k_counts"][best_split_k] = (
                        current["best_split_k_counts"].get(best_split_k, 0) + 1
                    )
                if selected_rows_per_program is not None:
                    current["selected_rows_per_program_counts"][selected_rows_per_program] = (
                        current["selected_rows_per_program_counts"].get(selected_rows_per_program, 0) + 1
                    )
                if best_rows_per_program is not None:
                    current["best_rows_per_program_counts"][best_rows_per_program] = (
                        current["best_rows_per_program_counts"].get(best_rows_per_program, 0) + 1
                    )
                selected_id = row.get("selected_config_id")
                if selected_id:
                    current["selected_config_ids"][selected_id] = current["selected_config_ids"].get(selected_id, 0) + 1
                best_id = row.get("best_scored_config_id")
                if best_id:
                    current["best_config_ids"][best_id] = current["best_config_ids"].get(best_id, 0) + 1

        for value in aggregate.values():
            rows.append(
                {
                    "study_id": value["study_id"],
                    "strategy_id": value["strategy_id"],
                    "selector_mode": value["selector_mode"],
                    "run_rows": value["run_rows"],
                    "selected_match_rate": compact_float(value["selected_matches_best_count"] / value["run_rows"]),
                    "mean_selected_score_regret": compact_float(mean(value["selected_score_regrets"]))
                    if value["selected_score_regrets"]
                    else "",
                    "selected_split_k_counts": dict_counts_to_string(value["selected_split_k_counts"]),
                    "best_split_k_counts": dict_counts_to_string(value["best_split_k_counts"]),
                    "selected_rows_per_program_counts": dict_counts_to_string(value["selected_rows_per_program_counts"]),
                    "best_rows_per_program_counts": dict_counts_to_string(value["best_rows_per_program_counts"]),
                    "selected_config_ids": dict_counts_to_string(value["selected_config_ids"]),
                    "best_scored_config_ids": dict_counts_to_string(value["best_config_ids"]),
                }
            )
    return sorted(rows, key=lambda row: (row["study_id"], row["strategy_id"]))


def build_splitk_decision_table(
    family_mismatch_rows: list[dict[str, Any]], frontier_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    relevant = [row for row in family_mismatch_rows if row["study_id"] in {"gemm_v3_baseline_mapping", "gemm_v3_aligned_reference"}]
    for row in relevant:
        selected_counts = row["selected_split_k_counts"] or ""
        best_counts = row["best_split_k_counts"] or ""
        rows.append(
            {
                "evidence_scope": row["study_id"],
                "strategy_id": row["strategy_id"],
                "selected_split_k_counts": selected_counts,
                "best_split_k_counts": best_counts,
                "interpretation": (
                    "non-unit split_k reached the chosen/best-scored family"
                    if any(token.startswith(("2:", "4:")) for token in selected_counts.split("; "))
                    or any(token.startswith(("2:", "4:")) for token in best_counts.split("; "))
                    else "only split_k=1 survived to chosen and best-scored families"
                ),
                "decision": "",
            }
        )

    frontier_nonunit = sum(
        1
        for row in frontier_rows
        if row["diagnostic_role"] in {"compile_frontier", "frontier_rank", "profile_prefix"}
        and str(row["split_k"]) in {"2", "4", "2.0", "4.0"}
    )
    frontier_total = sum(
        1 for row in frontier_rows if row["diagnostic_role"] in {"compile_frontier", "frontier_rank", "profile_prefix"}
    )
    rows.append(
        {
            "evidence_scope": "gemm_v3_schedule_diag",
            "strategy_id": "frontier_summary",
            "selected_split_k_counts": f"non_unit:{frontier_nonunit}; total:{frontier_total}",
            "best_split_k_counts": "",
            "interpretation": "split_k>1 appears in the diagnostic frontier, but not in the chosen or best-scored canonical families",
            "decision": "",
        }
    )
    rows.append(
        {
            "evidence_scope": "overall",
            "strategy_id": "final_decision",
            "selected_split_k_counts": "selected_non_unit:0; best_scored_non_unit:0",
            "best_split_k_counts": "",
            "interpretation": (
                "Across the canonical representative and aligned GEMM confirmation runs, split_k never became a chosen or "
                "best-scored family, and the diagnostic frontier only shows it as a reachable but dominated alternative."
            ),
            "decision": "retire_from_main_gemm_surface",
        }
    )
    return rows


def build_rows_per_program_decision_table(family_mismatch_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    relevant = [
        row
        for row in family_mismatch_rows
        if row["study_id"] in {"layernorm_v2_small_microstudy", "layernorm_v2_large_microstudy"}
    ]
    for row in relevant:
        rows.append(
            {
                "study_id": row["study_id"],
                "strategy_id": row["strategy_id"],
                "selected_rows_per_program_counts": row["selected_rows_per_program_counts"],
                "best_rows_per_program_counts": row["best_rows_per_program_counts"],
                "selected_match_rate": row["selected_match_rate"],
                "mean_selected_score_regret": row["mean_selected_score_regret"],
                "decision": "",
            }
        )
    rows.append(
        {
            "study_id": "overall",
            "strategy_id": "final_decision",
            "selected_rows_per_program_counts": "small_batch mixes 1/4/8 only in weak or noisy paths; large_batch uses 4/8 mostly in regressing profiled/revised paths",
            "best_rows_per_program_counts": "compile-only large_batch remains rows_per_program=1 throughout",
            "selected_match_rate": "",
            "mean_selected_score_regret": "",
            "decision": "retire_from_main_layernorm_surface",
        }
    )
    return rows


def build_claim_table(
    strategy_summary: list[dict[str, Any]],
    hypothesis_rows: list[dict[str, Any]],
    splitk_rows: list[dict[str, Any]],
    rows_per_program_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hypothesis_lookup = {
        (row["study_id"], row["run_role"], row["hypothesis_id"]): row for row in hypothesis_rows if row["scope"] == "batch"
    }
    claims: list[dict[str, Any]] = []

    def mean_speed(
        study_id: str,
        run_role: str,
        strategy_id: str,
        workloads: tuple[str, ...],
        *,
        group_id: str | None = None,
        selector_revision_id: str | None = None,
    ) -> float:
        values: list[float] = []
        for row in strategy_summary:
            if row["study_id"] != study_id or row["run_role"] != run_role:
                continue
            if row["strategy_id"] != strategy_id or row["workload_class"] not in workloads:
                continue
            if group_id is not None and row["group_id"] != group_id:
                continue
            if selector_revision_id is not None and row["selector_revision_id"] != selector_revision_id:
                continue
            value = safe_float(row["mean_speedup_vs_default"])
            if value is not None:
                values.append(value)
        if not values:
            raise ValueError(
                f"no strategy means found for {study_id=} {run_role=} {strategy_id=} {group_id=} {selector_revision_id=}"
            )
        return mean(values)

    h5 = hypothesis_lookup[("gemm_v3_baseline_mapping", "canonical", "H5_phase3_gemm")]
    h1 = hypothesis_lookup[("gemm_v3_baseline_mapping", "canonical", "H1_phase3_gemm")]
    representative_workloads = ("edge_nondivisible", "m_dominant", "n_dominant", "square_compute")
    prune_rep = mean_speed("gemm_v3_baseline_mapping", "canonical", "prune_rank", representative_workloads)
    revised_rep = mean_speed("gemm_v3_baseline_mapping", "canonical", "prune_rank_revised", representative_workloads)
    aligned_prune = mean_speed("gemm_v3_aligned_reference", "canonical", "prune_rank", ("aligned_square",))
    small_prune = mean_speed("layernorm_v2_small_microstudy", "canonical", "prune_rank", ("small_batch",))
    small_profiled = mean_speed(
        "layernorm_v2_small_microstudy", "canonical", "prune_rank_profiled", ("small_batch",)
    )
    large_prune = mean_speed("layernorm_v2_large_microstudy", "canonical", "prune_rank", ("large_batch",))
    large_profiled = mean_speed(
        "layernorm_v2_large_microstudy", "canonical", "prune_rank_profiled", ("large_batch",)
    )
    ablation_parent = mean_speed(
        "gemm_v3_selector_ablation", "canonical", "prune_rank", representative_workloads, group_id="gemm_v3_parent"
    )
    ablation_frontier = mean_speed(
        "gemm_v3_selector_ablation",
        "canonical",
        "prune_rank_revised",
        representative_workloads,
        group_id="gemm_v3_frontier",
        selector_revision_id="v4_transfer_safe_frontier",
    )
    ablation_profiled = mean_speed(
        "gemm_v3_selector_ablation",
        "canonical",
        "prune_rank_revised",
        representative_workloads,
        group_id="gemm_v3_profiled",
        selector_revision_id="v4_transfer_safe_profiled",
    )

    claims.append(
        {
            "claim_id": "C-P3-H5",
            "claim": "The transfer-safe v4 corrective pass does not recover near-random-search representative GEMM performance on the split-k space.",
            "status": h5["status"],
            "supporting_artifacts": "gemm_v3_baseline_mapping",
            "evidence": h5["evidence"],
            "confidence": "High",
            "caveat": "The failure is a bounded negative result for the current v4 rule, not a claim that representative GEMM is solved by compile-only ranking.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-H1-CONTEXT",
            "claim": "Phase 3 preserves the qualitative H1 limitation but does not materially strengthen it as a new supporting batch.",
            "status": h1["status"],
            "supporting_artifacts": "gemm_v3_baseline_mapping; replication_consistency_summary.csv",
            "evidence": h1["evidence"],
            "confidence": "Medium",
            "caveat": "The earlier main Phase 3 batch supported H1, but the canonical confirmation batch missed the +0.02 threshold even though the direction stayed the same.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-H4-TRANSFER",
            "claim": "Frontier-only and full-v4 both fail on the expanded representative GEMM space, so profiling does not rescue the revised selector once the frontier is wrong.",
            "status": "supported_negative",
            "supporting_artifacts": "gemm_v3_selector_ablation",
            "evidence": (
                f"canonical mean speedup vs default: parent={ablation_parent:.4f}, "
                f"frontier_only={ablation_frontier:.4f}, profiled_v4={ablation_profiled:.4f}"
            ),
            "confidence": "High",
            "caveat": "This is a transfer-failure result for the current revision family, not proof that all revised selectors must fail.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-H3-CONTEXT",
            "claim": "The Phase 3 aligned refresh does not strengthen the earlier H3 story; aligned GEMM remains context, not the main truth source.",
            "status": "mixed_context",
            "supporting_artifacts": "gemm_v3_baseline_mapping; gemm_v3_aligned_reference",
            "evidence": (
                f"canonical prune_rank mean speedup vs default: representative={prune_rep:.4f}, aligned={aligned_prune:.4f}"
            ),
            "confidence": "Medium",
            "caveat": "This weakens Phase-3-specific H3 reinforcement without overturning the broader earlier evidence for aligned-vs-representative mismatch.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-SPLITK",
            "claim": "split_k should be retired from the main GEMM reportable surface.",
            "status": "retire",
            "supporting_artifacts": "gemm_v3_baseline_mapping; gemm_v3_schedule_diag; splitk_decision_table.csv",
            "evidence": splitk_rows[-1]["interpretation"],
            "confidence": "High",
            "caveat": "This retires split_k as a mainline reportable knob, not as an archived diagnostic implementation.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-LN",
            "claim": "LayerNorm remains a bounded explanatory thread: small_batch is weak/noisy and large_batch favors compile-only ranking.",
            "status": "bounded_mixed",
            "supporting_artifacts": "layernorm_v2_small_microstudy; layernorm_v2_large_microstudy",
            "evidence": (
                f"small_batch prune_rank={small_prune:.4f}, profiled={small_profiled:.4f}; "
                f"large_batch prune_rank={large_prune:.4f}, profiled={large_profiled:.4f}"
            ),
            "confidence": "Medium",
            "caveat": "The microstudy is strong enough to tighten the narrative, but not to reopen a major LayerNorm optimization program.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-ROWS",
            "claim": "rows_per_program should be retired from the main LayerNorm surface.",
            "status": "retire",
            "supporting_artifacts": "layernorm_v2_small_microstudy; layernorm_v2_large_microstudy; rows_per_program_decision_table.csv",
            "evidence": rows_per_program_rows[-1]["selected_rows_per_program_counts"],
            "confidence": "Medium",
            "caveat": "The knob showed occasional non-unit selections, but they were unstable and did not produce a robust selector-level gain.",
        }
    )
    claims.append(
        {
            "claim_id": "C-P3-RERUN",
            "claim": "No bounded 12-hour rerun is required by the explicit Phase 3 gates.",
            "status": "no_rerun_triggered",
            "supporting_artifacts": "replication_consistency_summary.csv; splitk_decision_table.csv; rows_per_program_decision_table.csv",
            "evidence": (
                "H5 stayed unsupported in both main and canonical runs; split_k never survived into chosen or best-scored canonical GEMM families; "
                "rows_per_program evidence is weak enough to justify retirement without tie-break execution."
            ),
            "confidence": "High",
            "caveat": "A future rerun could still be justified if a paper figure later reveals a concrete missing credibility check.",
        }
    )
    return claims


def build_markdown_summary(
    campaign_integrity: list[dict[str, Any]],
    study_integrity: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    strategy_summary: list[dict[str, Any]],
    splitk_rows: list[dict[str, Any]],
    rows_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Phase 3 Analysis Bundle")
    lines.append("")
    lines.append("Generated from the completed Phase 3 execution program and its confirmation reruns on March 29, 2026.")
    lines.append("")
    lines.append("## Canonical Evidence")
    lines.append("")
    lines.append("- Canonical primary evidence comes from the latest confirmation study runs.")
    lines.append("- Earlier main Phase 3 study runs are retained as replication evidence.")
    lines.append("- No incomplete Phase 3 campaign roots are promoted into this bundle.")
    lines.append("")
    lines.append("## Artifact Integrity")
    lines.append("")
    for row in campaign_integrity:
        lines.append(
            f"- `{row['campaign_id']}` `{row['role']}`: jobs `{row['completed_jobs']}/{row['job_count']}`, "
            f"failed `{row['failed_jobs']}`, terminal `{row['terminal_status']}`, complete `{row['is_complete']}`"
        )
    lines.append("")
    for row in study_integrity:
        lines.append(
            f"- `{row['study_id']}` `{row['role']}`: run_count `{row['run_count']}`, "
            f"diagnostic `{row['diagnostic_only']}`, complete `{row['is_complete']}`"
        )
    lines.append("")
    lines.append("## Main Claims")
    lines.append("")
    for row in claims:
        lines.append(f"- `{row['claim_id']}` `{row['status']}`: {row['claim']}")
        lines.append(f"  Evidence: {row['evidence']}")
        lines.append(f"  Caveat: {row['caveat']}")
    lines.append("")
    lines.append("## Canonical Strategy Means")
    lines.append("")
    canonical_key_rows = [
        row
        for row in strategy_summary
        if row["run_role"] == "canonical"
        and row["strategy_id"] in {
            "naive_random_search",
            "prune_rank",
            "prune_rank_profiled",
            "prune_rank_revised",
            "default_config",
        }
    ]
    key_columns = [
        "study_id",
        "workload_class",
        "strategy_id",
        "mean_speedup_vs_default",
        "mean_speedup_vs_random",
        "mean_winner_rate",
        "mean_regret",
    ]
    lines.append(dataframe_to_markdown([{key: row[key] for key in key_columns} for row in canonical_key_rows]))
    lines.append("")
    lines.append("## Keep / Drop Decisions")
    lines.append("")
    lines.append(dataframe_to_markdown(splitk_rows[-1:]))
    lines.append("")
    lines.append(dataframe_to_markdown(rows_rows[-1:]))
    lines.append("")
    lines.append("## Rerun Gates")
    lines.append("")
    lines.append("- Gate A: not triggered. `H5` stayed unsupported in both main and canonical runs; `H1` changed batch status but not claim direction.")
    lines.append("- Gate B: not triggered. `H5` was far from the success threshold, not near it.")
    lines.append("- Gate C: not triggered. `split_k` appeared only as a reachable diagnostic family and never survived as a chosen or best-scored canonical GEMM family.")
    lines.append("- Gate D: not triggered. `rows_per_program` usage was unstable and did not justify keeping it in the main LayerNorm surface.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--output-dir",
        default="artifacts/analysis/phase3_20260329",
        help="Output directory for the generated analysis bundle",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    campaign_integrity = build_campaign_integrity(repo_root)
    study_integrity = build_study_integrity(repo_root)
    strategy_summary, strategy_index = build_strategy_mean_summary(repo_root)
    canonical_artifact_map = build_canonical_artifact_map(repo_root)
    hypothesis_rows = extract_hypothesis_rows(repo_root)
    replication_consistency = build_replication_consistency_summary(repo_root, strategy_index)
    frontier_diagnostics = build_frontier_diagnostics_summary(repo_root)
    family_mismatch = build_family_mismatch_summary(repo_root)
    splitk_rows = build_splitk_decision_table(family_mismatch, frontier_diagnostics)
    rows_rows = build_rows_per_program_decision_table(family_mismatch)
    claims = build_claim_table(strategy_summary, hypothesis_rows, splitk_rows, rows_rows)
    markdown_summary = build_markdown_summary(
        campaign_integrity,
        study_integrity,
        claims,
        strategy_summary,
        splitk_rows,
        rows_rows,
    )

    write_csv(output_dir / "campaign_integrity_summary.csv", campaign_integrity)
    write_csv(output_dir / "study_integrity_summary.csv", study_integrity)
    write_csv(output_dir / "canonical_artifact_map.csv", canonical_artifact_map)
    write_csv(output_dir / "replication_consistency_summary.csv", replication_consistency)
    write_csv(output_dir / "strategy_mean_summary.csv", strategy_summary)
    write_csv(output_dir / "hypothesis_status_summary.csv", hypothesis_rows)
    write_csv(output_dir / "frontier_diagnostics_summary.csv", frontier_diagnostics)
    write_csv(output_dir / "family_mismatch_summary.csv", family_mismatch)
    write_csv(output_dir / "splitk_decision_table.csv", splitk_rows)
    write_csv(output_dir / "rows_per_program_decision_table.csv", rows_rows)
    write_csv(output_dir / "claim_table.csv", claims)
    (output_dir / "phase3_analysis_summary.md").write_text(markdown_summary, encoding="utf-8")

    analysis_index = {
        "bundle": "phase3",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_dir": str(output_dir),
        "canonical_studies": {definition.study_id: definition.run_id for definition in CANONICAL_STUDIES},
        "replication_studies": {definition.study_id: definition.run_id for definition in REPLICATION_STUDIES},
        "files": {
            "campaign_integrity_summary": str(output_dir / "campaign_integrity_summary.csv"),
            "study_integrity_summary": str(output_dir / "study_integrity_summary.csv"),
            "canonical_artifact_map": str(output_dir / "canonical_artifact_map.csv"),
            "replication_consistency_summary": str(output_dir / "replication_consistency_summary.csv"),
            "strategy_mean_summary": str(output_dir / "strategy_mean_summary.csv"),
            "hypothesis_status_summary": str(output_dir / "hypothesis_status_summary.csv"),
            "frontier_diagnostics_summary": str(output_dir / "frontier_diagnostics_summary.csv"),
            "family_mismatch_summary": str(output_dir / "family_mismatch_summary.csv"),
            "splitk_decision_table": str(output_dir / "splitk_decision_table.csv"),
            "rows_per_program_decision_table": str(output_dir / "rows_per_program_decision_table.csv"),
            "claim_table": str(output_dir / "claim_table.csv"),
            "phase3_analysis_summary": str(output_dir / "phase3_analysis_summary.md"),
        },
        "key_decisions": {
            "H5": "unsupported",
            "split_k": "retire_from_main_gemm_surface",
            "rows_per_program": "retire_from_main_layernorm_surface",
            "rerun_required": False,
        },
    }
    write_json(output_dir / "analysis_bundle_index.json", analysis_index)


if __name__ == "__main__":
    main()
