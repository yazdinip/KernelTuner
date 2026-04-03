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
    if strategy_id == "default_config":
        return "Default"
    if strategy_id == "naive_random_search":
        return "Random"
    if strategy_id == "prune_rank":
        return "Compile"
    if strategy_id == "prune_rank_profiled":
        return "Compile+Profile"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_frontier":
        return "v5 Frontier"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v5_mainline_profiled":
        return "v5 Profiled"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v4_transfer_safe_frontier":
        return "v4 Frontier"
    if strategy_id == "prune_rank_revised" and selector_revision_id == "v4_transfer_safe_profiled":
        return "v4 Profiled"
    return strategy_id


COLORS = {
    "Default": "#9aa1a8",
    "Random": "#1f77b4",
    "Compile": "#d95f02",
    "Compile+Profile": "#7570b3",
    "v5 Frontier": "#1b9e77",
    "v5 Profiled": "#66a61e",
    "v4 Frontier": "#e7298a",
    "v4 Profiled": "#e6ab02",
}


def save_figure(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, format="pdf", bbox_inches="tight")
    plt.close(fig)


def build_pipeline_figure(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure1_pipeline_schematic.csv")
    fig, ax = plt.subplots(figsize=(8.5, 2.6))
    ax.axis("off")
    box_width = 0.145
    x_positions = [0.01, 0.18, 0.35, 0.52, 0.69, 0.86]
    y = 0.25
    for index, row in enumerate(frame.to_dict(orient="records")):
        x = x_positions[index]
        box = FancyBboxPatch(
            (x, y),
            box_width,
            0.5,
            boxstyle="round,pad=0.02",
            edgecolor="#4c566a",
            facecolor="#edf2f7",
            linewidth=1.0,
        )
        ax.add_patch(box)
        ax.text(x + box_width / 2, y + 0.33, row["stage"], ha="center", va="center", fontsize=8, fontweight="bold")
        ax.text(x + box_width / 2, y + 0.17, row["description"], ha="center", va="center", fontsize=6.6, wrap=True)
        if index < len(frame) - 1:
            ax.annotate(
                "",
                xy=(x + box_width + 0.012, y + 0.25),
                xytext=(x_positions[index + 1] - 0.008, y + 0.25),
                arrowprops=dict(arrowstyle="->", linewidth=1.0, color="#4c566a"),
            )
    save_figure(fig, output_dir / "figure1_pipeline.pdf")


def build_budget_curve(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure2_budget_curve.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    order = sorted(frame["budget_order"].dropna().unique())
    for (strategy_id, selector_revision_id), subset in frame.groupby(["strategy_id", "selector_revision_id"], dropna=False):
        label = strategy_label(str(strategy_id), str(selector_revision_id) if pd.notna(selector_revision_id) else "")
        subset = subset.sort_values("budget_order")
        ax.plot(
            subset["budget_order"],
            subset["mean_speedup_vs_default"],
            marker="o",
            linewidth=2.0,
            label=label,
            color=COLORS.get(label),
        )
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    ax.set_xticks(order)
    ax.set_xticklabels([f"{int(row.max_benchmarks)}/{int(row.max_profiles)}" for _, row in frame.drop_duplicates("budget_order").sort_values("budget_order").iterrows()])
    ax.set_xlabel("Matched budget (benchmarks / profiles)")
    ax.set_ylabel("Geomean speedup vs default")
    ax.set_title("Representative GEMM budget efficiency")
    ax.legend(frameon=False, fontsize=8, ncols=2)
    save_figure(fig, output_dir / "figure2_budget_curve.pdf")


def build_aligned_context(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure3_aligned_vs_representative.csv")
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    strategies = ["Compile", "Compile+Profile", "Random"]
    contexts = ["representative", "aligned"]
    x = range(len(strategies))
    width = 0.34
    for idx, context in enumerate(contexts):
        values = []
        for label in strategies:
            subset = frame[
                (frame["workload_context"] == context)
                & (frame.apply(lambda row: strategy_label(row["strategy_id"], row["selector_revision_id"] if pd.notna(row["selector_revision_id"]) else "") == label, axis=1))
            ]
            values.append(float(subset["mean_speedup_vs_default"].iloc[0]))
        positions = [value + (idx - 0.5) * width for value in x]
        ax.bar(positions, values, width=width, label=context.title(), alpha=0.9)
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    ax.set_xticks(list(x))
    ax.set_xticklabels(strategies)
    ax.set_ylabel("Geomean speedup vs default")
    ax.set_title("Aligned workloads flatter selector quality")
    ax.legend(frameon=False)
    save_figure(fig, output_dir / "figure3_aligned_context.pdf")


def build_layernorm_regimes(bundle_dir: Path, output_dir: Path) -> None:
    frame = pd.read_csv(bundle_dir / "figure4_layernorm_regimes.csv")
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    strategies = ["Compile", "Compile+Profile", "v2_validation"]
    label_map = {
        "Compile": ("prune_rank", ""),
        "Compile+Profile": ("prune_rank_profiled", ""),
        "v2_validation": ("prune_rank_revised", "v2_validation"),
    }
    regimes = ["small_batch", "large_batch"]
    x = range(len(strategies))
    width = 0.34
    for idx, regime in enumerate(regimes):
        values = []
        for label in strategies:
            strategy_id, selector_revision_id = label_map[label]
            subset = frame[(frame["regime"] == regime) & (frame["strategy_id"] == strategy_id)]
            if selector_revision_id:
                subset = subset[subset["selector_revision_id"] == selector_revision_id]
            values.append(float(subset["mean_speedup_vs_default"].iloc[0]))
        positions = [value + (idx - 0.5) * width for value in x]
        ax.bar(positions, values, width=width, label=regime.replace("_", " ").title())
    ax.axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["Compile", "Compile+Profile", "Revised"])
    ax.set_ylabel("Geomean speedup vs default")
    ax.set_title("LayerNorm profiling is regime dependent")
    ax.legend(frameon=False)
    save_figure(fig, output_dir / "figure4_layernorm_regimes.pdf")


def build_transfer_mainline(bundle_dir: Path, output_dir: Path) -> None:
    transfer = pd.read_csv(bundle_dir / "figure5_transfer_failure.csv")
    diagnostic = pd.read_csv(bundle_dir / "figure5_transfer_diagnostic.csv")
    ablation = pd.read_csv(bundle_dir / "figure5_mainline_ablation.csv")

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.2))

    transfer_labels = transfer["label"].tolist()
    transfer_values = transfer["mean_speedup_vs_default"].tolist()
    axes[0].bar(
        transfer_labels,
        transfer_values,
        color=[COLORS.get(strategy_label(row.strategy_id, row.selector_revision_id or ""), "#777777") for row in transfer.itertuples()],
    )
    axes[0].axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    axes[0].set_ylabel("Geomean speedup vs default")
    axes[0].set_title("Phase 3 transfer failure")
    if not diagnostic.empty:
        row = diagnostic.iloc[0]
        diag_text = (
            f"chosen=best: {bool(row['selected_matches_best_scored'])}\n"
            f"selected split_k={int(row['selected_split_k'])}\n"
            f"best split_k={int(row['best_split_k'])}"
        )
        axes[0].text(
            0.02,
            0.02,
            diag_text,
            transform=axes[0].transAxes,
            fontsize=8,
            va="bottom",
            ha="left",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#f7fafc", edgecolor="#cbd5e0"),
        )

    ablation_labels = ablation["label"].tolist()
    ablation_values = ablation["mean_speedup_vs_default"].tolist()
    axes[1].bar(
        ablation_labels,
        ablation_values,
        color=[COLORS.get(strategy_label(row.strategy_id, row.selector_revision_id or ""), "#777777") for row in ablation.itertuples()],
    )
    axes[1].axhline(1.0, color="#555555", linewidth=1.0, linestyle="--")
    axes[1].set_title("Final mainline ablation")

    save_figure(fig, output_dir / "figure5_transfer_mainline.pdf")


def main() -> None:
    args = parse_args()
    root = repo_root()
    bundle_dir = Path(args.bundle_dir).resolve() if args.bundle_dir else latest_final_bundle(root)
    if not (bundle_dir / "analysis_bundle_index.json").exists():
        raise FileNotFoundError(f"{bundle_dir} does not look like a final paper bundle")

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
