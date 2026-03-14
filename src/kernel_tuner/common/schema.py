"""Typed schemas for KernelTuner."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = 1


class KTModel(BaseModel):
    """Base model with strict validation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=True)


class StudyKind(StrEnum):
    SMOKE = "smoke"
    DEVELOPMENT = "development"
    REPORTABLE = "reportable"


class SelectorMode(StrEnum):
    PRUNE_ONLY = "prune_only"
    PRUNE_RANK = "prune_rank"
    PRUNE_RANK_PROFILED = "prune_rank_profiled"
    LEARNED_RANK = "learned_rank"


class BaselineMode(StrEnum):
    DEFAULT_CONFIG = "default_config"
    NAIVE_RANDOM_SEARCH = "naive_random_search"
    NAIVE_GRID_SEARCH = "naive_grid_search"
    SMALL_SPACE_ORACLE = "small_space_oracle"


class ComparisonClass(StrEnum):
    MATCHED_BUDGET = "matched_budget"
    ORACLE_ONLY = "oracle_only"
    NON_COMPARABLE = "non_comparable"


class RuntimeStatus(StrEnum):
    SUCCESS = "success"
    COMPILE_FAILED = "compile_failed"
    RUNTIME_FAILED = "runtime_failed"
    INVALID_CONFIG = "invalid_config"
    SKIPPED_BUDGET = "skipped_budget"
    SKIPPED_DEPENDENCY = "skipped_dependency"


class ProfileStatus(StrEnum):
    SUCCESS = "success"
    UNSUPPORTED_COUNTER = "unsupported_counter"
    TOOL_UNAVAILABLE = "tool_unavailable"
    PROFILE_FAILED = "profile_failed"
    SKIPPED_BUDGET = "skipped_budget"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class MeasurementPhase(StrEnum):
    CALIBRATION = "calibration"
    HELD_OUT = "held_out"
    ORACLE = "oracle"


class BenchmarkSettings(KTModel):
    warmup_iterations: int = 10
    timed_iterations: int = 30
    timing_backend: str = "cuda_events"
    reuse_inputs: bool = True
    store_raw_samples: bool = False

    @field_validator("warmup_iterations", "timed_iterations")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("iteration counts must be non-negative")
        return value


class ProfilingSettings(KTModel):
    replay_mode: str = "kernel"
    kernel_name_regex: str | None = None
    timeout_s: float | None = None
    cooldown_s: float = 0.0


class ExecutionSettings(KTModel):
    cache_root: str | None = None
    scratch_root: str | None = None
    isolate_triton_cache: bool = True
    expected_gpu_name: str | None = None
    expected_node_name: str | None = None
    expected_partition: str | None = None
    cuda_home: str | None = None


class AnalysisSettings(KTModel):
    enable_small_space_oracle: bool = False
    reportability_target: str | None = None
    confidence_interval_method: str = "bootstrap"


class SelectionBudget(KTModel):
    max_candidates: int
    max_benchmarks: int
    max_profiles: int
    seed: int | None = None
    wall_clock_limit_s: float | None = None

    @field_validator("max_candidates", "max_benchmarks", "max_profiles")
    @classmethod
    def _strictly_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("budget fields must be positive")
        return value


class CorrectnessPolicy(KTModel):
    atol: float = 1e-2
    rtol: float = 1e-2
    reference_dtype: str = "fp32"


class ShapeSchema(KTModel):
    required_dims: list[str]
    required_metadata: list[str] = Field(default_factory=list)


class KernelSpec(KTModel):
    kernel_id: str
    family: str
    description: str
    shape_schema: ShapeSchema
    dtype_support: list[str]
    config_parameters: dict[str, list[int]]
    reference_impl: str
    supports_profiling: bool
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    default_config: dict[str, int] | None = None
    correctness_policy: CorrectnessPolicy | None = None


