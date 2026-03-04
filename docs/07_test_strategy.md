# Test Strategy

## Purpose

This document defines the minimum testing and validation coverage for `KernelTuner` v1.

## Test Principles

- Correctness comes before performance claims.
- Schema stability and artifact integrity are part of the test surface.
- Failed configurations are a normal path and must be tested as first-class behavior.
- The project needs both software tests and experiment-validity checks.

## Test Categories

### 1. Unit Tests

Focus:

- ID generation
- config validation
- shape normalization
- budget accounting
- schema serialization helpers
- selector heuristic logic on synthetic inputs

Run expectations:

- should run without GPU wherever possible
- should cover deterministic logic thoroughly

### 2. Integration Tests

Focus:

- kernel registration through benchmark harness
- signal collection through result store
- profiling adapter invocation path
- orchestrator phase transitions
- CLI to module wiring

Run expectations:

- may require the target GPU host
- should use minimal shapes and tiny candidate sets

### 3. Benchmark Sanity Tests

Focus:

- repeated measurements are within a tolerable noise band
- warmup and timed-run behavior is applied correctly
- synchronization is not omitted
- failures are persisted rather than swallowed

### 4. Artifact and Schema Tests

Focus:

- manifest completeness
- Parquet schema versions
- YAML config validation
- read/write round-trips
- nullability behavior under failed measurements

### 5. Experiment Validity Tests

Focus:

- calibration and held-out data separation
- matched budget enforcement
- selector and baselines consuming the same candidate pool
- negative-result reporting path

### 6. Reproducibility Tests

Focus:

- deterministic candidate generation
- deterministic split assignment under a fixed seed
- deterministic ranking order when randomness is not involved
- equivalent sampling order when randomness is seeded

## Required Test Scenarios

The following scenarios are mandatory before treating the implementation as trustworthy:

1. Kernel registration rejects missing metadata and duplicate kernel IDs.
2. Config generation respects hard constraints and produces deterministic IDs.
3. Benchmark harness records failed configs explicitly and does not crash the whole experiment on one invalid config.
4. Runtime measurement uses fixed warmup and timed-run semantics and records enough metadata to reproduce results.
5. Signal collection can represent unavailable or tool-specific signals without schema breakage.
6. Profiling adapter can skip unsupported counters and mark the reason.
7. Selector never uses held-out measurements during calibration.
8. Baselines and selector consume the same candidate pool and same `SelectionBudget`.
9. Orchestrator writes a complete manifest even for partially failed runs.
10. Result store can round-trip every persisted artifact without schema ambiguity.
11. Analysis layer can produce a report for both positive and negative outcomes.
12. Re-running the same experiment spec with the same seed yields equivalent selection ordering where randomness is involved.

## Suggested Test Placement

- `tests/unit/`
- `tests/integration/`
- `tests/gpu/`
- `tests/artifacts/`

The exact directory names may change later, but these categories must remain.

## Acceptance Thresholds

- No module is considered complete without at least one unit or integration test aligned to its main contract.
- Artifact schemas are incomplete until round-trip tests exist.
- The selector is incomplete until budget, split separation, and failure recording are tested.
- Benchmark results are not reportable until benchmark sanity checks have run on the target host.

## Stable Contracts

- Schema tests, budget tests, and held-out split tests are mandatory.
- Failed and skipped paths must be tested, not treated as edge cases to ignore.
- Reproducibility tests are part of the core project, not a stretch goal.
