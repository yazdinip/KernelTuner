#!/usr/bin/env python3
"""Build the final paper-evidence bundle from the completed research program."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

FINAL_BUNDLE_DATE = "20260330"

CANONICAL_ANALYSIS_BUNDLES = {
    "phase2": "artifacts/analysis/phase2_20260327/analysis_bundle_index.json",
    "phase3": "artifacts/analysis/phase3_20260329/analysis_bundle_index.json",
}

CANONICAL_FINAL_STUDIES = {
    "gemm_final_baseline_mapping": "artifacts/studies/gemm_final_baseline_mapping/run_20260330T014317Z_359c1904",
    "gemm_final_selector_ablation": "artifacts/studies/gemm_final_selector_ablation/run_20260330T023529Z_7c800187",
}

CANONICAL_FINAL_CAMPAIGNS = {
    "gemm_final_baseline_mapping": {
        "path": "artifacts/campaigns/gemm_final_baseline_mapping/run_20260330T003313Z_9e0cdfce",
        "expected_job_count": 12,
    },
    "gemm_final_selector_ablation": {
        "path": "artifacts/campaigns/gemm_final_selector_ablation/run_20260330T014321Z_c4e9fa9d",
        "expected_job_count": 18,
    },
}

CANONICAL_CONTEXT_ARTIFACTS = {
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def resolve(root: Path, relative_path: str) -> Path:
    return root / relative_path


def load_bundle_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing bundle index at {path}")
    return load_json(path)


def bundle_file(index: dict[str, Any], key: str) -> str:
    if "files" in index:
        return index["files"][key]
    return index[key]


def find_required_paths(root: Path, mapping: dict[str, str]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for key, relative in mapping.items():
        path = resolve(root, relative)
        if not path.exists():
            raise FileNotFoundError(f"missing canonical path for {key}: {path}")
        resolved[key] = path
    return resolved


def build_artifact_integrity_summary(
    root: Path,
    phase2_index: dict[str, Any],
    phase3_index: dict[str, Any],
    study_runs: dict[str, Path],
    campaign_runs: dict[str, Path],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [
        {
            "artifact_id": "phase2_bundle",
            "kind": "analysis_bundle",
            "path": phase2_index["output_dir"],
            "complete": True,
            "notes": "Canonical Phase 2 bundle promoted into the final paper package.",
        },
        {
            "artifact_id": "phase3_bundle",
            "kind": "analysis_bundle",
            "path": phase3_index["output_dir"],
            "complete": True,
            "notes": "Canonical Phase 3 bundle promoted into the final paper package.",
        },
    ]

    for campaign_id, metadata in CANONICAL_FINAL_CAMPAIGNS.items():
        run_dir = campaign_runs[campaign_id]
        status = load_json(run_dir / "campaign_status.json")
        rows.append(
            {
                "artifact_id": campaign_id,
                "kind": "campaign",
                "path": str(run_dir),
                "complete": (
                    status.get("job_count") == metadata["expected_job_count"]
                    and status.get("completed_jobs") == metadata["expected_job_count"]
                    and status.get("failed_jobs") == 0
                    and status.get("terminal_status") == "success"
                ),
                "notes": f"expected_jobs={metadata['expected_job_count']}",
            }
        )

    for study_id, run_dir in study_runs.items():
        summary = load_json(run_dir / "cross_run_summary.json")
        rows.append(
            {
                "artifact_id": study_id,
                "kind": "study",
                "path": str(run_dir),
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
                "artifact_id": "gemm_final_aligned_reference",
                "kind": "optional_study",
                "path": "",
                "complete": True,
                "notes": "Optional R6 aligned refresh was gate-skipped; final package uses the canonical Phase 2 aligned reference instead.",
            },
            {
                "artifact_id": "phase3_raw_archive_exclusion",
                "kind": "provenance_rule",
                "path": "/tmp/.../phase3_raw",
                "complete": True,
                "notes": NONCANONICAL_PHASE3_ARCHIVE_NOTE,
            },
            {
                "artifact_id": "superseded_roots_exclusion",
                "kind": "provenance_rule",
                "path": "",
                "complete": True,
                "notes": "The final bundle excludes incomplete or superseded campaign and study roots even when newer runs exist in the same family.",
            },
        ]
    )

    return pd.DataFrame(rows)


def build_final_strategy_summary(
    study_runs: dict[str, Path],
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

    for study_id, run_dir in study_runs.items():
        strategy_metrics = pd.read_csv(run_dir / "study_strategy_metrics.csv")
        summary = (
            strategy_metrics.groupby(
                ["group_id", "strategy_id", "selector_version", "selector_revision_id", "workload_class"],
                dropna=False,
            )
            .agg(
                mean_speedup_vs_default=("geomean_speedup_vs_default_config", "mean"),
                mean_speedup_vs_random=("speedup_vs_naive_random_search", "mean"),
                mean_winner_rate=("winner_rate", "mean"),
                mean_regret=("regret_vs_best_measured_calibration", "mean"),
                run_rows=("run_id", "count"),
            )
            .reset_index()
        )
        summary.insert(0, "study_id", study_id)
        summary.insert(1, "source_bundle", "r6")
        frames.append(summary)

    return pd.concat(frames, ignore_index=True, sort=False)


def _mean_or_none(frame: pd.DataFrame, strategy_id: str, selector_revision_id: str = "") -> float | None:
    subset = frame[frame["strategy_id"] == strategy_id]
    if selector_revision_id:
        subset = subset[subset["selector_revision_id"] == selector_revision_id]
    if subset.empty:
        return None
    return float(subset["geomean_speedup_vs_default_config"].mean())


def build_headline_result_summary(study_runs: dict[str, Path]) -> pd.DataFrame:
    baseline_metrics = pd.read_csv(study_runs["gemm_final_baseline_mapping"] / "study_strategy_metrics.csv")
    baseline_metrics = baseline_metrics[baseline_metrics["group_id"] == "gemm_final_representative"].copy()

    ablation_metrics = pd.read_csv(study_runs["gemm_final_selector_ablation"] / "study_strategy_metrics.csv")

    parent = _mean_or_none(baseline_metrics, "prune_rank")
    random_v = _mean_or_none(baseline_metrics, "naive_random_search")
    profiled = _mean_or_none(baseline_metrics, "prune_rank_revised", "v5_mainline_profiled")
    frontier_ablation = _mean_or_none(
        ablation_metrics[ablation_metrics["group_id"] == "gemm_final_frontier"].copy(),
        "prune_rank_revised",
        "v5_mainline_frontier",
    )

    if parent is None or random_v is None or profiled is None:
        raise ValueError("missing required final headline metrics from gemm_final_baseline_mapping")

    by_seed: dict[str, dict[str, float]] = {"parent": {}, "profiled": {}}
    for (strategy_id, selector_revision_id, seed), frame in baseline_metrics.groupby(
        ["strategy_id", "selector_revision_id", "seed"], dropna=False
    ):
        if strategy_id == "prune_rank":
            by_seed["parent"][str(seed)] = float(frame["geomean_speedup_vs_default_config"].mean())
        elif strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
            by_seed["profiled"][str(seed)] = float(frame["geomean_speedup_vs_default_config"].mean())

    profiled_positive = sum(
        1
        for seed in ("7", "19", "43")
        if by_seed["profiled"].get(seed, float("-inf")) > by_seed["parent"].get(seed, float("inf"))
    )

    profiled_delta = profiled - parent
    profiled_gap = random_v - profiled

    if profiled_delta >= 0.05 and profiled_gap <= 0.03 and profiled_positive >= 2:
        decision = "promote_positive_headline"
    elif profiled_delta >= 0.05:
        decision = "bounded_improvement"
    else:
        decision = "lock_bounded_negative"

    return pd.DataFrame(
        [
            {
                "study_id": "gemm_final_baseline_mapping",
                "parent_mean_speedup_vs_default": parent,
                "random_mean_speedup_vs_default": random_v,
                "frontier_ablation_mean_speedup_vs_default": frontier_ablation,
                "winner_revision_id": "v5_mainline_profiled",
                "winner_mean_speedup_vs_default": profiled,
                "winner_delta_vs_parent": profiled_delta,
                "winner_gap_to_random": profiled_gap,
                "winner_positive_seed_count": profiled_positive,
                "decision": decision,
            }
        ]
    )


def build_canonical_artifact_map(root: Path, study_runs: dict[str, Path]) -> pd.DataFrame:
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
            "path": str(study_runs["gemm_final_baseline_mapping"]),
            "notes": "Final representative GEMM mainline mapping study.",
        },
        {
            "artifact_id": "r6_selector_ablation",
            "role": "mechanism_study",
            "path": str(study_runs["gemm_final_selector_ablation"]),
            "notes": "Final parent/frontier/profiled ablation study.",
        },
        {
            "artifact_id": "phase2_aligned_reference",
            "role": "context_study",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"])),
            "notes": "Canonical aligned-context source because the optional R6 aligned refresh was skipped by gate.",
        },
        {
            "artifact_id": "phase2_representative_mapping",
            "role": "context_study",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
            "notes": "Canonical Phase 2 representative GEMM comparison for aligned-context support.",
        },
        {
            "artifact_id": "phase2_layernorm_small_regime",
            "role": "secondary_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_regime"])),
            "notes": "Canonical Phase 2 LayerNorm small-batch regime source.",
        },
        {
            "artifact_id": "phase2_layernorm_large_regime",
            "role": "secondary_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_regime"])),
            "notes": "Canonical Phase 2 LayerNorm large-batch regime source.",
        },
        {
            "artifact_id": "phase3_layernorm_small_microstudy",
            "role": "secondary_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_microstudy"])),
            "notes": "Canonical Phase 3 LayerNorm small-batch microstudy source.",
        },
        {
            "artifact_id": "phase3_layernorm_large_microstudy",
            "role": "secondary_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_microstudy"])),
            "notes": "Canonical Phase 3 LayerNorm large-batch microstudy source.",
        },
        {
            "artifact_id": "phase3_schedule_diag",
            "role": "diagnostic_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"])),
            "notes": "Canonical chosen-family versus best-family diagnostic source.",
        },
        {
            "artifact_id": "phase3_transfer_mapping",
            "role": "diagnostic_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_baseline_mapping"])),
            "notes": "Canonical Phase 3 transfer-failure source for H5.",
        },
        {
            "artifact_id": "phase3_transfer_ablation",
            "role": "diagnostic_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
            "notes": "Canonical Phase 3 transfer-ablation source for H4/H5.",
        },
        {
            "artifact_id": "h4_narrow_positive_context",
            "role": "diagnostic_context",
            "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["h4_retry_g3"])),
            "notes": "Narrow-space positive revised-selector context retained for the mixed H4 story.",
        },
    ]
    return pd.DataFrame(rows)


def build_figure_source_map(root: Path) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "figure_id": "F1",
                "figure_name": "representative_gemm_headline",
                "source_study": "gemm_final_baseline_mapping",
                "path": str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_baseline_mapping"])),
                "notes": "Final representative GEMM headline figure.",
            },
            {
                "figure_id": "F2",
                "figure_name": "aligned_vs_representative_context",
                "source_study": "gemm_v2_aligned_reference + gemm_v2_baseline_mapping",
                "path": "; ".join(
                    [
                        str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"])),
                        str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                    ]
                ),
                "notes": "Phase 2 aligned-context figure retained because the optional R6 aligned refresh was skipped by gate.",
            },
            {
                "figure_id": "F3",
                "figure_name": "layernorm_regime_split",
                "source_study": "layernorm_v2_small_regime + layernorm_v2_large_regime",
                "path": "; ".join(
                    [
                        str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_regime"])),
                        str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_regime"])),
                    ]
                ),
                "notes": "Phase 2 regime-split LayerNorm figure remains the strongest paper-facing source.",
            },
            {
                "figure_id": "F7",
                "figure_name": "revised_selector_transfer_ablation",
                "source_study": "gemm_final_selector_ablation",
                "path": str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_selector_ablation"])),
                "notes": "Final mainline ablation promoted over earlier v2/v3 selector comparisons.",
            },
            {
                "figure_id": "F11",
                "figure_name": "chosen_family_vs_best_family",
                "source_study": "gemm_v3_schedule_diag",
                "path": str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"])),
                "notes": "Phase 3 diagnostic remains the canonical family-mismatch figure source.",
            },
        ]
    )


def build_final_claim_table(root: Path, headline_summary: pd.DataFrame) -> pd.DataFrame:
    headline = headline_summary.iloc[0]
    decision = str(headline["decision"])
    final_delta = float(headline["winner_delta_vs_parent"])
    final_gap = float(headline["winner_gap_to_random"])
    final_profiled = float(headline["winner_mean_speedup_vs_default"])
    final_parent = float(headline["parent_mean_speedup_vs_default"])
    final_random = float(headline["random_mean_speedup_vs_default"])
    frontier_ablation = headline["frontier_ablation_mean_speedup_vs_default"]

    if decision == "promote_positive_headline":
        headline_status = "supported_positive"
        headline_caveat = (
            "This is the final non-split_k mainline result and must not be back-projected onto the archived split_k Phase 3 space."
        )
    elif decision == "bounded_improvement":
        headline_status = "bounded_improvement"
        headline_caveat = (
            "The final mainline result is clearly positive on mean performance, but it did not clear the stricter positive-seed gate for the strongest promotion tier."
        )
    else:
        headline_status = "bounded_negative"
        headline_caveat = (
            "The final non-split_k mainline push did not justify a stronger positive paper headline and should be framed as a final credibility-hardening failure."
        )

    rows = [
        {
            "claim_id": "C-FINAL-HEADLINE",
            "claim_classification": "headline",
            "hypothesis_id": "",
            "allowed_wording": "The guarded v5_mainline_profiled selector improves representative GEMM on the final non-split_k mainline and approaches naive random search under the same matched budget.",
            "status": headline_status,
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_baseline_mapping"])),
                    str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_selector_ablation"])),
                ]
            ),
            "evidence": (
                f"representative mean speedup vs default: parent={final_parent:.4f}, "
                f"v5_mainline_profiled={final_profiled:.4f}, naive_random_search={final_random:.4f}, "
                f"delta_vs_parent={final_delta:.4f}, gap_to_random={final_gap:.4f}"
            ),
            "confidence": "High",
            "caveat": headline_caveat,
            "figure_table_mapping": "F1, F7, T7",
        },
        {
            "claim_id": "C-FINAL-H1",
            "claim_classification": "supporting",
            "hypothesis_id": "H1",
            "allowed_wording": "Cheap compile-adjacent signals are useful for pruning but not sufficient for reliable representative GEMM ranking on realistic schedule surfaces.",
            "status": "supported",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                    str(resolve(root, "artifacts/analysis/phase2_20260327/claim_table.csv")),
                ]
            ),
            "evidence": "Phase 2 representative GEMM baseline mapping keeps compile-ranked selection well below the best reachable result on the expanded non-split_k surface.",
            "confidence": "High",
            "caveat": "The strongest final H1 wording should rely on the Phase 2 expanded non-split_k surface, not on the later split_k negative-result round.",
            "figure_table_mapping": "F1, T7",
        },
        {
            "claim_id": "C-FINAL-H2",
            "claim_classification": "supporting",
            "hypothesis_id": "H2",
            "allowed_wording": "LayerNorm is a regime-split secondary result: small_batch profiling is weak and noisy, while large_batch continues to favor compile-only ranking.",
            "status": "bounded_mixed",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_regime"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_regime"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_microstudy"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_microstudy"])),
                ]
            ),
            "evidence": "Phase 2 regime studies and Phase 3 microstudies agree that profiling does not deliver a strong, uniform LayerNorm advantage under matched budget.",
            "confidence": "Medium",
            "caveat": "LayerNorm remains explanatory and bounded; the paper should avoid presenting it as a second major positive optimization story.",
            "figure_table_mapping": "F3, T7",
        },
        {
            "claim_id": "C-FINAL-H3",
            "claim_classification": "supporting",
            "hypothesis_id": "H3",
            "allowed_wording": "Aligned GEMM is useful as context, but it is not the truth source; it overstates selector quality relative to the representative GEMM workload program.",
            "status": "contextual_support",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_aligned_reference"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v2_baseline_mapping"])),
                ]
            ),
            "evidence": "The final aligned-context figure is intentionally pinned to the stronger Phase 2 comparison because the optional R6 aligned refresh was gate-skipped.",
            "confidence": "Medium",
            "caveat": "H3 should be written as evaluation-context support, not as the main headline finding of the paper.",
            "figure_table_mapping": "F2, T7",
        },
        {
            "claim_id": "C-FINAL-H4",
            "claim_classification": "supporting",
            "hypothesis_id": "H4",
            "allowed_wording": "Revised selectors are a transfer story rather than a simple success story: a narrow-space frontier-aware revision worked, but later expanded-space evidence showed that the same revision family did not generalize cleanly.",
            "status": "mixed_transfer_limited",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["h4_retry_g3"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                    str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_selector_ablation"])),
                ]
            ),
            "evidence": (
                f"narrow-space H4 retry succeeded earlier; final mainline ablation now shows frontier-only={frontier_ablation:.4f} "
                f"and profiled={final_profiled:.4f} versus parent={final_parent:.4f} on the guarded non-split_k surface."
            ),
            "confidence": "High",
            "caveat": "Do not flatten H4 into either 'revisions always work' or 'revisions always fail'; the defensible claim is transfer-limited mixed evidence.",
            "figure_table_mapping": "F7, T7",
        },
        {
            "claim_id": "C-FINAL-H5",
            "claim_classification": "supporting",
            "hypothesis_id": "H5",
            "allowed_wording": "The transfer-safe v4 corrective pass remained unsupported on the expanded split_k space.",
            "status": "unsupported",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_baseline_mapping"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                ]
            ),
            "evidence": "The canonical Phase 3 representative GEMM mapping and ablation both keep the v4 family far below the parent selector and naive random search on the split_k space.",
            "confidence": "High",
            "caveat": "H5 stays specific to the expanded split_k Phase 3 surface and must not be rewritten to absorb the later non-split_k R6 positive result.",
            "figure_table_mapping": "F11, T7",
        },
        {
            "claim_id": "C-FINAL-SPLITK",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "split_k is retired from the main GEMM reportable surface.",
            "status": "retire",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_schedule_diag"])),
                    str(resolve(root, "artifacts/analysis/phase3_20260329/splitk_decision_table.csv")),
                ]
            ),
            "evidence": "The canonical Phase 3 diagnostic never promotes non-unit split_k into chosen or best-scored final families.",
            "confidence": "High",
            "caveat": "Retirement applies to the paper-facing mainline surface only; split_k remains available as archived diagnostic code.",
            "figure_table_mapping": "F11",
        },
        {
            "claim_id": "C-FINAL-ROWS",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "rows_per_program is retired from the main LayerNorm surface.",
            "status": "retire",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_small_microstudy"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["layernorm_v2_large_microstudy"])),
                    str(resolve(root, "artifacts/analysis/phase3_20260329/rows_per_program_decision_table.csv")),
                ]
            ),
            "evidence": "Non-unit rows_per_program appears only in weak or regressing paths and never becomes a stable mainline selector lever.",
            "confidence": "High",
            "caveat": "Retirement applies to the paper-facing mainline surface only; the knob remains part of archived diagnostic experiments.",
            "figure_table_mapping": "F3",
        },
        {
            "claim_id": "C-FINAL-CLOSEOUT",
            "claim_classification": "supporting",
            "hypothesis_id": "",
            "allowed_wording": "No further selector-family growth is justified for the paper backbone.",
            "status": "closed",
            "supporting_artifact_paths": "; ".join(
                [
                    str(resolve(root, CANONICAL_FINAL_STUDIES["gemm_final_baseline_mapping"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_baseline_mapping"])),
                    str(resolve(root, CANONICAL_CONTEXT_ARTIFACTS["gemm_v3_selector_ablation"])),
                ]
            ),
            "evidence": "The project now has both a bounded negative result on the split_k expansion and a successful final non-split_k mainline lock, leaving no unresolved evidence-backed reason to admit another selector family.",
            "confidence": "High",
            "caveat": "This closes the current paper-facing research program; it does not claim that no future project could justify a different selector family.",
            "figure_table_mapping": "F1, F7, T7",
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
        f"- positive robustness seeds vs parent: `{headline['winner_positive_seed_count']}`",
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


def main() -> None:
    root = repo_root()
    output_dir = root / "artifacts" / "analysis" / f"final_paper_{FINAL_BUNDLE_DATE}"
    output_dir.mkdir(parents=True, exist_ok=True)

    phase2_index = load_bundle_index(resolve(root, CANONICAL_ANALYSIS_BUNDLES["phase2"]))
    phase3_index = load_bundle_index(resolve(root, CANONICAL_ANALYSIS_BUNDLES["phase3"]))
    study_runs = find_required_paths(root, CANONICAL_FINAL_STUDIES)
    campaign_runs = {
        campaign_id: resolve(root, metadata["path"])
        for campaign_id, metadata in CANONICAL_FINAL_CAMPAIGNS.items()
    }

    artifact_integrity = build_artifact_integrity_summary(root, phase2_index, phase3_index, study_runs, campaign_runs)
    canonical_map = build_canonical_artifact_map(root, study_runs)
    strategy_summary = build_final_strategy_summary(study_runs, phase2_index, phase3_index)
    headline_summary = build_headline_result_summary(study_runs)
    figure_source_map = build_figure_source_map(root)
    final_claim_table = build_final_claim_table(root, headline_summary)
    summary_md = build_final_bundle_summary(headline_summary, figure_source_map, final_claim_table)

    write_csv(output_dir / "artifact_integrity_summary.csv", artifact_integrity)
    write_csv(output_dir / "canonical_artifact_map.csv", canonical_map)
    write_csv(output_dir / "final_strategy_summary.csv", strategy_summary)
    write_csv(output_dir / "headline_result_summary.csv", headline_summary)
    write_csv(output_dir / "figure_source_map.csv", figure_source_map)
    write_csv(output_dir / "final_claim_table.csv", final_claim_table)
    (output_dir / "final_bundle_summary.md").write_text(summary_md, encoding="utf-8")

    index = {
        "bundle": "final_paper",
        "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
        "output_dir": str(output_dir),
        "phase2_bundle": phase2_index["output_dir"],
        "phase3_bundle": phase3_index["output_dir"],
        "canonical_final_studies": {study_id: run_dir.name for study_id, run_dir in study_runs.items()},
        "canonical_context_artifacts": CANONICAL_CONTEXT_ARTIFACTS,
        "files": {
            "artifact_integrity_summary": str(output_dir / "artifact_integrity_summary.csv"),
            "canonical_artifact_map": str(output_dir / "canonical_artifact_map.csv"),
            "final_strategy_summary": str(output_dir / "final_strategy_summary.csv"),
            "headline_result_summary": str(output_dir / "headline_result_summary.csv"),
            "figure_source_map": str(output_dir / "figure_source_map.csv"),
            "final_claim_table": str(output_dir / "final_claim_table.csv"),
            "final_bundle_summary": str(output_dir / "final_bundle_summary.md"),
        },
        "key_decisions": {
            "r6_headline_decision": headline_summary.iloc[0]["decision"],
            "winner_revision_id": headline_summary.iloc[0]["winner_revision_id"],
            "aligned_refresh_promoted": False,
            "confirmation_rerun_promoted": False,
            "h5_status": "unsupported",
            "split_k_mainline_status": "retired",
            "rows_per_program_mainline_status": "retired",
        },
    }
    (output_dir / "analysis_bundle_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
