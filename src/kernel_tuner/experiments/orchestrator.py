"""Experiment orchestration."""

from __future__ import annotations

import json
import os
import random
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from kernel_tuner.analysis.reporting import summarize_run
from kernel_tuner.baselines.strategies import run_baseline_mode
from kernel_tuner.benchmark.harness import benchmark_candidate
from kernel_tuner.common.config import (
    counter_set_path,
    load_counter_set,
    kernel_config_path,
    load_kernel_spec,
    load_selector_revision_spec,
    resolve_artifact_root,
    selector_revision_path,
)
from kernel_tuner.common.ids import make_run_id
from kernel_tuner.common.provenance import (
    capture_environment_metadata,
    capture_invocation_metadata,
    capture_slurm_metadata,
    python_command,
    require_gpu_environment,
)
from kernel_tuner.common.schema import (
    CandidateConfig,
    ComparisonClass,
    CounterCompatibilityRecord,
    ExperimentSpec,
    Manifest,
    MeasurementPhase,
    ProfileMeasurement,
    ProfileStatus,
    RunLabels,
    RunStatus,
    RuntimeStatus,
    RuntimeMeasurement,
    SelectorRevisionSpec,
    StudyKind,
)
from kernel_tuner.config_space.generator import generate_candidate_records
from kernel_tuner.kernels.registry import resolve_kernel
from kernel_tuner.profiling.adapter import profile_candidate
from kernel_tuner.profiling.compatibility import validate_counter_set_for_experiment
from kernel_tuner.selector.engine import run_selector_mode
from kernel_tuner.signals.collector import collect_compile_signals
from kernel_tuner.storage import RunStore


