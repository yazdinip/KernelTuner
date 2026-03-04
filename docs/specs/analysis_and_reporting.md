# Module Spec: Analysis and Reporting

## Purpose

Define how run artifacts are aggregated into human-readable summaries, comparison tables, and negative-result analysis.

## Responsibilities

- load persisted artifacts for one run
- compute comparison metrics across selector and baselines
- generate the canonical `summary.json`
- produce tables and plots suitable for internal reporting
- support both positive and negative result narratives

## Non-Responsibilities

- running experiments
- collecting runtime or profile data
- enforcing budget semantics during execution

## Public Inputs and Outputs

Inputs:

- `manifest.json`
- all run artifacts listed in the data-model doc

Outputs:

- `summary.json`
- optional tabular or image outputs under the run directory

Required summary sections:

- run metadata
- strategy list
- per-strategy best config
- budget consumption
- runtime comparison metrics
- held-out evaluation metrics
- failure counts
- interpretation notes

## Internal Workflow

1. Read the manifest and validate referenced artifact versions.
2. Load candidate, signal, runtime, profile, and decision artifacts.
3. Compute per-strategy and per-scope aggregates.
4. Compare selector results with baselines under the recorded budgets.
5. Generate canonical summary output.
6. Generate optional plots and tables from the same normalized data.

## Persisted Artifacts Touched

- reads all required run artifacts
- writes `summary.json`
- may write derived plots or tables under the run directory

## Failure Modes and Fallback Behavior

- missing artifact declared in the manifest: fail summary generation clearly
- missing optional analysis input: degrade gracefully if the canonical summary can still be produced
- inconsistent schema versions: fail fast

## Logging and Observability Requirements

- log which run is being summarized
- log missing optional versus missing required artifacts distinctly
- log summary completion with the main comparison outputs

## Test Cases

- summary generation works for a complete successful run
- summary generation works for a partial-failure run with explicit limitations
- negative-result summary path includes interpretation notes
- missing required artifact causes a clear failure

## Extension Points

- richer visualizations
- multi-run aggregation and sweep analysis
- export formats for course reports or papers

## Stable Contract vs Exploratory Areas

Stable contract:

- `summary.json` is the canonical serialized `ExperimentResult` view
- analysis must support positive and negative results
- required summary sections listed above must exist in v1

Exploratory areas:

- exact plot set
- advanced multi-run comparison features
