# Module Spec: Analysis and Reporting

## Purpose

Define how run artifacts are aggregated into human-readable summaries, derived analysis outputs, and cross-run study comparisons.

## Responsibilities

- load persisted artifacts for one run
- compute comparison metrics across selector and baselines
- generate the canonical `summary.json`
- produce derived run-level tables and plots
- support negative-result analysis and opportunity mining
- aggregate multiple completed runs into study-level comparison outputs

## Non-Responsibilities

- running experiments
- collecting runtime or profile data
- enforcing budget semantics during execution

## Public Inputs and Outputs

### Run-level inputs

- `manifest.json`
- `experiment_spec.yaml`
- all required run artifacts listed in the data-model doc

### Run-level outputs

Core output:

- `summary.json`

Common derived outputs when the required upstream data exists:

- `budget_usage.csv`
- `held_out_pairwise.csv`
- `held_out_per_shape.csv`
- `signal_runtime_correlations.csv`
- `counter_availability.parquet`
- `counter_availability_report.csv`
- `bottleneck_signatures.parquet`
- `opportunity_catalog.csv`
- `heuristic_candidates.yaml`
- `strategy_speedups.png`

### Study-level inputs

- `StudySpec`
- completed run directories

### Study-level outputs

Core output:

- `cross_run_summary.json`

Common derived outputs when grouped runs and metrics are available:

- `study_strategy_metrics.csv`
- `stability_report.csv`
- `hypothesis_results.csv`
- `opportunity_catalog.csv`
- `comparison_primary_metric.png`

## Required Summary Sections

`summary.json` must include:

- run metadata
- strategy list
- per-strategy best config
- budget consumption
- runtime comparison metrics
- held-out evaluation metrics
- failure counts
- interpretation notes or warnings
- reportability and comparability status
- uncertainty metrics
- artifact locations

## Internal Workflow

### Run-level summary path

1. Read the manifest and validate referenced artifact versions.
2. Load candidate, signal, runtime, profile, and decision artifacts.
3. Decode JSON-encoded structured columns from Parquet-backed tables.
4. Compute per-strategy and per-shape aggregates.
5. Compute held-out pairwise comparisons and geometric-mean speedups.
6. Compute cheap-signal correlations.
7. Compute counter-availability records from profiler results and the requested counter set.
8. Build bottleneck signatures and opportunity catalog entries.
9. Generate heuristic-candidate proposals from recurring opportunity patterns.
10. Verify comparability and reportability from recorded metadata and derived counter availability.
11. Write canonical summary output and derived tables and plots.

### Study-level comparison path

1. Load `StudySpec`.
2. Resolve referenced run directories from explicit paths and experiment IDs.
3. Ensure each run has a `summary.json`, generating one if needed.
4. Load normalized run payloads, held-out per-shape data, counter-availability reports, and opportunity tables.
5. Group runs according to the study definition.
6. Compute cross-run strategy metrics and stability statistics.
7. Evaluate pre-registered hypotheses as supported, unsupported, or inconclusive.
8. Aggregate opportunities across grouped runs.
9. Write study-level summary files and comparison plot.

## Persisted Artifacts Touched

- reads all required run artifacts
- writes the run-level outputs listed above
- reads completed run directories during study comparison
- writes study-level comparison outputs under `artifacts/studies/`

## Failure Modes and Fallback Behavior

- missing artifact declared in the manifest: fail clearly
- missing optional analysis input: degrade gracefully if the canonical output can still be produced
- inconsistent schema versions: fail fast
- empty held-out data: produce limited outputs and mark the comparison accordingly
- study filters matching no runs: fail clearly

## Logging and Observability Requirements

- log which run or study is being summarized
- log missing optional versus missing required artifacts distinctly
- log summary completion with the main comparison outputs
- log when a strategy is downgraded to non-comparable or oracle-only status
- log when counter sets fail availability thresholds

## Test Cases

- summary generation works for a complete successful run
- summary generation works for a partial-failure run with explicit limitations
- negative-result summary path includes interpretation notes
- counter-availability and opportunity artifacts are generated when profile data exists
- missing required artifact causes a clear failure
- non-comparable or oracle-only strategies are surfaced explicitly in the summary
- smoke or development-only runs are marked non-reportable
- study comparison works on multiple completed runs and writes hypothesis results

## Extension Points

- richer visualizations
- more advanced study-level grouping and statistical analysis
- export formats for course reports or papers

## Stable Contract vs Exploratory Areas

Stable contract:

- `summary.json` is the canonical serialized `ExperimentResult` view
- `cross_run_summary.json` is the canonical study-level comparison view
- analysis must support both positive and negative results
- reportability and comparability status must be explicit
- run-level opportunity outputs are part of the supported analysis surface

Exploratory areas:

- exact plot set
- exact hypothesis decision thresholds
- richer study-level statistical tests
