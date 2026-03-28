"""Typed schemas for KernelTuner."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = 2

_LEGACY_SHAPE_KEYS = {"m", "n", "k", "rows", "hidden"}


class KTModel(BaseModel):
    """Base model with strict validation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=True)


class StudyKind(StrEnum):
    SMOKE = "smoke"
    DEVELOPMENT = "development"
    REPORTABLE = "reportable"
    DIAGNOSTIC_ONLY = "diagnostic_only"


class SelectorMode(StrEnum):
    PRUNE_ONLY = "prune_only"
    PRUNE_RANK = "prune_rank"
    PRUNE_RANK_PROFILED = "prune_rank_profiled"
    PRUNE_RANK_REVISED = "prune_rank_revised"
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
    TIMEOUT = "timeout"
    INVOCATION_FAILED = "invocation_failed"
    NO_PROFILE_DATA = "no_profile_data"
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


class ProfileSamplingMode(StrEnum):
    FIRST_CALIBRATION = "first_calibration"
    PER_WORKLOAD_CLASS_TOP1 = "per_workload_class_top1"
    ALL_CALIBRATION = "all_calibration"
    EXPLICIT_SHAPE_IDS = "explicit_shape_ids"


class AvailabilityFailureMode(StrEnum):
    DOWNGRADE_TO_DIAGNOSTIC = "downgrade_to_diagnostic"
    FAIL_RUN = "fail_run"


class HypothesisComparator(StrEnum):
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


class HypothesisSource(StrEnum):
    STRATEGY_ROWS = "strategy_rows"
    STABILITY_REPORT = "stability_report"


class ReductionMode(StrEnum):
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"


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