def _mode_name(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _shape_split(spec: ExperimentSpec):
    ordered = sorted(spec.shapes, key=lambda shape: shape.shape_id)
    if len(ordered) <= 1 or spec.held_out_split <= 0.0:
        return ordered, []
    should_stratify = spec.reportability_policy.require_stratified_split or (
        spec.study_kind == StudyKind.REPORTABLE and any(shape.workload_class for shape in ordered)
    )
    if not should_stratify:
        rng = random.Random(spec.seed)
        shuffled = ordered[:]
        rng.shuffle(shuffled)
        calibration_count = round(len(shuffled) * spec.calibration_split)
        calibration_count = max(1, min(len(shuffled) - 1, calibration_count))
        calibration = sorted(shuffled[:calibration_count], key=lambda shape: shape.shape_id)
        held_out = sorted(shuffled[calibration_count:], key=lambda shape: shape.shape_id)
        return calibration, held_out

    calibration: list = []
    held_out: list = []
    grouped: dict[str, list] = {}
    for shape in ordered:
        grouped.setdefault(shape.workload_class or "__unlabeled__", []).append(shape)
    for workload_class, shapes in sorted(grouped.items()):
        if len(shapes) <= 1:
            calibration.extend(shapes)
            continue
        rng = random.Random(f"{spec.seed}:{workload_class}")
        shuffled = shapes[:]
        rng.shuffle(shuffled)
        calibration_count = round(len(shuffled) * spec.calibration_split)
        calibration_count = max(1, min(len(shuffled) - 1, calibration_count))
        calibration.extend(sorted(shuffled[:calibration_count], key=lambda shape: shape.shape_id))
        held_out.extend(sorted(shuffled[calibration_count:], key=lambda shape: shape.shape_id))
    return calibration, held_out


def _validate_environment(spec: ExperimentSpec, environment) -> None:
    require_gpu_environment(
        spec.execution_settings.expected_partition,
        spec.execution_settings.expected_node_name,
    )
    expected_gpu = spec.execution_settings.expected_gpu_name
    if expected_gpu and environment.gpu_name and environment.gpu_name != expected_gpu:
        raise RuntimeError(f"expected GPU '{expected_gpu}' but found '{environment.gpu_name}'")
    if expected_gpu and environment.gpu_name is None and spec.study_kind == "reportable":
        raise RuntimeError("reportable run requires visible GPU metadata")
    cuda_home = spec.execution_settings.cuda_home
    if cuda_home and not Path(cuda_home).exists():
        raise RuntimeError(f"configured cuda_home '{cuda_home}' does not exist")


def _profile_shapes(spec: ExperimentSpec, calibration_shapes) -> list:
    if not calibration_shapes:
        return []
    policy = spec.profile_policy
    if policy is None:
        return [calibration_shapes[0]]
    mode = policy.shape_sampling_mode
    if mode == "all_calibration":
        selected = list(calibration_shapes)
    elif mode == "explicit_shape_ids":
        explicit_ids = set(policy.explicit_shape_ids)
        selected = [shape for shape in calibration_shapes if shape.shape_id in explicit_ids]
    elif mode == "per_workload_class_top1":
        by_class: dict[str, list] = {}
        for shape in calibration_shapes:
            by_class.setdefault(shape.workload_class or "__unlabeled__", []).append(shape)
        selected = [
            sorted(shapes, key=lambda shape: shape.shape_id)[0]
            for _, shapes in sorted(by_class.items())
            if shapes
        ]
    else:
        selected = [sorted(calibration_shapes, key=lambda shape: shape.shape_id)[0]]
    max_shapes = policy.max_shapes_per_config if policy else None
    if max_shapes is not None:
        selected = selected[:max_shapes]
    return selected


def _run_labels(
    *,
    experiment_spec: ExperimentSpec,
    kernel_family: str,
    counter_set_id: str | None,
    repeat_index: int | None,
    campaign_id: str | None,
    round_id: str | None,
) -> RunLabels:
    return RunLabels(
        kernel_family=kernel_family,
        workload_matrix_id=experiment_spec.analysis_settings.workload_id,
        counter_set_id=counter_set_id,
        selector_version=experiment_spec.selector_version,
        selector_revision_id=experiment_spec.selector_revision_id,
        budget_id=experiment_spec.budget_id,
        seed=experiment_spec.seed,
        repeat_index=repeat_index,
        campaign_id=campaign_id,
        round_id=round_id,
        execution_mode=experiment_spec.study_kind,
        reportability_mode=(
            "matched_budget" if experiment_spec.study_kind == StudyKind.REPORTABLE else experiment_spec.study_kind
        ),
        workload_classes=sorted(
            {shape.workload_class for shape in experiment_spec.shapes if shape.workload_class is not None}
        ),
    )


def _comparison_class_for_run(
    experiment_spec: ExperimentSpec,
    counter_compatibility: CounterCompatibilityRecord | None,
) -> ComparisonClass:
    if experiment_spec.study_kind == StudyKind.REPORTABLE:
        if counter_compatibility is not None and not counter_compatibility.acceptable:
            return ComparisonClass.NON_COMPARABLE
        return ComparisonClass.MATCHED_BUDGET
    return ComparisonClass.NON_COMPARABLE


def _validate_reportability_contract(
    spec: ExperimentSpec,
    calibration_shapes,
    held_out_shapes,
    compatibility: CounterCompatibilityRecord | None,
) -> list[str]:
    policy = spec.reportability_policy
    warnings: list[str] = []
    if not policy.enforce_preflight:
        return warnings
    if spec.study_kind == StudyKind.REPORTABLE:
        if len(calibration_shapes) < policy.minimum_calibration_shapes:
            raise RuntimeError(
                f"reportable run requires at least {policy.minimum_calibration_shapes} calibration shapes"
            )
        if len(held_out_shapes) < policy.minimum_held_out_shapes:
            raise RuntimeError(
                f"reportable run requires at least {policy.minimum_held_out_shapes} held-out shapes"
            )
        if policy.require_workload_class_labels and any(not shape.workload_class for shape in spec.shapes):
            raise RuntimeError("reportable run requires workload_class labels on all shapes")
        if policy.minimum_held_out_per_workload_class > 0:
            by_class: dict[str, int] = {}
            for shape in held_out_shapes:
                by_class[shape.workload_class or "__unlabeled__"] = by_class.get(
                    shape.workload_class or "__unlabeled__", 0
                ) + 1
            if any(count < policy.minimum_held_out_per_workload_class for count in by_class.values()):
                raise RuntimeError(
                    "reportable run does not satisfy minimum held-out shapes per workload class"
                )
        if compatibility is not None and policy.abort_on_incompatible_counter_set and not compatibility.acceptable:
            if (
                spec.profile_policy is not None
                and spec.profile_policy.availability_failure_mode == "downgrade_to_diagnostic"
            ):
                warnings.append(
                    "counter set "
                    f"'{compatibility.counter_set_id}' is not acceptable for reportable use; "
                    "downgrading this run to diagnostic/non-comparable evidence"
                )
            else:
                raise RuntimeError(
                    f"counter set '{compatibility.counter_set_id}' is not acceptable for reportable use"
                )
    return warnings


@contextmanager
def _isolated_caches(spec: ExperimentSpec, store: RunStore):
    previous = os.environ.get("TRITON_CACHE_DIR")
    if spec.execution_settings.isolate_triton_cache:
        cache_dir = store.run_dir / "cache" / "triton"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["TRITON_CACHE_DIR"] = str(cache_dir)
    try:
        yield
    finally:
        if spec.execution_settings.isolate_triton_cache:
            if previous is None:
                os.environ.pop("TRITON_CACHE_DIR", None)
            else:
                os.environ["TRITON_CACHE_DIR"] = previous


def _register_raw_samples(
    store: RunStore,
    strategy_id: str,
    measurement_phase: MeasurementPhase,
    measurement: RuntimeMeasurement,
    raw_samples_us: list[float] | None,
) -> RuntimeMeasurement:
    if not raw_samples_us:
        return measurement
    path = store.register_log_file(
        f"samples/{strategy_id}_{measurement_phase.value}_{measurement.shape_id}_{measurement.config_id}.json",
        json.dumps(raw_samples_us),
    )
    return measurement.model_copy(
        update={"raw_sample_ref": path.relative_to(store.run_dir).as_posix()}
    )


def _register_profile_logs(
    store: RunStore,
    strategy_id: str,
    measurement: ProfileMeasurement,
    *,
    stdout: str,
    stderr: str,
) -> ProfileMeasurement:
    updates: dict[str, str] = {}
    if stdout:
        stdout_path = store.register_log_file(
            f"profile/{strategy_id}_{measurement.shape_id}_{measurement.config_id}.stdout.txt",
            stdout,
        )
        updates["profiler_stdout_ref"] = stdout_path.relative_to(store.run_dir).as_posix()
    if stderr:
        stderr_path = store.register_log_file(
            f"profile/{strategy_id}_{measurement.shape_id}_{measurement.config_id}.stderr.txt",
            stderr,
        )
        updates["profiler_stderr_ref"] = stderr_path.relative_to(store.run_dir).as_posix()
    return measurement.model_copy(update=updates) if updates else measurement


class StrategyBroker:
    def __init__(
        self,
        *,
        store: RunStore,
        run_id: str,
        strategy_id: str,
        kernel,
        kernel_id: str,
        candidate_records: list[CandidateConfig],
        calibration_shapes,
        held_out_shapes,
        experiment_spec: ExperimentSpec,
        counter_set,
        profile_shapes,
        selector_revision: SelectorRevisionSpec | None,
        deadline_s: float | None,
    ) -> None:
        self.store = store
        self.run_id = run_id
        self.strategy_id = strategy_id
        self.kernel = kernel
        self.kernel_id = kernel_id
        self.calibration_shapes = list(calibration_shapes)
        self.held_out_shapes = list(held_out_shapes)
        self.profile_shapes = list(profile_shapes)
        self.experiment_spec = experiment_spec
        self.counter_set = counter_set
        self.selector_revision = selector_revision
        self.deadline_s = deadline_s
        self._candidate_lookup = {
            (candidate.shape_id, candidate.config_id): candidate for candidate in candidate_records
        }
        self._runtime_cache: dict[tuple[str, MeasurementPhase], list[RuntimeMeasurement]] = {}
        self._profile_cache: dict[str, list[ProfileMeasurement]] = {}
        self.runtime_records: list[RuntimeMeasurement] = []
        self.profile_records: list[ProfileMeasurement] = []
        self._measurement_order_index = 0

    def _budget_exhausted(self) -> bool:
        return self.deadline_s is not None and time.perf_counter() >= self.deadline_s

    def benchmark_calibration(self, config_id: str) -> list[RuntimeMeasurement]:
        return self._benchmark_shapes(config_id, self.calibration_shapes, MeasurementPhase.CALIBRATION)

    def benchmark_held_out(self, config_id: str) -> list[RuntimeMeasurement]:
        return self._benchmark_shapes(config_id, self.held_out_shapes, MeasurementPhase.HELD_OUT)

    def _benchmark_shapes(self, config_id: str, shapes, phase: MeasurementPhase) -> list[RuntimeMeasurement]:
        cache_key = (config_id, phase)
        if cache_key in self._runtime_cache:
            return self._runtime_cache[cache_key]

        records: list[RuntimeMeasurement] = []
        for index, shape in enumerate(shapes):
            if self._budget_exhausted():
                skipped = RuntimeMeasurement(
                    run_id=self.run_id,
                    strategy_id=self.strategy_id,
                    measurement_phase=phase,
                    kernel_id=self.kernel.spec.kernel_id,
                    shape_id=shape.shape_id,
                    config_id=config_id,
                    warmup_count=self.experiment_spec.benchmark_settings.warmup_iterations,
                    timed_run_count=self.experiment_spec.benchmark_settings.timed_iterations,
                    latency_median_us=None,
                    latency_mean_us=None,
                    latency_std_us=None,
                    latency_p95_us=None,
                    throughput_value=None,
                    throughput_unit=None,
                    status=RuntimeStatus.SKIPPED_BUDGET,
                    timing_backend=self.experiment_spec.benchmark_settings.timing_backend,
                    measurement_order_index=self._measurement_order_index,
                    error_message="wall_clock_limit_s exhausted before benchmark",
                )
                records.append(skipped)
                self.runtime_records.append(skipped)
                self._measurement_order_index += 1
                continue
            candidate = self._candidate_lookup[(shape.shape_id, config_id)]
            outcome = benchmark_candidate(
                run_id=self.run_id,
                strategy_id=self.strategy_id,
                kernel=self.kernel,
                shape=shape,
                candidate=candidate,
                settings=self.experiment_spec.benchmark_settings,
                seed=self.experiment_spec.seed + index,
                measurement_phase=phase,
                measurement_order_index=self._measurement_order_index,
            )
            measurement = _register_raw_samples(
                self.store,
                self.strategy_id,
                phase,
                outcome.measurement,
                outcome.raw_samples_us,
            )
            records.append(measurement)
            self.runtime_records.append(measurement)
            self._measurement_order_index += 1
        self._runtime_cache[cache_key] = records
        return records

    def profile_calibration(self, config_id: str) -> list[ProfileMeasurement]:
        if self.counter_set is None or not self.profile_shapes:
            return []
        if config_id in self._profile_cache:
            return self._profile_cache[config_id]

        measurements: list[ProfileMeasurement] = []
        for shape in self.profile_shapes:
            if self._budget_exhausted():
                measurement = ProfileMeasurement(
                    run_id=self.run_id,
                    strategy_id=self.strategy_id,
                    kernel_id=self.kernel_id,
                    shape_id=shape.shape_id,
                    config_id=config_id,
                    counter_set_id=self.counter_set.counter_set_id,
                    profile_status=ProfileStatus.SKIPPED_BUDGET,
                    notes="wall_clock_limit_s exhausted before profiling",
                )
                self.profile_records.append(measurement)
                measurements.append(measurement)
                continue
            candidate = self._candidate_lookup[(shape.shape_id, config_id)]
            outcome = profile_candidate(
                run_id=self.run_id,
                strategy_id=self.strategy_id,
                kernel_id=self.kernel_id,
                shape=shape,
                candidate=candidate,
                counter_set=self.counter_set,
                experiment_spec=self.experiment_spec,
            )
            measurement = _register_profile_logs(
                self.store,
                self.strategy_id,
                outcome.measurement,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
            )
            self.profile_records.append(measurement)
            measurements.append(measurement)
        self._profile_cache[config_id] = measurements
        return measurements


def run_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
    run_id: str | None = None,
    repeat_index: int | None = None,
    campaign_id: str | None = None,
    round_id: str | None = None,
) -> dict[str, object]:
    artifact_root = resolve_artifact_root(experiment_spec.artifact_root, experiment_path)
    run_id = run_id or make_run_id()
    store = RunStore(artifact_root, experiment_spec.experiment_id, run_id)
    environment = capture_environment_metadata(Path.cwd())
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
    counter_set = (
        load_counter_set(counter_set_path(experiment_spec.counter_set_id, experiment_path))
        if experiment_spec.counter_set_id
        else None
    )
    counter_compatibility = validate_counter_set_for_experiment(
        experiment_spec,
        experiment_path=experiment_path,
    )
    selector_revision = (
        load_selector_revision_spec(selector_revision_path(experiment_spec.selector_revision_id, experiment_path))
        if experiment_spec.selector_revision_id
        else None
    )
    labels = _run_labels(
        experiment_spec=experiment_spec,
        kernel_family=kernel_spec.family,
        counter_set_id=counter_set.counter_set_id if counter_set is not None else None,
        repeat_index=repeat_index,
        campaign_id=campaign_id,
        round_id=round_id,
    )
    manifest = Manifest(
        experiment_id=experiment_spec.experiment_id,
        run_id=run_id,
        created_at_utc=datetime.now(timezone.utc),
        git_commit=environment.git_commit,
        git_branch=environment.git_branch,
        git_dirty=environment.git_dirty,
        environment=environment,
        invocation=capture_invocation_metadata(
            "ktune run-experiment",
            experiment_config_path=str(Path(experiment_path).resolve()) if experiment_path else None,
            counter_config_path=(
                str(counter_set_path(experiment_spec.counter_set_id, experiment_path))
                if experiment_spec.counter_set_id
                else None
            ),
            seed=experiment_spec.seed,
            repeat_index=repeat_index,
            selector_revision_id=experiment_spec.selector_revision_id,
            campaign_id=campaign_id,
        ),
        slurm=capture_slurm_metadata(),
        artifact_files=[],
        status=RunStatus.CREATED,
        warnings=[],
        labels=labels,
    )
    store.initialize_manifest(manifest)

    try:
        _validate_environment(experiment_spec, environment)
        calibration_shapes, held_out_shapes = _shape_split(experiment_spec)
        warnings = _validate_reportability_contract(
            experiment_spec,
            calibration_shapes,
            held_out_shapes,
            counter_compatibility,
        )
        store.write_experiment_spec(experiment_spec)
        if counter_compatibility is not None:
            store.write_json_artifact(
                "counter_compatibility",
                counter_compatibility.model_dump(mode="json"),
                filename="counter_compatibility.json",
            )

        pip_freeze = subprocess.run(
            [python_command(), "-m", "pip", "freeze"],
            check=False,
            capture_output=True,
            text=True,
        )
        if pip_freeze.stdout:
            store.register_log_file("pip_freeze.txt", pip_freeze.stdout)

        kernel = resolve_kernel(kernel_spec)
        profile_shapes = _profile_shapes(experiment_spec, calibration_shapes)
        deadline_s = (
            time.perf_counter() + experiment_spec.budgets.wall_clock_limit_s
            if experiment_spec.budgets.wall_clock_limit_s is not None
            else None
        )
        candidate_records = generate_candidate_records(experiment_spec, experiment_path=experiment_path)
        store.write_table("candidates", candidate_records)

        compile_signal_records = []
        with _isolated_caches(experiment_spec, store):
            for index, shape in enumerate(experiment_spec.shapes):
                shape_candidates = [
                    candidate for candidate in candidate_records if candidate.shape_id == shape.shape_id
                ]
                compile_signal_records.extend(
                    collect_compile_signals(
                        run_id=run_id,
                        kernel=kernel,
                        shape=shape,
                        candidates=shape_candidates,
                        seed=experiment_spec.seed + (index * 1000),
                    )
                )
        store.write_table("compile_signals", compile_signal_records)

        calibration_candidate_records = [
            candidate for candidate in candidate_records if candidate.shape_id in {shape.shape_id for shape in calibration_shapes}
        ]
        calibration_compile_signals = [
            record for record in compile_signal_records if record.shape_id in {shape.shape_id for shape in calibration_shapes}
        ]

        runtime_measurements: list[RuntimeMeasurement] = []
        profile_measurements: list[ProfileMeasurement] = []
        selection_decisions = []
        for selector_mode in experiment_spec.selector_modes:
            strategy_id = _mode_name(selector_mode)
            broker = StrategyBroker(
                store=store,
                run_id=run_id,
                strategy_id=strategy_id,
                kernel=kernel,
                kernel_id=kernel_spec.kernel_id,
                candidate_records=candidate_records,
                calibration_shapes=calibration_shapes,
                held_out_shapes=held_out_shapes,
                experiment_spec=experiment_spec,
                counter_set=counter_set,
                profile_shapes=profile_shapes,
                selector_revision=selector_revision,
                deadline_s=deadline_s,
            )
            with _isolated_caches(experiment_spec, store):
                decision = run_selector_mode(
                    run_id=run_id,
                    strategy_id=strategy_id,
                    selector_mode=selector_mode,
                    kernel_id=kernel_spec.kernel_id,
                    candidate_records=calibration_candidate_records,
                    compile_signals=calibration_compile_signals,
                    budgets=experiment_spec.budgets,
                    request_benchmark=broker.benchmark_calibration,
                    request_profile=broker.profile_calibration if counter_set is not None else None,
                    selector_revision=selector_revision,
                )
                if decision.selected_config_id and held_out_shapes:
                    broker.benchmark_held_out(decision.selected_config_id)
            decision.comparison_class = _comparison_class_for_run(
                experiment_spec,
                counter_compatibility,
            )
            selection_decisions.append(decision)
            runtime_measurements.extend(broker.runtime_records)
            profile_measurements.extend(broker.profile_records)
            if decision.decision_status.startswith("failed"):
                warnings.append(f"{strategy_id}: {decision.decision_status}")

        for baseline_mode in experiment_spec.baselines:
            strategy_id = _mode_name(baseline_mode)
            broker = StrategyBroker(
                store=store,
                run_id=run_id,
                strategy_id=strategy_id,
                kernel=kernel,
                kernel_id=kernel_spec.kernel_id,
                candidate_records=candidate_records,
                calibration_shapes=calibration_shapes,
                held_out_shapes=held_out_shapes,
                experiment_spec=experiment_spec,
                counter_set=None,
                profile_shapes=[],
                selector_revision=None,
                deadline_s=deadline_s,
            )
            with _isolated_caches(experiment_spec, store):
                decision = run_baseline_mode(
                    run_id=run_id,
                    strategy_id=strategy_id,
                    baseline_mode=baseline_mode,
                    kernel_id=kernel_spec.kernel_id,
                    candidate_records=calibration_candidate_records,
                    budgets=experiment_spec.budgets,
                    seed=experiment_spec.seed,
                    default_config=kernel_spec.default_config,
                    request_benchmark=broker.benchmark_calibration,
                )
                if decision.selected_config_id and held_out_shapes:
                    broker.benchmark_held_out(decision.selected_config_id)
            decision.comparison_class = _comparison_class_for_run(
                experiment_spec,
                counter_compatibility,
            )
            selection_decisions.append(decision)
            runtime_measurements.extend(broker.runtime_records)
            profile_measurements.extend(broker.profile_records)
            if decision.decision_status.startswith("failed"):
                warnings.append(f"{strategy_id}: {decision.decision_status}")

        store.write_table("runtime_measurements", runtime_measurements)
        store.write_table("profile_measurements", profile_measurements)
        store.write_table("selection_decisions", selection_decisions)
        terminal_status = RunStatus.SUCCESS if not warnings else RunStatus.PARTIAL_FAILURE
        store.finalize(terminal_status, warnings=warnings)
        summary = summarize_run(store.run_dir)
        return {
            "experiment_id": experiment_spec.experiment_id,
            "run_id": run_id,
            "run_dir": str(store.run_dir),
            "terminal_status": terminal_status.value,
            "summary_path": str(store.run_dir / "summary.json"),
            "selected_configs": summary["best_configs"],
        }
    except Exception as exc:
        store.finalize(RunStatus.FAILED, warnings=[str(exc)])
        raise
