# ADR-005: Primary Kernel First

- Status: Accepted
- Date: 2026-03-03

## Context

The project needs one strong case study more than several shallow ones. GEMM is the most likely primary kernel family because it is central, tunable, and has a meaningful configuration space in Triton.

## Decision

GEMM is mandatory for v1. Secondary kernels are optional and may be added only after the full pipeline is stable on the primary kernel family.

## Consequences

- The team can prioritize one complete end-to-end story.
- The implementation roadmap has a clear cut line under time pressure.
- Generality claims must remain modest until secondary kernels are added.

## Rejected Alternatives

- Require two kernels from the start: rejected because it increases implementation risk too early.
- Keep the primary kernel unspecified: rejected because it delays important design choices.
- Focus only on tiny kernels: rejected because it weakens the project's substance.

## Revisit If

- The GEMM pipeline stabilizes early enough to add a second case study.
- Another kernel family becomes a better primary target due to tooling or implementation constraints discovered during build-out.
