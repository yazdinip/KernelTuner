"""Compile signal collection."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from kernel_tuner.common.config import kernel_config_path, load_kernel_spec
from kernel_tuner.common.schema import CandidateConfig, CompileSignalRecord, ExperimentSpec
from kernel_tuner.config_space.generator import config_dict_from_record, generate_candidate_bundle
from kernel_tuner.kernels.registry import resolve_kernel


def collect_compile_signal(
    *,
    run_id: str,
    kernel,
    shape,
    candidate: CandidateConfig,
    seed: int,
) -> CompileSignalRecord:
    config = config_dict_from_record(candidate)
    valid, reason = kernel.supports_config(shape, config)
    if not valid or not candidate.is_valid:
        return CompileSignalRecord(
            run_id=run_id,
            kernel_id=kernel.spec.kernel_id,
            shape_id=shape.shape_id,
            config_id=candidate.config_id,
            compile_status="invalid_config",
            compile_success=False,
            signal_backend="preflight_validation",
            notes=reason or candidate.validation_notes,
        )

    try:
        inputs = kernel.make_inputs(shape, seed=seed)
        metadata = kernel.compile_metadata(inputs, shape, config)
        return CompileSignalRecord(
            run_id=run_id,
            kernel_id=kernel.spec.kernel_id,
            shape_id=shape.shape_id,
            config_id=candidate.config_id,
            compile_status="success",
            compile_success=True,
            register_count=metadata.get("register_count"),
            shared_memory_bytes=metadata.get("shared_memory_bytes"),
            occupancy_estimate=metadata.get("occupancy_estimate"),
            signal_backend=metadata.get("signal_backend"),
            occupancy_method=metadata.get("occupancy_method"),
            notes=metadata.get("notes"),
        )
    except Exception as exc:
        return CompileSignalRecord(
            run_id=run_id,
            kernel_id=kernel.spec.kernel_id,
            shape_id=shape.shape_id,
            config_id=candidate.config_id,
            compile_status="compile_failed",
            compile_success=False,
            notes=str(exc),
        )


def collect_compile_signals(
    *,
    run_id: str,
    kernel,
    shape,
    candidates: Iterable[CandidateConfig],
    seed: int,
) -> list[CompileSignalRecord]:
    return [
        collect_compile_signal(
            run_id=run_id,
            kernel=kernel,
            shape=shape,
            candidate=candidate,
            seed=seed + index,
        )
        for index, candidate in enumerate(candidates)
    ]


def collect_signals_for_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
    kernel = resolve_kernel(kernel_spec)
    candidate_bundle = generate_candidate_bundle(experiment_spec, experiment_path=experiment_path)
    candidates = candidate_bundle["records"]
    records = []
    for index, shape in enumerate(experiment_spec.shapes):
        shape_candidates = [
            candidate for candidate in candidates if candidate.shape_id == shape.shape_id
        ]
        records.extend(
            collect_compile_signals(
                run_id="standalone",
                kernel=kernel,
                shape=shape,
                candidates=shape_candidates,
                seed=experiment_spec.seed + index,
            )
        )
    return {
        "experiment_id": experiment_spec.experiment_id,
        "record_count": len(records),
        "records": [record.model_dump(mode="json") for record in records],
        "generation_metadata": candidate_bundle["metadata"],
    }
