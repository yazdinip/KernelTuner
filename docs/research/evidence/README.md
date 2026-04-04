# Evidence Snapshot

This directory preserves the compact paper-facing evidence set in tracked repo state so the
project can remain self-contained even if the large `artifacts/` tree is removed locally.

What is kept here:

- the final paper bundle summaries and plot-ready figure CSVs
- concise Phase 2 and Phase 3 promoted-result summaries
- the Phase 3 `split_k` and `rows_per_program` retirement tables

What is intentionally not kept here:

- raw experiment run directories
- large parquet tables
- transient scheduler logs
- superseded or incomplete campaign roots

This snapshot is a compact preservation layer for the current paper and research docs. It is
derived from the historical `artifacts/analysis/` bundles but is meant to survive local cleanup
of the full artifact directory.

Current preserved bundles:

- `phase2_20260327_summary.md`
- `phase3_20260329_summary.md`
- `phase3_20260329/`
- `final_paper_20260403/`
