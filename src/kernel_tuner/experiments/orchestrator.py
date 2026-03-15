"""Experiment orchestration."""

from __future__ import annotations

import json
import os
import random
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from kernel_tuner.analysis.reporting import summarize_run
from kernel_tuner.baselines.strategies import run_baseline_mode
from kernel_tuner.benchmark.harness import benchmark_candidate
from kernel_tuner.common.config import (
    counter_set_path,
    kernel_config_path,
    load_counter_set,
    load_kernel_spec,
    resolve_artifact_root,
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
    ExperimentSpec,
    Manifest,
    MeasurementPhase,
    ProfileMeasurement,
    ProfileStatus,
    RunStatus,
    RuntimeMeasurement,
)
from kernel_tuner.config_space.generator import generate_candidate_records
from kernel_tuner.kernels.registry import resolve_kernel
from kernel_tuner.profiling.adapter import profile_candidate
from kernel_tuner.selector.engine import run_selector_mode
from kernel_tuner.signals.collector import collect_compile_signals
from kernel_tuner.storage import RunStore


def _mode_name(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _shape_split(spec: ExperimentSpec):
    ordered = sorted(spec.shapes, key=lambda shape: shape.shape_id)
    if len(ordered) <= 1 or spec.held_out_split <= 0.0:
        return ordered, []
    rng = random.Random(spec.seed)
    shuffled = ordered[:]
    rng.shuffle(shuffled)
    calibration_count = round(len(shuffled) * spec.calibration_split)
    calibration_count = max(1, min(len(shuffled) - 1, calibration_count))
    calibration = sorted(shuffled[:calibration_count], key=lambda shape: shape.shape_id)
    held_out = sorted(shuffled[calibration_count:], key=lambda shape: shape.shape_id)
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
    ) -> None:
        self.store = store
        self.run_id = run_id
        self.strategy_id = strategy_id
        self.kernel = kernel
        self.kernel_id = kernel_id
        self.calibration_shapes = list(calibration_shapes)
        self.held_out_shapes = list(held_out_shapes)
        self.experiment_spec = experiment_spec
        self.counter_set = counter_set
        self._candidate_lookup = {
            (candidate.shape_id, candidate.config_id): candidate for candidate in candidate_records
        }
        self._runtime_cache: dict[tuple[str, MeasurementPhase], list[RuntimeMeasurement]] = {}
        self._profile_cache: dict[str, list[ProfileMeasurement]] = {}
        self.runtime_records: list[RuntimeMeasurement] = []
        self.profile_records: list[ProfileMeasurement] = []
        self._measurement_order_index = 0

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
        if self.counter_set is None or not self.calibration_shapes:
            return []
        if config_id in self._profile_cache:
            return self._profile_cache[config_id]

        shape = self.calibration_shapes[0]
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
        self._profile_cache[config_id] = [measurement]
        return [measurement]


def run_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    artifact_root = resolve_artifact_root(experiment_spec.artifact_root, experiment_path)
    run_id = make_run_id()
    store = RunStore(artifact_root, experiment_spec.experiment_id, run_id)
    environment = capture_environment_metadata(Path.cwd())
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
        ),
        slurm=capture_slurm_metadata(),
        artifact_files=[],
        status=RunStatus.CREATED,
        warnings=[],
    )
    store.initialize_manifest(manifest)

    try:
        _validate_environment(experiment_spec, environment)
        store.write_experiment_spec(experiment_spec)

        pip_freeze = subprocess.run(
            [python_command(), "-m", "pip", "freeze"],
            check=False,
            capture_output=True,
            text=True,
        )
        if pip_freeze.stdout:
            store.register_log_file("pip_freeze.txt", pip_freeze.stdout)

        kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
        kernel = resolve_kernel(kernel_spec)
        counter_set = (
            load_counter_set(counter_set_path(experiment_spec.counter_set_id, experiment_path))
            if experiment_spec.counter_set_id
            else None
        )
        calibration_shapes, held_out_shapes = _shape_split(experiment_spec)
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
        warnings: list[str] = []

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
                )
                if decision.selected_config_id and held_out_shapes:
                    broker.benchmark_held_out(decision.selected_config_id)
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
