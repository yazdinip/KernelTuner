"""Configuration space generation."""

from __future__ import annotations

import itertools
from pathlib import Path

from kernel_tuner.common.config import kernel_config_path, load_kernel_spec
from kernel_tuner.common.ids import canonical_config_id
from kernel_tuner.common.schema import CandidateConfig, ExperimentSpec, KernelSpec, ProblemShape
from kernel_tuner.kernels.registry import resolve_kernel


def _ordered_parameter_names(spec: KernelSpec) -> list[str]:
    return sorted(spec.config_parameters)


def _candidate_sort_key(record: CandidateConfig) -> tuple[object, ...]:
    return (
        record.kernel_id,
        record.shape_id,
        record.block_m,
        record.block_n,
        record.block_k,
        record.num_warps,
        record.num_stages,
        record.config_id,
    )


def _candidate_record(
    experiment_id: str,
    kernel_id: str,
    shape: ProblemShape,
    config: dict[str, int],
    *,
    is_valid: bool,
    validation_notes: str | None,
    generation_provenance: str,
) -> CandidateConfig:
    return CandidateConfig(
        experiment_id=experiment_id,
        kernel_id=kernel_id,
        shape_id=shape.shape_id,
        config_id=canonical_config_id(config),
        block_m=config["block_m"],
        block_n=config["block_n"],
        block_k=config["block_k"],
        num_warps=config["num_warps"],
        num_stages=config["num_stages"],
        is_valid=is_valid,
        validation_notes=validation_notes,
        generation_provenance=generation_provenance,
    )


def config_dict_from_record(record: CandidateConfig) -> dict[str, int]:
    return {
        "block_m": record.block_m,
        "block_n": record.block_n,
        "block_k": record.block_k,
        "num_warps": record.num_warps,
        "num_stages": record.num_stages,
    }


def generate_candidate_records(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> list[CandidateConfig]:
    all_candidates: list[CandidateConfig] = []
    for kernel_id in experiment_spec.kernels:
        spec = load_kernel_spec(kernel_config_path(kernel_id, experiment_path))
        kernel = resolve_kernel(spec)
        parameter_names = _ordered_parameter_names(spec)
        value_sets = [spec.config_parameters[name] for name in parameter_names]
        raw_configs = [dict(zip(parameter_names, values)) for values in itertools.product(*value_sets)]
        config_ids = sorted({canonical_config_id(config) for config in raw_configs})
        selected_config_ids = set(config_ids[: experiment_spec.budgets.max_candidates])
        generation_provenance = "cartesian_product"
        if len(config_ids) > len(selected_config_ids):
            generation_provenance = "cartesian_product|max_candidates_truncation"

        for shape in experiment_spec.shapes:
            for config in raw_configs:
                config_id = canonical_config_id(config)
                if config_id not in selected_config_ids:
                    continue
                valid, reason = kernel.supports_config(shape, config)
                all_candidates.append(
                    _candidate_record(
                        experiment_spec.experiment_id,
                        kernel_id,
                        shape,
                        config,
                        is_valid=valid,
                        validation_notes=reason,
                        generation_provenance=generation_provenance,
                    )
                )

    deduped = {
        (record.kernel_id, record.shape_id, record.config_id): record
        for record in all_candidates
    }
    return sorted(deduped.values(), key=_candidate_sort_key)


def generate_candidate_configs(
    experiment_spec: ExperimentSpec,
    *,
    emit_artifacts: bool = False,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    ordered = generate_candidate_records(experiment_spec, experiment_path=experiment_path)
    return {
        "candidate_count": len(ordered),
        "records": [record.model_dump(mode="json") for record in ordered],
    }
