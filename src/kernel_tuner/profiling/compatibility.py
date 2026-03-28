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
from kernel_tuner.common.provenance import resolve_tool_path
from kernel_tuner.common.schema import CounterCompatibilityRecord, ExperimentSpec


def _metric_match(counter: str, discovered: set[str]) -> bool:
    if counter in discovered:
        return True
    parts = counter.split(".")
    while len(parts) > 1:
        parts = parts[:-1]
        if ".".join(parts) in discovered:
            return True
    return False


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
    return validate_counter_set(
        counter_set,
        kernel_family=kernel_spec.family,
        supports_profiling=kernel_spec.supports_profiling,
        require_reportable_constraints=experiment_spec.study_kind == "reportable",
    )


def validate_counter_set_from_path(experiment_path: str | Path) -> dict[str, object]:
    path = Path(experiment_path).resolve()
    record = validate_counter_set_for_experiment(load_experiment_spec(path), experiment_path=path)
    return record.model_dump(mode="json") if record is not None else {}


def validate_counter_set(
    counter_set,
    *,
    kernel_family: str,
    supports_profiling: bool = True,
    require_reportable_constraints: bool = False,
) -> CounterCompatibilityRecord:
    family_allowed = not counter_set.kernel_family_filters or kernel_family in counter_set.kernel_family_filters
    requested = list(counter_set.counters)
    available: list[str] = []
    missing = list(requested)
    notes_parts: list[str] = []
    backend = "ncu_query_metrics"

    if counter_set.tool != "ncu":
        backend = "unsupported_tool"
        notes_parts.append(f"unsupported profiling tool '{counter_set.tool}'")
    if not supports_profiling:
        notes_parts.append("kernel does not advertise profiling support")
    if counter_set.diagnostic_only:
        notes_parts.append("counter set is diagnostic-only")
    if require_reportable_constraints and not counter_set.kernel_name_regex:
        notes_parts.append("reportable counter sets require kernel_name_regex for defensible attribution")
    if counter_set.kernel_name_regex:
        try:
            re.compile(counter_set.kernel_name_regex)
        except re.error as exc:
            notes_parts.append(f"invalid kernel_name_regex: {exc}")

    try:
        completed = None
        if backend == "ncu_query_metrics":
            ncu = resolve_tool_path("ncu")
            completed = subprocess.run(
                [ncu, "--query-metrics"],
                check=False,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError:
        backend = "tool_unavailable"
        notes_parts.append("ncu executable not found")

    if completed is not None and completed.returncode == 0:
        metrics_blob = f"{completed.stdout}\n{completed.stderr}"
        discovered = set(re.findall(r"([A-Za-z0-9_.]+)", metrics_blob))
        available = [counter for counter in requested if _metric_match(counter, discovered)]
        missing = [counter for counter in requested if counter not in available]
        if missing:
            notes_parts.append(
                "missing or unsupported queried metrics: " + ", ".join(sorted(missing))
            )
    elif completed is not None:
        backend = "ncu_query_failed"
        notes_parts.append(completed.stderr.strip() or completed.stdout.strip() or "ncu --query-metrics failed")

    availability = (len(available) / len(requested)) if requested else 1.0
    acceptable = (
        family_allowed
        and supports_profiling
        and counter_set.tool == "ncu"
        and availability >= counter_set.minimum_availability
        and (not counter_set.diagnostic_only)
        and (not require_reportable_constraints or bool(counter_set.kernel_name_regex))
        and not any(part.startswith("invalid kernel_name_regex") for part in notes_parts)
    )
    notes = "; ".join(notes_parts) or None

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