class ProblemShape(KTModel):
    shape_id: str
    m: int
    n: int
    k: int
    dtype: str
    layout: str
    batch_group: str | None = None
    notes: str | None = None

    @field_validator("m", "n", "k")
    @classmethod
    def _positive_dims(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("shape dimensions must be positive")
        return value


class CounterSetSpec(KTModel):
    counter_set_id: str
    description: str
    tool: str
    counters: list[str]
    kernel_family_filters: list[str] = Field(default_factory=list)
    ncu_args: list[str] = Field(default_factory=list)
    replay_mode: str | None = None
    kernel_name_regex: str | None = None
    target_processes: str | None = None
    notes: str | None = None


class ExperimentSpec(KTModel):
    experiment_id: str
    kernels: list[str]
    shapes: list[ProblemShape]
    selector_modes: list[SelectorMode]
    baselines: list[BaselineMode]
    budgets: SelectionBudget
    calibration_split: float
    held_out_split: float
    artifact_root: str
    seed: int
    study_kind: StudyKind = StudyKind.DEVELOPMENT
    counter_set_id: str | None = None
    benchmark_settings: BenchmarkSettings = Field(default_factory=BenchmarkSettings)
    profiling_settings: ProfilingSettings = Field(default_factory=ProfilingSettings)
    execution_settings: ExecutionSettings = Field(default_factory=ExecutionSettings)
    analysis_settings: AnalysisSettings = Field(default_factory=AnalysisSettings)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_splits(self) -> "ExperimentSpec":
        total = self.calibration_split + self.held_out_split
        if abs(total - 1.0) > 1e-6:
            raise ValueError("calibration_split and held_out_split must sum to 1.0")
        if self.study_kind == StudyKind.REPORTABLE:
            if self.calibration_split <= 0.0 or self.held_out_split <= 0.0:
                raise ValueError("reportable studies require non-zero calibration and held-out splits")
        if self.budgets.seed is None:
            self.budgets.seed = self.seed
        return self


class CandidateConfig(KTModel):
    schema_version: int = SCHEMA_VERSION
    experiment_id: str
    kernel_id: str
    shape_id: str
    config_id: str
    block_m: int
    block_n: int
    block_k: int
    num_warps: int
    num_stages: int
    is_valid: bool
    validation_notes: str | None = None
    generation_provenance: str | None = None


class CompileSignalRecord(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    kernel_id: str
    shape_id: str
    config_id: str
    compile_status: str
    compile_success: bool
    register_count: int | None = None
    shared_memory_bytes: int | None = None
    occupancy_estimate: float | None = None
    signal_backend: str | None = None
    occupancy_method: str | None = None
    notes: str | None = None


class RuntimeMeasurement(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    strategy_id: str
    measurement_phase: MeasurementPhase
    kernel_id: str
    shape_id: str
    config_id: str
    warmup_count: int
    timed_run_count: int
    latency_median_us: float | None
    latency_mean_us: float | None
    latency_std_us: float | None
    latency_p95_us: float | None
    throughput_value: float | None
    throughput_unit: str | None
    status: RuntimeStatus
    raw_sample_ref: str | None = None
    timing_backend: str | None = None
    measurement_order_index: int | None = None
    error_message: str | None = None
    attempt_index: int = 0


class ProfileMeasurement(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    strategy_id: str
    kernel_id: str
    shape_id: str
    config_id: str
    counter_set_id: str
    profile_status: ProfileStatus
    counter_map: dict[str, float | None] = Field(default_factory=dict)
    profiler_metadata: dict[str, Any] = Field(default_factory=dict)
    profiler_stdout_ref: str | None = None
    profiler_stderr_ref: str | None = None
    notes: str | None = None


class SelectionDecision(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    strategy_id: str
    comparison_class: ComparisonClass
    selector_mode: str
    kernel_id: str
    shape_scope: str
    selected_config_id: str | None = None
    ranked_config_ids: list[str] = Field(default_factory=list)
    pruned_config_ids: list[str] = Field(default_factory=list)
    candidates_considered: int = 0
    benchmarks_requested: int = 0
    profiles_requested: int = 0
    decision_wall_clock_s: float | None = None
    rationale_summary: str
    decision_status: str
    requested_selector_mode: str | None = None
    score_map: dict[str, float] = Field(default_factory=dict)
    confidence_value: float | None = None
    calibration_metadata: dict[str, Any] = Field(default_factory=dict)


class EnvironmentMetadata(KTModel):
    hostname: str
    os_name: str
    os_version: str
    python_version: str
    gpu_name: str | None = None
    gpu_uuid: str | None = None
    nvidia_driver_version: str | None = None
    cuda_runtime_version: str | None = None
    pytorch_version: str | None = None
    triton_version: str | None = None
    ncu_version: str | None = None
    cuda_visible_devices: str | None = None
    git_commit: str | None = None
    git_branch: str | None = None
    git_dirty: bool | None = None
    cache_roots: dict[str, str] = Field(default_factory=dict)


class InvocationMetadata(KTModel):
    command: str
    experiment_config_path: str | None = None
    kernel_config_path: str | None = None
    counter_config_path: str | None = None
    seed: int | None = None


class SlurmMetadata(KTModel):
    job_id: str | None = None
    array_task_id: str | None = None
    partition: str | None = None
    node_name: str | None = None
    gres: str | None = None
    cpus_per_task: str | None = None
    mem: str | None = None


class ArtifactFile(KTModel):
    logical_name: str
    relative_path: str
    schema_version: int
    row_count: int | None = None
    content_hash: str | None = None


class Manifest(KTModel):
    schema_version: int = SCHEMA_VERSION
    experiment_id: str
    run_id: str
    created_at_utc: datetime
    git_commit: str | None = None
    git_branch: str | None = None
    git_dirty: bool | None = None
    environment: EnvironmentMetadata
    invocation: InvocationMetadata
    slurm: SlurmMetadata | None = None
    artifact_files: list[ArtifactFile] = Field(default_factory=list)
    status: RunStatus = RunStatus.CREATED
    warnings: list[str] = Field(default_factory=list)


class ExperimentResult(KTModel):
    schema_version: int = SCHEMA_VERSION
    experiment_id: str
    run_id: str
    terminal_status: str
    strategies: list[str]
    best_configs: dict[str, str | None]
    aggregate_metrics: dict[str, Any] = Field(default_factory=dict)
    comparison_warnings: list[str] = Field(default_factory=list)
    reportability: dict[str, Any] = Field(default_factory=dict)
    uncertainty_metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_locations: dict[str, str] = Field(default_factory=dict)
