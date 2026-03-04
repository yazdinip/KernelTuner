# ADR-004: Matched Budget Evaluation

- Status: Accepted
- Date: 2026-03-03

## Context

The project's main empirical claim is about using search budget more effectively, not simply about finding a good configuration by spending more measurements.

## Decision

Selector and baseline strategies must be compared under matched `SelectionBudget` semantics. Any exception must be declared explicitly and marked as non-comparable in reporting.

## Consequences

- The evaluation protocol stays aligned with the research question.
- The implementation must expose budget accounting clearly.
- Baselines cannot be under-specified or given hidden advantages.

## Rejected Alternatives

- Compare against unconstrained naive tuning: rejected because it confounds budget with method quality.
- Equal wall-clock only with no count-based budget: rejected because tooling overhead can distort the comparison.
- Strategy-specific budget rules: rejected because they undermine fairness.

## Revisit If

- A later extension studies a different question, such as absolute best-found configuration independent of search cost.
