# Old PDF vs Current Source

This note records the selective review of the checked-in `CSC2210H_Project.pdf` against the current LaTeX source in `paper/`.

## Status of the checked-in PDF

- The checked-in PDF is an older snapshot created on March 22, 2026.
- It is only 3 pages long.
- It still contains placeholder front matter, including the title `TITLE`.
- It should not be treated as the current source of truth.

The current paper state is the LaTeX source rooted at `paper/main.tex`.

## Front Matter Mismatch

The strongest mismatch is the front matter:

- old PDF title: `TITLE`
- current source title: `Bottleneck-Aware Schedule-First Tuning for Triton Kernels Under Matched Budget`
- old PDF author line: `Pedram` and `Giovanni Galea Curmi`
- current source author line: `Project Draft`

The old PDF therefore captures an earlier milestone, not the present manuscript state.

## What Exists Locally But Not in the Old PDF

The old PDF contains an early short draft with an introduction, related-work framing, and references. The current source now includes a full manuscript structure:

- abstract,
- introduction,
- background and problem setting,
- system design,
- experimental methodology,
- results,
- discussion and limitations,
- related work,
- conclusion,
- and appendices for methods, results, and provenance.

The current source also includes the main paper tables, figure manifest, table manifest, and section index used to keep the draft aligned with the evidence bundle.

## What the Old PDF Still Does Well

The old PDF has a few writing choices worth preserving because they are direct and easy to follow:

- It states the narrow project question early.
- It explains the paper's "middle ground" positioning in simple language.
- It plainly says what the project is not trying to do: redesign Triton, replace vendor libraries, or generate kernels from scratch.
- It introduces the practical tuning problem before moving into literature positioning.

These choices should remain visible in the current source even as the manuscript becomes more complete.

## Wording Worth Preserving Selectively

The following phrasing patterns from the old PDF are worth keeping when they fit naturally:

- "keeps the Triton kernel fixed"
- "a narrower but still meaningful question"
- "under the same budget"
- explicit contrasts such as "not redesign Triton" and "not generate new kernels from scratch"

These phrases are useful because they set scope quickly and avoid inflated language.

## Main Difference in Writing Density

The current source is more complete and scientifically stronger, but it is also denser than the old PDF in some places, especially in `Results` and `Discussion`.

The editing goal is therefore:

- keep the newer evidence-backed structure,
- preserve the clearer scope-setting language from the old PDF when helpful,
- and avoid drifting into a more compressed research voice than the paper needs.
