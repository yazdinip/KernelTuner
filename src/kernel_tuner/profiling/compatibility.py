"""Counter-set compatibility validation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from kernel_tuner.common.config import (
    counter_set_path,
    kernel_config_path,
    load_counter_set,
    load_experiment_spec,
    load_kernel_spec,
)
from kernel_tuner.common.schema import CounterCompatibilityRecord, ExperimentSpec


def validate_counter_set_for_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> CounterCompatibilityRecord | None:
    counter_set_id = (
        experiment_spec.profile_policy.counter_set_id if experiment_spec.profile_policy else None
    ) or experiment_spec.counter_set_id
    if not counter_set_id:
        return None
    counter_set = load_counter_set(counter_set_path(counter_set_id, experiment_path))
    kernel_spec = load_kernel_spec(kernel_config_path(experiment_spec.kernels[0], experiment_path))
    return validate_counter_set(counter_set, kernel_family=kernel_spec.family)


def validate_counter_set_from_path(experiment_path: str | Path) -> dict[str, object]:
    path = Path(experiment_path).resolve()
    record = validate_counter_set_for_experiment(load_experiment_spec(path), experiment_path=path)
    return record.model_dump(mode="json") if record is not None else {}


def validate_counter_set(counter_set, *, kernel_family: str) -> CounterCompatibilityRecord:
    family_allowed = not counter_set.kernel_family_filters or kernel_family in counter_set.kernel_family_filters
    requested = list(counter_set.counters)
    available: list[str] = []
    missing = list(requested)
    notes = None
    backend = "ncu_query_metrics"
    try:
        completed = subprocess.run(
            ["ncu", "--query-metrics"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        backend = "tool_unavailable"
        notes = "ncu executable not found"
        completed = None

    if completed is not None and completed.returncode == 0:
        metrics_blob = f"{completed.stdout}\n{completed.stderr}"
        discovered = set(re.findall(r"([A-Za-z0-9_.]+)", metrics_blob))
        available = [counter for counter in requested if counter in discovered]
        missing = [counter for counter in requested if counter not in discovered]
    elif completed is not None:
        backend = "ncu_query_failed"
        notes = completed.stderr.strip() or completed.stdout.strip() or "ncu --query-metrics failed"

    availability = (len(available) / len(requested)) if requested else 1.0
    acceptable = family_allowed and availability >= counter_set.minimum_availability
    if counter_set.diagnostic_only:
        acceptable = False
        notes = (notes + "; " if notes else "") + "counter set is diagnostic-only"

    return CounterCompatibilityRecord(
        counter_set_id=counter_set.counter_set_id,
        kernel_family=kernel_family,
        requested_counter_count=len(requested),
        available_counter_count=len(available),
        missing_counters=missing,
        availability_fraction=availability,
        acceptable=acceptable,
        diagnostic_only=counter_set.diagnostic_only,
        kernel_family_allowed=family_allowed,
        validation_backend=backend,
        notes=notes,
    )
