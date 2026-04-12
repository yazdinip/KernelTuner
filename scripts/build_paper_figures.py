#!/usr/bin/env python3
"""Generate vector paper figures from the final paper bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-dir",
        default=None,
        help="Final bundle directory. Defaults to the latest artifacts/analysis/final_paper_* bundle.",
    )
    parser.add_argument(
        "--output-dir",
        default="paper/figures/generated",
        help="Output directory for generated vector figure PDFs.",
    )
    return parser.parse_args()


def latest_final_bundle(root: Path) -> Path:
    analysis_root = root / "artifacts" / "analysis"
    candidates = sorted(path for path in analysis_root.glob("final_paper_*") if path.is_dir())
    if not candidates:
        raise FileNotFoundError("no final_paper_* bundle directories were found under artifacts/analysis")
    return candidates[-1]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def strategy_label(strategy_id: str, selector_revision_id: str = "") -> str:
    """Return a reader-facing label for a selector, using plain-language names
    rather than internal revision identifiers."""
    if strategy_id == "default_config":
        return "Default"
    if strategy_id == "naive_random_search":
        return "Random search"
    if strategy_id == "prune_rank":
        return "Compile signals"
    if strategy_id == "prune_rank_profiled":
        return "Compile + profile"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_frontier":
        return "Conservative"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
        return "Conservative + profile"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v4_transfer_safe_frontier":
        return "With reduction split"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v4_transfer_safe_profiled":
        return "With reduction split + profile"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v2_validation":
        return "Revised"
    return strategy_id


COLORS = {
    "Default": "#9aa1a8",
    "Random search": "#1f77b4",
    "Compile signals": "#d95f02",
    "Compile + profile": "#7570b3",
    "Conservative": "#1b9e77",
    "Conservative + profile": "#66a61e",
    "With reduction split": "#e7298a",
    "With reduction split + profile": "#e6ab02",
    "Revised": "#66a61e",
}


def ablation_label(raw: str) -> str:
    """Translate internal ablation row labels into plain-language x-axis labels."""
    mapping = {
        "parent": "Compile signals",
        "v4_frontier": "Reduction split\n(frontier only)",
        "v4_profiled": "Reduction split\n+ profile",
        "v5_frontier": "Conservative\n(frontier only)",
        "v5_profiled": "Conservative\n+ profile",
    }
    return mapping.get(raw, raw)


def save_figure(fig: plt.Figure, path: Path, *, tight: bool = True) -> None:
    if tight:
        fig.tight_layout()
    fig.savefig(path, format="pdf", bbox_inches="tight")
    plt.close(fig)


def _wrap_text(text: str, width: int) -> str:
    import textwrap

    return "\n".join(textwrap.wrap(text, width=width))


def build_pipeline_figure(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure1_pipeline_schematic.csv")
    records = frame.to_dict(orient="records")
    n_stages = len(records)

    # Human-readable stage headers that fit comfortably in a narrow box.
    stage_headers = {
        "Candidate generation": "Candidate\ngeneration",
        "Cheap signals": "Cheap\nsignals",
        "Frontier construction": "Frontier\nconstruction",
        "Bounded profiling": "Bounded\nprofiling",
        "Held-out evaluation": "Held-out\nevaluation",
        "Evidence promotion": "Evidence\npromotion",
    }
    # Slightly polished descriptions for standalone readability.
    stage_descriptions = {
        "Candidate generation": "Enumerate the schedule space; keep only admissible configurations.",
        "Cheap signals": "Read register count, shared-memory footprint, and occupancy without running the kernel.",
        "Frontier construction": "Use cheap signals to prune and rank candidates under the matched budget.",
        "Bounded profiling": "Optionally profile a small frontier subset on calibration shapes.",
        "Held-out evaluation": "Benchmark the chosen configuration on representative held-out shapes.",
        "Evidence promotion": "Promote only stable, reproducible runs into the reportable claim set.",
    }

    fig, ax = plt.subplots(figsize=(11.5, 3.6))
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_title(
        "The matched-budget tuning pipeline used throughout the paper",
        fontsize=11,
        pad=10,
    )

    box_width = 1.75
    box_height = 2.7
    gap = 0.12
    total_width = n_stages * box_width + (n_stages - 1) * gap
    x_start = (11.5 - total_width) / 2
    y = 0.2

    for index, row in enumerate(records):
        x = x_start + index * (box_width + gap)
        box = FancyBboxPatch(
            (x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.08",
            edgecolor="#4c566a",
            facecolor="#edf2f7",
            linewidth=1.0,
        )
        ax.add_patch(box)
        header = stage_headers.get(str(row["stage"]), str(row["stage"]))
        description = stage_descriptions.get(str(row["stage"]), str(row["description"]))
        ax.text(
            x + box_width / 2,
            y + box_height - 0.2,
            f"{int(row['step_order'])}.",
            ha="center",
            va="top",
            fontsize=8,
            color="#4c566a",
        )
        ax.text(
            x + box_width / 2,
            y + box_height - 0.55,
            header,
            ha="center",
            va="top",
            fontsize=9.5,
            fontweight="bold",
            color="#1f2933",
            linespacing=1.15,
        )
        ax.text(
            x + box_width / 2,
            y + box_height - 1.45,
            _wrap_text(description, 20),
            ha="center",
            va="top",
            fontsize=6.8,
            color="#2d3748",
            linespacing=1.3,
        )
        if index < n_stages - 1:
            arrow_x_start = x + box_width + 0.01
            arrow_x_end = x + box_width + gap - 0.01
            ax.annotate(
                "",
                xy=(arrow_x_end, y + box_height / 2),
                xytext=(arrow_x_start, y + box_height / 2),
                arrowprops=dict(arrowstyle="->", linewidth=1.1, color="#4c566a"),
                annotation_clip=False,
            )
    save_figure(fig, output_dir / "figure1_pipeline.pdf", tight=False)


def build_budget_curve(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure2_budget_curve.csv")
    # Single-budget snapshot: render as a bar chart so the four selectors are
    # directly comparable without a misleading line plot between repeated points.
    frame = frame.sort_values(["strategy_id", "selector_revision_id"])
    labels = []
    values = []
    colors = []
    for row in frame.itertuples():
        label = strategy_label(
            str(row.strategy_id),
            str(row.selector_revision_id) if pd.notna(row.selector_revision_id) else "",
        )
        labels.append(label)
        values.append(float(row.mean_speedup_vs_default))
        colors.append(COLORS.get(label, "#777777"))
    # Preferred display order: Default, Random, Compile-only parent, Conservative+profile.
    display_order = ["Default", "Random search", "Compile signals", "Conservative + profile"]
    ordering = sorted(range(len(labels)), key=lambda i: display_order.index(labels[i]) if labels[i] in display_order else len(display_order))
    labels = [labels[i] for i in ordering]
    values = [values[i] for i in ordering]
    colors = [colors[i] for i in ordering]

    budget_row = frame.drop_duplicates("budget_order").iloc[0]
    budget_str = f"{int(budget_row.max_benchmarks)} benchmarks, {int(budget_row.max_profiles)} profile runs"

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    bars = ax.bar(labels, values, color=colors, edgecolor="#333333", linewidth=0.6)
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--", label="Default parity")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.01,
            f"{value:.3f}x",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_ylabel("Speedup vs. default (geomean)")
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_title(
        f"Representative matrix multiplication, matched budget ({budget_str})",
        fontsize=9,
    )
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
    save_figure(fig, output_dir / "figure2_budget_curve.pdf")


def build_aligned_context(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure3_aligned_vs_representative.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    strategies = ["Compile signals", "Compile + profile", "Random search"]
    contexts = [
        ("representative", "Representative (irregular shapes)", "#4c72b0"),
        ("aligned", "Aligned (powers of two)", "#dd8452"),
    ]
    x = list(range(len(strategies)))
    width = 0.36
    for idx, (context, display, color) in enumerate(contexts):
        values = []
        for label in strategies:
            subset = frame[
                (frame["workload_context"] == context)
                & (frame.apply(lambda row: strategy_label(row["strategy_id"], row["selector_revision_id"] if pd.notna(row["selector_revision_id"]) else "") == label, axis=1))
            ]
            values.append(float(subset["mean_speedup_vs_default"].iloc[0]))
        positions = [value + (idx - 0.5) * width for value in x]
        bars = ax.bar(positions, values, width=width, label=display, color=color, edgecolor="#333333", linewidth=0.5)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.01,
                f"{value:.2f}x",
                ha="center",
                va="bottom",
                fontsize=7,
            )
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--", label="Default parity")
    ax.set_xticks(x)
    ax.set_xticklabels(strategies)
    ax.set_ylabel("Speedup vs. default (geomean)")
    ax.set_ylim(0, 1.30)
    ax.set_title(
        "Aligned matrix-mult shapes overstate selector quality",
        fontsize=10,
    )
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save_figure(fig, output_dir / "figure3_aligned_context.pdf")


def build_layernorm_regimes(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure4_layernorm_regimes.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    strategies = [
        ("Compile signals", ("prune_rank", "")),
        ("Compile + profile", ("prune_rank_profiled", "")),
        ("Revised", ("prune_rank_revised", "v2_validation")),
    ]
    regimes = [
        ("small_batch", "Small-batch regime", "#4c72b0"),
        ("large_batch", "Large-batch regime", "#dd8452"),
    ]
    x = list(range(len(strategies)))
    width = 0.36
    for idx, (regime, display, color) in enumerate(regimes):
        values = []
        for _display_label, (strategy_id, selector_revision_id) in strategies:
            subset = frame[(frame["regime"] == regime) & (frame["strategy_id"] == strategy_id)]
            if selector_revision_id:
                subset = subset[subset["selector_revision_id"] == selector_revision_id]
            values.append(float(subset["mean_speedup_vs_default"].iloc[0]))
        positions = [value + (idx - 0.5) * width for value in x]
        bars = ax.bar(positions, values, width=width, label=display, color=color, edgecolor="#333333", linewidth=0.5)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.003,
                f"{value:.3f}x",
                ha="center",
                va="bottom",
                fontsize=7,
            )
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--", label="Default parity")
    ax.set_xticks(x)
    ax.set_xticklabels([label for label, _ in strategies])
    ax.set_ylabel("Speedup vs. default (geomean)")
    ax.set_ylim(0.95, 1.03)
    ax.set_title("Layer normalization: profiling helps unevenly across regimes", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    save_figure(fig, output_dir / "figure4_layernorm_regimes.pdf")


def build_transfer_mainline(bundle_dir: Path, output_dir: Path) -> None:
    transfer = pd.read_csv(bundle_dir / "figure5_transfer_failure.csv")
    diagnostic = pd.read_csv(bundle_dir / "figure5_transfer_diagnostic.csv")
    ablation = pd.read_csv(bundle_dir / "figure5_mainline_ablation.csv")

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))

    # Left panel: transfer failure on the enlarged search space.
    transfer_labels = [ablation_label(label) for label in transfer["label"].tolist()]
    transfer_values = transfer["mean_speedup_vs_default"].tolist()
    transfer_colors = [
        COLORS.get(strategy_label(row.strategy_id, row.selector_revision_id or ""), "#777777")
        for row in transfer.itertuples()
    ]
    bars0 = axes[0].bar(transfer_labels, transfer_values, color=transfer_colors, edgecolor="#333333", linewidth=0.5)
    axes[0].axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    axes[0].text(
        0.99,
        1.0,
        "  default parity",
        transform=axes[0].get_yaxis_transform(),
        fontsize=7,
        color="#555555",
        va="center",
        ha="right",
    )
    axes[0].set_ylabel("Speedup vs. default (geomean)")
    axes[0].set_ylim(0, 1.55)
    axes[0].set_title(
        "Enlarged search space: reduction-split variants collapse",
        fontsize=9,
    )
    for bar, value in zip(bars0, transfer_values):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.2f}x",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    if not diagnostic.empty:
        row = diagnostic.iloc[0]
        diag_text = (
            "Diagnostic run:\n"
            f"selected family = best-scored: {bool(row['selected_matches_best_scored'])}\n"
            f"reduction split (selected): {int(row['selected_split_k'])}\n"
            f"reduction split (best-scored): {int(row['best_split_k'])}"
        )
        axes[0].text(
            0.98,
            0.98,
            diag_text,
            transform=axes[0].transAxes,
            fontsize=6.5,
            va="top",
            ha="right",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7fafc", edgecolor="#cbd5e0"),
        )
    plt.setp(axes[0].get_xticklabels(), fontsize=8)

    # Right panel: final mainline recovery after the reduction split is retired.
    ablation_labels = [ablation_label(label) for label in ablation["label"].tolist()]
    ablation_values = ablation["mean_speedup_vs_default"].tolist()
    ablation_colors = [
        COLORS.get(strategy_label(row.strategy_id, row.selector_revision_id or ""), "#777777")
        for row in ablation.itertuples()
    ]
    bars1 = axes[1].bar(ablation_labels, ablation_values, color=ablation_colors, edgecolor="#333333", linewidth=0.5)
    axes[1].axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    axes[1].text(
        0.99,
        1.0,
        "  default parity",
        transform=axes[1].get_yaxis_transform(),
        fontsize=7,
        color="#555555",
        va="center",
        ha="right",
    )
    axes[1].set_ylabel("Speedup vs. default (geomean)")
    axes[1].set_ylim(0, 1.55)
    axes[1].set_title(
        "Reduction split removed: conservative selector recovers parity",
        fontsize=9,
    )
    for bar, value in zip(bars1, ablation_values):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.2f}x",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    plt.setp(axes[1].get_xticklabels(), fontsize=8)

    save_figure(fig, output_dir / "figure5_transfer_mainline.pdf")


def main() -> None:
    args = parse_args()
    root = repo_root()
    bundle_dir = Path(args.bundle_dir).resolve() if args.bundle_dir else latest_final_bundle(root)
    required = [
        "figure1_pipeline_schematic.csv",
        "figure2_budget_curve.csv",
        "figure3_aligned_vs_representative.csv",
        "figure4_layernorm_regimes.csv",
        "figure5_mainline_ablation.csv",
        "figure5_transfer_failure.csv",
        "figure5_transfer_diagnostic.csv",
    ]
    missing = [name for name in required if not (bundle_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"{bundle_dir} does not look like a final paper bundle; missing CSVs: {missing}"
        )

    output_dir = (root / args.output_dir).resolve()
    ensure_dir(output_dir)

    build_pipeline_figure(bundle_dir, output_dir)
    build_budget_curve(bundle_dir, output_dir)
    build_aligned_context(bundle_dir, output_dir)
    build_layernorm_regimes(bundle_dir, output_dir)
    build_transfer_mainline(bundle_dir, output_dir)

    manifest = {
        "bundle_dir": str(bundle_dir),
        "output_dir": str(output_dir),
        "generated_files": {
            "figure1_pipeline": str(output_dir / "figure1_pipeline.pdf"),
            "figure2_budget_curve": str(output_dir / "figure2_budget_curve.pdf"),
            "figure3_aligned_context": str(output_dir / "figure3_aligned_context.pdf"),
            "figure4_layernorm_regimes": str(output_dir / "figure4_layernorm_regimes.pdf"),
            "figure5_transfer_mainline": str(output_dir / "figure5_transfer_mainline.pdf"),
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
