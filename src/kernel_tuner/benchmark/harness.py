"""Benchmark harness."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from kernel_tuner.common.config import kernel_config_path, load_kernel_spec
from kernel_tuner.common.schema import (
    BenchmarkSettings,
    CandidateConfig,
    ExperimentSpec,
    MeasurementPhase,
    ProblemShape,
    RuntimeMeasurement,
    RuntimeStatus,
)
from kernel_tuner.config_space.generator import config_dict_from_record, generate_candidate_records
from kernel_tuner.kernels.registry import resolve_kernel


@dataclass
class BenchmarkOutcome:
    measurement: RuntimeMeasurement
    raw_samples_us: list[float] | None = None


def _status_measurement(
    *,
    run_id: str,
    strategy_id: str,
    measurement_phase: MeasurementPhase,
    kernel_id: str,
    shape_id: str,
    config_id: str,
    settings: BenchmarkSettings,
    status: RuntimeStatus,
    measurement_order_index: int,
    error_message: str | None,
) -> RuntimeMeasurement:
    return RuntimeMeasurement(
        run_id=run_id,
        strategy_id=strategy_id,
        measurement_phase=measurement_phase,
        kernel_id=kernel_id,
        shape_id=shape_id,
        config_id=config_id,
        warmup_count=settings.warmup_iterations,
        timed_run_count=settings.timed_iterations,
        latency_median_us=None,
        latency_mean_us=None,
        latency_std_us=None,
        latency_p95_us=None,
        throughput_value=None,
        throughput_unit=None,
        status=status,
        timing_backend=settings.timing_backend,
        measurement_order_index=measurement_order_index,
        error_message=error_message,
    )


def _percentile(sorted_samples: list[float], percentile: float) -> float:
    index = int(round((len(sorted_samples) - 1) * percentile))
    return sorted_samples[index]


def benchmark_candidate(
    *,
    run_id: str,
    strategy_id: str,
    kernel,
    shape: ProblemShape,
    candidate: CandidateConfig,
    settings: BenchmarkSettings,
    seed: int,
    measurement_phase: MeasurementPhase,
    measurement_order_index: int = 0,
) -> BenchmarkOutcome:
    import torch

    config = config_dict_from_record(candidate)
    valid, reason = kernel.supports_config(shape, config)
    if not valid or not candidate.is_valid:
        return BenchmarkOutcome(
            measurement=_status_measurement(
                run_id=run_id,
                strategy_id=strategy_id,
                measurement_phase=measurement_phase,
                kernel_id=kernel.spec.kernel_id,
                shape_id=shape.shape_id,
                config_id=candidate.config_id,
                settings=settings,
                status=RuntimeStatus.INVALID_CONFIG,
                measurement_order_index=measurement_order_index,
                error_message=reason or candidate.validation_notes,
            )
        )

    inputs = kernel.make_inputs(shape, seed=seed)
    try:
        output = kernel.run_kernel(inputs, shape, config)
        torch.cuda.synchronize()
    except Exception as exc:
        return BenchmarkOutcome(
            measurement=_status_measurement(
                run_id=run_id,
                strategy_id=strategy_id,
                measurement_phase=measurement_phase,
                kernel_id=kernel.spec.kernel_id,
                shape_id=shape.shape_id,
                config_id=candidate.config_id,
                settings=settings,
                status=RuntimeStatus.COMPILE_FAILED,
                measurement_order_index=measurement_order_index,
                error_message=str(exc),
            )
        )

    reference = kernel.reference_impl(inputs, kernel.spec.correctness_policy)
    if not kernel.validate_output(output, reference, kernel.spec.correctness_policy):
        return BenchmarkOutcome(
            measurement=_status_measurement(
                run_id=run_id,
                strategy_id=strategy_id,
                measurement_phase=measurement_phase,
                kernel_id=kernel.spec.kernel_id,
                shape_id=shape.shape_id,
                config_id=candidate.config_id,
                settings=settings,
                status=RuntimeStatus.RUNTIME_FAILED,
                measurement_order_index=measurement_order_index,
                error_message="correctness validation failed",
            )
        )

    stream = torch.cuda.Stream()
    with torch.cuda.stream(stream):
        for _ in range(settings.warmup_iterations):
            kernel.run_kernel(inputs, shape, config)
        stream.synchronize()

        samples: list[float] = []
        for _ in range(settings.timed_iterations):
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record(stream)
            kernel.run_kernel(inputs, shape, config)
            end.record(stream)
            end.synchronize()
            samples.append(start.elapsed_time(end) * 1000.0)

    sorted_samples = sorted(samples)
    median_us = statistics.median(sorted_samples)
    mean_us = statistics.fmean(sorted_samples)
    std_us = statistics.pstdev(sorted_samples) if len(sorted_samples) > 1 else 0.0
    p95_us = _percentile(sorted_samples, 0.95)
    throughput_value, throughput_unit = kernel.performance_metric(shape, config, median_us)
    measurement = RuntimeMeasurement(
        run_id=run_id,
        strategy_id=strategy_id,
        measurement_phase=measurement_phase,
        kernel_id=kernel.spec.kernel_id,
        shape_id=shape.shape_id,
        config_id=candidate.config_id,
        warmup_count=settings.warmup_iterations,
        timed_run_count=settings.timed_iterations,
        latency_median_us=median_us,
        latency_mean_us=mean_us,
        latency_std_us=std_us,
        latency_p95_us=p95_us,
        throughput_value=throughput_value,
        throughput_unit=throughput_unit,
        status=RuntimeStatus.SUCCESS,
        timing_backend=settings.timing_backend,
        measurement_order_index=measurement_order_index,
    )
    return BenchmarkOutcome(
        measurement=measurement,
        raw_samples_us=samples if settings.store_raw_samples else None,
    )


def benchmark_candidates_for_shape(
    *,
    run_id: str,
    strategy_id: str,
    kernel,
    shape: ProblemShape,
    candidates: Iterable[CandidateConfig],
    settings: BenchmarkSettings,
    seed: int,
    measurement_phase: MeasurementPhase,
    start_order_index: int = 0,
) -> list[BenchmarkOutcome]:
    outcomes: list[BenchmarkOutcome] = []
    for offset, candidate in enumerate(candidates):
        outcomes.append(
            benchmark_candidate(
                run_id=run_id,
                strategy_id=strategy_id,
                kernel=kernel,
                shape=shape,
                candidate=candidate,
                settings=settings,
                seed=seed + offset,
                measurement_phase=measurement_phase,
                measurement_order_index=start_order_index + offset,
            )
        )
    return outcomes


def benchmark_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
    kernel = resolve_kernel(kernel_spec)
    candidates = generate_candidate_records(experiment_spec, experiment_path=experiment_path)
    first_shape = experiment_spec.shapes[0]
    shape_candidates = [
        candidate for candidate in candidates if candidate.shape_id == first_shape.shape_id
    ]
    default_candidate = next(
        (
            candidate
            for candidate in shape_candidates
            if config_dict_from_record(candidate) == (kernel_spec.default_config or {})
        ),
        shape_candidates[0],
    )
    outcome = benchmark_candidate(
        run_id="standalone",
        strategy_id="benchmark_cli",
        kernel=kernel,
        shape=first_shape,
        candidate=default_candidate,
        settings=experiment_spec.benchmark_settings,
        seed=experiment_spec.seed,
        measurement_phase=MeasurementPhase.CALIBRATION,
    )
    return outcome.measurement.model_dump(mode="json")
