# Documentation Index

This file is the canonical table of contents for the `KernelTuner` v1 documentation package.

## Reading Order

1. [README.md](../README.md)
2. [01_project_charter.md](01_project_charter.md)
3. [02_system_overview.md](02_system_overview.md)
4. [03_execution_environment.md](03_execution_environment.md)
5. [04_experiment_protocol.md](04_experiment_protocol.md)
6. [05_data_model_and_artifacts.md](05_data_model_and_artifacts.md)
7. [ADR directory](adr/)
8. [Module specs](specs/)
9. [07_test_strategy.md](07_test_strategy.md)
10. [06_implementation_roadmap.md](06_implementation_roadmap.md)
11. [08_risks_and_open_questions.md](08_risks_and_open_questions.md)

## Documentation Conventions

- `Stable contract`: a decision that implementation should treat as fixed for v1.
- `Exploratory area`: a space where iteration is expected and change is acceptable if documented.
- `Authoritative`: the file is part of the current source of truth for implementation.
- `Owner`: the team responsible for maintaining the doc as implementation starts.

## Top-Level and Planning Docs

| Path | Purpose | Audience | Owner | Status |
| --- | --- | --- | --- | --- |
| [`../README.md`](../README.md) | Repo landing page and quick orientation | Build team | KernelTuner build team | Authoritative v1 |
| [`01_project_charter.md`](01_project_charter.md) | Project mission, scope, and success criteria | Build team, course staff | KernelTuner build team | Authoritative v1 |
| [`02_system_overview.md`](02_system_overview.md) | High-level architecture and end-to-end workflow | Build team | KernelTuner build team | Authoritative v1 |
| [`03_execution_environment.md`](03_execution_environment.md) | Supported environment and tooling assumptions | Build team | KernelTuner build team | Authoritative v1 |
| [`04_experiment_protocol.md`](04_experiment_protocol.md) | Measurement and evaluation rules | Build team | KernelTuner build team | Authoritative v1 |
| [`05_data_model_and_artifacts.md`](05_data_model_and_artifacts.md) | Artifact schemas, file formats, and storage contracts | Build team | KernelTuner build team | Authoritative v1 |
| [`06_implementation_roadmap.md`](06_implementation_roadmap.md) | Milestones, dependencies, and cut lines | Build team | KernelTuner build team | Authoritative v1 |
| [`07_test_strategy.md`](07_test_strategy.md) | Required tests and validation coverage | Build team | KernelTuner build team | Authoritative v1 |
| [`08_risks_and_open_questions.md`](08_risks_and_open_questions.md) | Explicit risks and unresolved issues | Build team, course staff | KernelTuner build team | Authoritative v1 |

## Architecture Decision Records

| Path | Decision | Audience | Owner | Status |
| --- | --- | --- | --- | --- |
| [`adr/ADR-001-single-host-single-gpu.md`](adr/ADR-001-single-host-single-gpu.md) | Single Linux host and one GPU for v1 | Build team | KernelTuner build team | Authoritative v1 |
| [`adr/ADR-002-heuristic-first-selector.md`](adr/ADR-002-heuristic-first-selector.md) | Heuristic selector first, learned ranker optional | Build team | KernelTuner build team | Authoritative v1 |
| [`adr/ADR-003-file-based-artifact-store.md`](adr/ADR-003-file-based-artifact-store.md) | File-based artifact storage | Build team | KernelTuner build team | Authoritative v1 |
| [`adr/ADR-004-matched-budget-evaluation.md`](adr/ADR-004-matched-budget-evaluation.md) | Matched search budgets for fair comparison | Build team | KernelTuner build team | Authoritative v1 |
| [`adr/ADR-005-primary-kernel-first.md`](adr/ADR-005-primary-kernel-first.md) | GEMM first, secondary kernels later | Build team | KernelTuner build team | Authoritative v1 |

## Module Specs

| Path | Purpose | Audience | Owner | Status |
| --- | --- | --- | --- | --- |
| [`specs/cli_and_config.md`](specs/cli_and_config.md) | CLI commands and config schemas | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/kernel_registry.md`](specs/kernel_registry.md) | Kernel registration and kernel metadata contracts | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/config_space_generator.md`](specs/config_space_generator.md) | Candidate configuration generation | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/benchmark_harness.md`](specs/benchmark_harness.md) | Correctness and runtime measurement rules | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/signal_collection.md`](specs/signal_collection.md) | Compile-time and compile-adjacent signal extraction | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/profiling_adapter.md`](specs/profiling_adapter.md) | Selective profiling workflow and counter capture | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/selector_engine.md`](specs/selector_engine.md) | Bottleneck-aware pruning, ranking, and calibration | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/baseline_strategies.md`](specs/baseline_strategies.md) | Baselines for comparison | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/experiment_orchestrator.md`](specs/experiment_orchestrator.md) | End-to-end experiment control | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/result_store.md`](specs/result_store.md) | Artifact writing, layout, and readback | Build team | KernelTuner build team | Authoritative v1 |
| [`specs/analysis_and_reporting.md`](specs/analysis_and_reporting.md) | Aggregation and experiment summary outputs | Build team | KernelTuner build team | Authoritative v1 |

## Maintenance Rule

If implementation deviates from these docs, update the relevant spec or add a new ADR before treating the code as authoritative.