class ProfilePolicySpec(KTModel):
    counter_set_id: str | None = None
    shape_sampling_mode: ProfileSamplingMode = ProfileSamplingMode.FIRST_CALIBRATION
    max_shapes_per_config: int | None = None
    aggregation_mode: ReductionMode = ReductionMode.MEAN
    explicit_shape_ids: list[str] = Field(default_factory=list)
    availability_failure_mode: AvailabilityFailureMode = (
        AvailabilityFailureMode.DOWNGRADE_TO_DIAGNOSTIC
    )

    @field_validator("max_shapes_per_config")
    @classmethod
    def _positive_or_none(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("max_shapes_per_config must be positive when provided")
        return value


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
    workload_id: str | None = None
    comparison_tags: list[str] = Field(default_factory=list)


class ReportabilityPolicy(KTModel):
    enforce_preflight: bool = True
    require_workload_class_labels: bool = False
    require_stratified_split: bool = False
    minimum_calibration_shapes: int = 1
    minimum_held_out_shapes: int = 1
    minimum_held_out_per_workload_class: int = 0
    abort_on_incompatible_counter_set: bool = True

    @field_validator(
        "minimum_calibration_shapes",
        "minimum_held_out_shapes",
        "minimum_held_out_per_workload_class",
    )
    @classmethod
    def _non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("reportability minimums must be non-negative")
        return value


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
    supported_knob_families: list[str] = Field(default_factory=list)
    expected_signal_families: list[str] = Field(default_factory=list)
    unsupported_knobs: list[str] = Field(default_factory=list)


class ProblemShape(KTModel):
    shape_id: str
    dimensions: dict[str, int]
    dtype: str | None = None
    layout: str | None = None
    batch_group: str | None = None
    workload_class: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_shape_fields(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if "dimensions" not in payload:
            legacy_dims = {
                key: payload.pop(key)
                for key in list(payload)
                if key in _LEGACY_SHAPE_KEYS
            }
            if legacy_dims:
                payload["dimensions"] = legacy_dims
        if "metadata" not in payload:
            payload["metadata"] = {}
        return payload

    @field_validator("dimensions")
    @classmethod
    def _positive_dims(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("dimensions must not be empty")
        for name, dim in value.items():
            if dim <= 0:
                raise ValueError(f"shape dimension '{name}' must be positive")
        return dict(sorted(value.items()))

    def dim(self, name: str) -> int:
        return self.dimensions[name]

    @property
    def m(self) -> int | None:
        return self.dimensions.get("m")

    @property
    def n(self) -> int | None:
        return self.dimensions.get("n")

    @property
    def k(self) -> int | None:
        return self.dimensions.get("k")

    @property
    def rows(self) -> int | None:
        return self.dimensions.get("rows")

    @property
    def hidden(self) -> int | None:
        return self.dimensions.get("hidden")


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
    diagnostic_only: bool = False
    minimum_availability: float = 0.9
    notes: str | None = None

    @field_validator("minimum_availability")
    @classmethod
    def _availability_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("minimum_availability must be in [0, 1]")
        return value


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
    profile_policy: ProfilePolicySpec | None = None
    reportability_policy: ReportabilityPolicy = Field(default_factory=ReportabilityPolicy)
    selector_version: str = "v1"
    selector_revision_id: str | None = None
    budget_id: str | None = None
    benchmark_settings: BenchmarkSettings = Field(default_factory=BenchmarkSettings)
    profiling_settings: ProfilingSettings = Field(default_factory=ProfilingSettings)
    execution_settings: ExecutionSettings = Field(default_factory=ExecutionSettings)
    analysis_settings: AnalysisSettings = Field(default_factory=AnalysisSettings)
    explicit_configs: list[dict[str, int]] = Field(default_factory=list)
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
        if len(self.kernels) != 1:
            raise ValueError("v1 experiments must specify exactly one kernel")
        if self.budgets.seed is None:
            self.budgets.seed = self.seed
        if self.budget_id is None:
            self.budget_id = (
                f"cand{self.budgets.max_candidates}_bench{self.budgets.max_benchmarks}_"
                f"profile{self.budgets.max_profiles}"
            )
        if self.profile_policy is None:
            self.profile_policy = ProfilePolicySpec(counter_set_id=self.counter_set_id)
        elif self.profile_policy.counter_set_id is None:
            self.profile_policy.counter_set_id = self.counter_set_id
        if self.counter_set_id is None and self.profile_policy.counter_set_id is not None:
            self.counter_set_id = self.profile_policy.counter_set_id
        if self.study_kind == StudyKind.REPORTABLE:
            self.reportability_policy.enforce_preflight = True
            if self.reportability_policy.minimum_held_out_shapes == 0:
                self.reportability_policy.minimum_held_out_shapes = 1
        return self


class CandidateConfig(KTModel):
    schema_version: int = SCHEMA_VERSION
    experiment_id: str
    kernel_id: str
    shape_id: str
    config_id: str
    config: dict[str, int]
    shape_dimensions: dict[str, int] = Field(default_factory=dict)
    workload_class: str | None = None
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


class CounterAvailabilityRecord(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    strategy_id: str
    counter_set_id: str
    counter_name: str
    populated_rows: int
    total_rows: int
    non_null_fraction: float
    acceptable: bool


class BottleneckSignatureRecord(KTModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    strategy_id: str
    kernel_id: str
    shape_id: str
    config_id: str
    workload_class: str | None = None
    occupancy_bucket: str
    tensor_util_bucket: str
    memory_pressure_bucket: str
    scoreboard_bucket: str
    shared_conflict_bucket: str
    compile_feasibility_bucket: str
    selected_by_strategy: bool
    held_out_outcome: str
    regret_to_best_measured: float | None = None
    opportunity_tags: list[str] = Field(default_factory=list)


class HypothesisSpec(KTModel):
    hypothesis_id: str
    description: str
    comparison_pair: list[str] = Field(default_factory=list)
    clauses: list["HypothesisClause"] = Field(default_factory=list)
    notes: str | None = None


class RunGroupSpec(KTModel):
    group_id: str
    experiment_ids: list[str] = Field(default_factory=list)
    run_dirs: list[str] = Field(default_factory=list)
    include_latest_runs: int | None = None
    kernel_family: str | None = None
    workload_class: str | None = None
    selector_version: str | None = None
    selector_revision_id: str | None = None
    counter_set_id: str | None = None
    budget_id: str | None = None
    execution_mode: StudyKind | None = None
    seeds: list[int] = Field(default_factory=list)
    repeat_indices: list[int] = Field(default_factory=list)
    notes: str | None = None


class StudySpec(KTModel):
    study_id: str
    hypotheses: list[HypothesisSpec]
    run_groups: list[RunGroupSpec]
    group_by: list[str] = Field(
        default_factory=lambda: [
            "kernel_family",
            "workload_class",
            "selector_version",
            "counter_set_id",
            "budget_id",
            "seed",
        ]
    )
    primary_metric: str = "geomean_speedup_vs_default_config"
    secondary_metrics: list[str] = Field(
        default_factory=lambda: [
            "speedup_vs_naive_random_search",
            "speedup_vs_naive_grid_search",
            "winner_rate",
            "regret_vs_best_measured_calibration",
            "selection_agreement",
            "stability_band",
            "signal_runtime_correlation",
            "counter_availability",
        ]
    )
    reportability_filter: bool = True
    environment_filter: dict[str, str] = Field(default_factory=dict)
    comparison_rules: dict[str, Any] = Field(default_factory=dict)
    output_root: str = "artifacts/studies"


class RunLabels(KTModel):
    kernel_family: str | None = None
    workload_matrix_id: str | None = None
    counter_set_id: str | None = None
    selector_version: str | None = None
    selector_revision_id: str | None = None
    budget_id: str | None = None
    seed: int | None = None
    repeat_index: int | None = None
    campaign_id: str | None = None
    round_id: str | None = None
    execution_mode: StudyKind | None = None
    reportability_mode: str | None = None
    workload_classes: list[str] = Field(default_factory=list)


class CounterCompatibilityRecord(KTModel):
    schema_version: int = SCHEMA_VERSION
    counter_set_id: str
    kernel_family: str
    requested_counter_count: int
    available_counter_count: int
    missing_counters: list[str] = Field(default_factory=list)
    availability_fraction: float
    acceptable: bool
    diagnostic_only: bool = False
    kernel_family_allowed: bool = True
    validation_backend: str
    notes: str | None = None


class SelectorRankingFeature(KTModel):
    feature_name: str
    source: str
    direction: str = "desc"
    missing_value: float | None = None


class SelectorPruneRule(KTModel):
    rule_id: str
    source: str
    feature_name: str
    comparator: str
    threshold: float
    prune_reason: str


class SelectorRevisionSpec(KTModel):
    revision_id: str
    parent_selector_mode: SelectorMode = SelectorMode.PRUNE_RANK_PROFILED
    linked_opportunity_tags: list[str] = Field(default_factory=list)
    prune_rules: list[SelectorPruneRule] = Field(default_factory=list)
    frontier_ranking_features: list[SelectorRankingFeature] = Field(default_factory=list)
    ranking_features: list[SelectorRankingFeature] = Field(default_factory=list)
    tie_break_relative_tolerance: float = 0.02
    notes: str | None = None


class CampaignTemplateSpec(KTModel):
    template_id: str
    experiment_ids: list[str] = Field(default_factory=list)
    seeds: list[int] = Field(default_factory=list)
    repeats: int = 1
    counter_set_ids: list[str] = Field(default_factory=list)
    selector_revision_ids: list[str] = Field(default_factory=list)
    execution_mode: StudyKind | None = None
    notes: str | None = None

    @field_validator("repeats")
    @classmethod
    def _positive_repeats(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("repeats must be positive")
        return value


class CampaignStudyBinding(KTModel):
    study_id: str
    study_path: str | None = None
    requires_templates: list[str] = Field(default_factory=list)
    notes: str | None = None


class CampaignSpec(KTModel):
    campaign_id: str
    round_id: str
    templates: list[CampaignTemplateSpec]
    studies: list[CampaignStudyBinding] = Field(default_factory=list)
    artifact_root: str = "artifacts/campaigns"
    notes: str | None = None


class HypothesisMetricRef(KTModel):
    source: HypothesisSource = HypothesisSource.STRATEGY_ROWS
    metric: str
    group_id: str | None = None
    strategy_id: str | None = None
    kernel_family: str | None = None
    workload_class: str | None = None
    selector_version: str | None = None
    selector_revision_id: str | None = None
    counter_set_id: str | None = None
    budget_id: str | None = None
    reduction: ReductionMode = ReductionMode.MEAN


class HypothesisClause(KTModel):
    left: HypothesisMetricRef
    comparator: HypothesisComparator = HypothesisComparator.GREATER_THAN
    right: HypothesisMetricRef | None = None
    right_constant: float | None = None
    minimum_delta: float = 0.0

    @model_validator(mode="after")
    def _validate_rhs(self) -> "HypothesisClause":
        if self.right is None and self.right_constant is None:
            raise ValueError("hypothesis clause requires either right or right_constant")
        if self.right is not None and self.right_constant is not None:
            raise ValueError("hypothesis clause cannot set both right and right_constant")
        return self


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
    tool_paths: dict[str, str] = Field(default_factory=dict)
    gpu_attributes: dict[str, Any] = Field(default_factory=dict)


class InvocationMetadata(KTModel):
    command: str
    experiment_config_path: str | None = None
    kernel_config_path: str | None = None
    counter_config_path: str | None = None
    study_config_path: str | None = None
    campaign_config_path: str | None = None
    seed: int | None = None
    repeat_index: int | None = None
    selector_revision_id: str | None = None
    campaign_id: str | None = None


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
    labels: RunLabels = Field(default_factory=RunLabels)


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
    run_labels: dict[str, Any] = Field(default_factory=dict)


HypothesisSpec.model_rebuild()
