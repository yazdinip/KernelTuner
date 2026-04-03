# Figures Directory

Main-text figures are generated from the repo-local final paper bundle rather than drawn manually inside LaTeX.

Current generated assets live under:

- `paper/figures/generated/`

Regenerate them with:

```bash
python scripts/build_final_paper_bundle.py --output-tag final_paper_20260403
python scripts/build_paper_figures.py --bundle-dir artifacts/analysis/final_paper_20260403
```

If the canonical bundle date changes, update:

- `paper/FIGURE_MANIFEST.md`
- the figure environments in `paper/sections/design.tex` and `paper/sections/results.tex`
- `paper/SECTION_INDEX.md`
- any appendix references that point to the previous bundle
