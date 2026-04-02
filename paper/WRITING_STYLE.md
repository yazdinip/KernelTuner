# Paper Writing Style

This file defines the writing standard for the paper draft in `paper/`.

The target style is the readability of `MAT1510_Project.pdf`, not a denser or more performative research voice. The reader should feel that the paper is careful and technical, but never harder to read than it needs to be.

## Core Goal

Write for a technical reader who may not know Triton, autotuning, or GPU performance tuning in advance.

The paper should:

- explain terms before leaning on them,
- keep the main thread visible at all times,
- make claims only as strongly as the evidence allows,
- and stay readable even when presenting mixed or negative results.

## Required Style Rules

### 1. Define ideas before compressing them

- Introduce a concept in plain language before using shorthand or specialized wording.
- If a term such as "matched budget," "representative GEMM," or "frontier construction" is important, explain it first in one clear sentence.
- Do not stack several new terms in the same sentence unless each one is already familiar from earlier text.

### 2. Prefer short paragraphs with one job each

- Most paragraphs should make one point.
- Use the first sentence to tell the reader what the paragraph is about.
- Avoid paragraphs that combine background, result, caveat, and interpretation all at once.

### 3. Keep prose simpler than the evidence layer

- The research docs and artifact manifests can stay dense.
- The paper should translate that evidence into a readable narrative.
- Do not write like a lab notebook or an execution log.

### 4. Keep numeric detail moderate in prose

- Important comparisons should appear in sentences.
- Dense value lists belong in tables, figures, or appendices.
- Use enough numbers to support the claim, but not so many that the paragraph becomes a spreadsheet.

### 5. Keep caveats, but do not repeat them mechanically

- Every promoted result needs its correct limitation.
- State the caveat once where it matters most, then move on unless the interpretation changes.
- Do not dilute the narrative by repeating the same limitation in every paragraph.

### 6. Use only paper-safe claim wording

- Main-text claim wording must match `docs/research/11_final_claim_inventory.md` or be weaker.
- Never strengthen a claim for rhetorical effect.
- If a sentence feels stronger than the claim ledger, weaken it.

### 7. Preserve the paper's role structure

- Representative GEMM is the primary truth source.
- Aligned GEMM is supporting context, not the headline.
- LayerNorm is a bounded secondary story, split by regime.
- `split_k` and `rows_per_program` are keep/drop decisions, not hidden implementation details.

### 8. Prefer concrete language over inflated phrasing

Use:

- "This result is mixed."
- "This helps with pruning, not ranking."
- "Aligned workloads make the selector look better than it is."
- "The transfer-safe pass did not hold up on the expanded space."

Avoid:

- vague intensifiers,
- overclaimed novelty language,
- and sentences whose main purpose is to sound more sophisticated than the evidence requires.

## Section-Level Guidance

### Introduction and Background

- Motivate the project with a simple question early.
- Explain the middle-ground positioning clearly: narrower than compiler-scale autoscheduling and narrower than full-kernel generation.
- Introduce Triton as the fixed-kernel setting before discussing the selector.

### Design and Methodology

- Explain what the system does in the order the reader needs it.
- Separate implementation mechanics from why those mechanics matter scientifically.
- Keep promotion rules and evidence discipline explicit but not repetitive.

### Results

- Organize the section as a story, not as a timeline of experiment rounds.
- Each subsection should answer one question and then interpret it.
- Use numbers to anchor the main comparison, then explain why the result matters.

### Discussion and Conclusion

- Say directly what the project established and what it did not.
- Keep the final framing narrow, credible, and easy to restate aloud.
- Treat negative results as part of the contribution, not as an apology.

## Editing Checklist

Before treating a section as stable, check:

- Does the section introduce terms before using them heavily?
- Does each paragraph have one main job?
- Are the main claims consistent with `11_final_claim_inventory.md`?
- Are there enough numbers to support the claim, but not so many that the prose becomes dense?
- Are caveats present without being repeated excessively?
- Could a technical reader outside this subfield follow the argument on a first pass?
