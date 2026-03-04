# ADR-002: Heuristic-First Selector

- Status: Accepted
- Date: 2026-03-03

## Context

The project wants to build something substantial without depending on a large amount of training data or a learned model that may fail for reasons unrelated to the bottleneck-aware idea itself.

## Decision

The v1 selector will start with two required layers:

1. pruning heuristics based on resource and validity signals
2. ranking heuristics based on suspected bottlenecks

A learned ranking component is explicitly optional and may be added only after the heuristic path is implemented and instrumented.

## Consequences

- The first implementation remains achievable within the project timeline.
- The selector still has enough structure to be meaningful.
- Negative results are easier to interpret because the initial system is simpler.
- The architecture must still leave room for a learned component later.

## Rejected Alternatives

- Learned model first: rejected because it increases data and evaluation complexity too early.
- Hard-coded single-rule selector only: rejected because it would make the project too narrow.
- Full exhaustive tuning only: rejected because it removes the selector contribution.

## Revisit If

- Calibration data clearly supports a simple learned ranker.
- Heuristic ranking saturates and further progress requires a predictive model.
