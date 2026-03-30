"""Configuration space generation."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

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
        tuple(sorted(record.config.items())),
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
        config=dict(sorted(config.items())),
        shape_dimensions=dict(sorted(shape.dimensions.items())),
        workload_class=shape.workload_class,
        is_valid=is_valid,
        validation_notes=validation_notes,
        generation_provenance=generation_provenance,
    )


class CandidateSpaceOverflowError(RuntimeError):
    """Raised when the globally valid candidate set exceeds the declared budget."""

    def __init__(
        self,
        *,
        experiment_id: str,
        kernel_id: str,
        max_candidates: int,
        raw_config_count: int,
        valid_config_count: int,
    ) -> None:
        self.metadata = {
            "experiment_id": experiment_id,
            "kernel_id": kernel_id,
            "max_candidates": max_candidates,
            "raw_config_count": raw_config_count,
            "valid_config_count": valid_config_count,
            "overflowed": True,
        }
        super().__init__(
            "candidate space overflow for "
            f"experiment '{experiment_id}' kernel '{kernel_id}': "
            f"{valid_config_count} globally valid configs exceed max_candidates={max_candidates}; "
            "increase budgets.max_candidates or reduce the declared config space"
        )


def config_dict_from_record(record: CandidateConfig) -> dict[str, int]:
    return dict(record.config)


def _generation_provenance(
    *,
    raw_config_count: int,
    valid_config_count: int,
    max_candidates: int,
) -> str:
    return (
        "cartesian_product|global_validation"
        f"|raw_config_count={raw_config_count}"
        f"|valid_config_count={valid_config_count}"
        f"|max_candidates={max_candidates}"
    )


def generate_candidate_bundle(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, Any]:
    all_candidates: list[CandidateConfig] = []
    kernel_summaries: list[dict[str, Any]] = []
    for kernel_id in experiment_spec.kernels:
        spec = load_kernel_spec(kernel_config_path(kernel_id, experiment_path))
        kernel = resolve_kernel(spec)
        if experiment_spec.explicit_configs:
            raw_configs = [dict(sorted(config.items())) for config in experiment_spec.explicit_configs]
        else:
            parameter_names = _ordered_parameter_names(spec)
            value_sets = [spec.config_parameters[name] for name in parameter_names]
            raw_configs = [dict(zip(parameter_names, values, strict=False)) for values in itertools.product(*value_sets)]
        globally_valid_configs: list[dict[str, int]] = []
        for config in raw_configs:
            if all(kernel.supports_config(shape, config)[0] for shape in experiment_spec.shapes):
                globally_valid_configs.append(config)

        raw_config_count = len(raw_configs)
        valid_config_count = len(globally_valid_configs)
        if valid_config_count > experiment_spec.budgets.max_candidates:
            raise CandidateSpaceOverflowError(
                experiment_id=experiment_spec.experiment_id,
                kernel_id=kernel_id,
                max_candidates=experiment_spec.budgets.max_candidates,
                raw_config_count=raw_config_count,
                valid_config_count=valid_config_count,
            )

        generation_provenance = _generation_provenance(
            raw_config_count=raw_config_count,
            valid_config_count=valid_config_count,
            max_candidates=experiment_spec.budgets.max_candidates,
        )
        kernel_summaries.append(
            {
                "kernel_id": kernel_id,
                "raw_config_count": raw_config_count,
                "valid_config_count": valid_config_count,
                "max_candidates": experiment_spec.budgets.max_candidates,
                "overflowed": False,
                "generation_provenance": generation_provenance,
            }
        )
        for shape in experiment_spec.shapes:
            for config in globally_valid_configs:
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
    ordered = sorted(deduped.values(), key=_candidate_sort_key)
    return {
        "records": ordered,
        "metadata": {
            "experiment_id": experiment_spec.experiment_id,
            "kernel_summaries": kernel_summaries,
            "raw_config_count": sum(summary["raw_config_count"] for summary in kernel_summaries),
            "valid_config_count": sum(summary["valid_config_count"] for summary in kernel_summaries),
            "candidate_record_count": len(ordered),
            "overflowed": False,
        },
    }


def generate_candidate_records(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> list[CandidateConfig]:
    return generate_candidate_bundle(experiment_spec, experiment_path=experiment_path)["records"]


def generate_candidate_configs(
    experiment_spec: ExperimentSpec,
    *,
    emit_artifacts: bool = False,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    bundle = generate_candidate_bundle(experiment_spec, experiment_path=experiment_path)
    ordered = bundle["records"]
    return {
        "candidate_count": len(ordered),
        "records": [record.model_dump(mode="json") for record in ordered],
        "config_ids": [record.config_id for record in ordered],
        "config_space_signature": canonical_config_id(
            {"records": [json.dumps(record.config, sort_keys=True) for record in ordered]}
        ),
        "generation_metadata": bundle["metadata"],
    }
