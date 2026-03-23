"""Profiling adapter."""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from kernel_tuner.common.config import (
    counter_set_path,
    kernel_config_path,
    load_counter_set,
    load_experiment_spec,
    load_kernel_spec,
)
from kernel_tuner.common.provenance import python_command
from kernel_tuner.common.schema import (
    CandidateConfig,
    CounterSetSpec,
    ExperimentSpec,
    MeasurementPhase,
    ProfileMeasurement,
    ProfileStatus,
    ProblemShape,
)
from kernel_tuner.config_space.generator import config_dict_from_record, generate_candidate_records
from kernel_tuner.kernels.registry import resolve_kernel


@dataclass
class ProfileOutcome:
    measurement: ProfileMeasurement
    stdout: str = ""
    stderr: str = ""


def _maybe_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().strip('"')
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _extract_csv_rows(stdout: str) -> list[dict[str, str]]:
    lines = stdout.splitlines()
    header_index = next((index for index, line in enumerate(lines) if '"Kernel Name"' in line), None)
    if header_index is None:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    return [dict(row) for row in reader]


def _choose_kernel_row(
    rows: list[dict[str, str]],
    *,
    kernel_name_regex: str | None,
) -> tuple[dict[str, str] | None, dict[str, Any]]:
    if not rows:
        return None, {"kernel_attribution_status": "no_rows", "kernel_name_candidates": [], "matched_row_count": 0}

    kernel_names = sorted({row.get("Kernel Name", "") for row in rows if row.get("Kernel Name")})
    filtered: list[dict[str, str]] = rows
    if kernel_name_regex:
        pattern = re.compile(kernel_name_regex)
        matched = [row for row in rows if pattern.search(row.get("Kernel Name", ""))]
        if not matched:
            return None, {
                "kernel_attribution_status": "regex_no_match",
                "kernel_name_candidates": kernel_names,
                "matched_row_count": 0,
            }
        matched_names = sorted({row.get("Kernel Name", "") for row in matched if row.get("Kernel Name")})
        if len(matched_names) > 1:
            return None, {
                "kernel_attribution_status": "regex_ambiguous",
                "kernel_name_candidates": matched_names,
                "matched_row_count": len(matched),
            }
        filtered = matched
    elif len(kernel_names) > 1:
        return None, {
            "kernel_attribution_status": "ambiguous_without_regex",
            "kernel_name_candidates": kernel_names,
            "matched_row_count": len(rows),
        }

    duration_key = "gpu__time_duration.sum"
    filtered = sorted(
        filtered,
        key=lambda row: (
            _maybe_float(row.get(duration_key)) or -1.0,
            row.get("Kernel Name", ""),
        ),
    )
    return (
        filtered[-1] if filtered else None,
        {
            "kernel_attribution_status": "matched",
            "kernel_name_candidates": kernel_names,
            "matched_row_count": len(filtered),
        },
    )


def _parse_counter_map(
    stdout: str,
    counters: list[str],
    *,
    kernel_name_regex: str | None,
) -> tuple[dict[str, float | None], list[str], str | None, dict[str, Any]]:
    rows = _extract_csv_rows(stdout)
    row, diagnostics = _choose_kernel_row(rows, kernel_name_regex=kernel_name_regex)
    if row is None:
        return (
            {counter: None for counter in counters},
            counters,
            None,
            {
                "row_count": len(rows),
                **diagnostics,
            },
        )
    counter_map = {counter: _maybe_float(row.get(counter)) for counter in counters}
    missing = [counter for counter, value in counter_map.items() if value is None]
    return (
        counter_map,
        missing,
        row.get("Kernel Name"),
        {
            "row_count": len(rows),
            **diagnostics,
        },
    )


@lru_cache(maxsize=1)
def _ncu_version() -> str | None:
    try:
        completed = subprocess.run(
            ["ncu", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else None


def _base_profiler_metadata(
    *,
    command: list[str],
    counter_set: CounterSetSpec,
    kernel_name_regex: str | None,
    experiment_spec: ExperimentSpec,
) -> dict[str, Any]:
    return {
        "command": command,
        "requested_counters": list(counter_set.counters),
        "target_processes": counter_set.target_processes or "all",
        "replay_mode": counter_set.replay_mode or experiment_spec.profiling_settings.replay_mode,
        "kernel_name_regex": kernel_name_regex,
        "ncu_args": list(counter_set.ncu_args),
        "minimum_availability": counter_set.minimum_availability,
        "diagnostic_only": counter_set.diagnostic_only,
        "timeout_s": experiment_spec.profiling_settings.timeout_s,
        "cooldown_s": experiment_spec.profiling_settings.cooldown_s,
        "ncu_version": _ncu_version(),
    }


def _build_profile_command(
    counter_set: CounterSetSpec,
    profiling_settings,
    payload: str,
) -> list[str]:
    command = [
        "ncu",
        "--csv",
        "--page",
        "raw",
        "--target-processes",
        counter_set.target_processes or "all",
        "--metrics",
        ",".join(counter_set.counters),
    ]
    replay_mode = counter_set.replay_mode or profiling_settings.replay_mode
    if replay_mode:
        command.extend(["--replay-mode", replay_mode])
    kernel_name_regex = counter_set.kernel_name_regex or profiling_settings.kernel_name_regex
    if kernel_name_regex:
        command.extend(["--kernel-name-base", "demangled", "--kernel-name", f"regex:{kernel_name_regex}"])
    if counter_set.ncu_args:
        command.extend(counter_set.ncu_args)
    command.extend([python_command(), "-m", "kernel_tuner.cli.app", "_profile-once", payload])
    return command


def profile_candidate(
    *,
    run_id: str,
    strategy_id: str,
    kernel_id: str,
    shape: ProblemShape,
    candidate: CandidateConfig,
    counter_set: CounterSetSpec,
    experiment_spec: ExperimentSpec,
    experiment_path: str | Path | None = None,
) -> ProfileOutcome:
    payload = json.dumps(
        {
            "kernel_path": str(kernel_config_path(kernel_id, experiment_path)),
            "shape": shape.model_dump(mode="json"),
            "config": config_dict_from_record(candidate),
            "seed": experiment_spec.seed,
        },
        sort_keys=True,
    )
    command = _build_profile_command(counter_set, experiment_spec.profiling_settings, payload)
    command_started = time.perf_counter()
    kernel_name_regex = counter_set.kernel_name_regex or experiment_spec.profiling_settings.kernel_name_regex
    base_metadata = _base_profiler_metadata(
        command=command,
        counter_set=counter_set,
        kernel_name_regex=kernel_name_regex,
        experiment_spec=experiment_spec,
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=experiment_spec.profiling_settings.timeout_s,
        )
    except FileNotFoundError:
        measurement = ProfileMeasurement(
            run_id=run_id,
            strategy_id=strategy_id,
            kernel_id=kernel_id,
            shape_id=shape.shape_id,
            config_id=candidate.config_id,
            counter_set_id=counter_set.counter_set_id,
            profile_status=ProfileStatus.TOOL_UNAVAILABLE,
            profiler_metadata={
                **base_metadata,
                "returncode": None,
                "duration_s": time.perf_counter() - command_started,
            },
            notes="ncu executable not found",
        )
        if experiment_spec.profiling_settings.cooldown_s > 0.0:
            time.sleep(experiment_spec.profiling_settings.cooldown_s)
        return ProfileOutcome(measurement=measurement)
    except subprocess.TimeoutExpired as exc:
        measurement = ProfileMeasurement(
            run_id=run_id,
            strategy_id=strategy_id,
            kernel_id=kernel_id,
            shape_id=shape.shape_id,
            config_id=candidate.config_id,
            counter_set_id=counter_set.counter_set_id,
            profile_status=ProfileStatus.TIMEOUT,
            profiler_metadata={
                **base_metadata,
                "returncode": None,
                "duration_s": time.perf_counter() - command_started,
            },
            notes=f"ncu timed out: {exc}",
        )
        if experiment_spec.profiling_settings.cooldown_s > 0.0:
            time.sleep(experiment_spec.profiling_settings.cooldown_s)
        return ProfileOutcome(measurement=measurement, stdout=exc.stdout or "", stderr=exc.stderr or "")

    counter_map, missing_counters, matched_kernel_name, diagnostics = _parse_counter_map(
        completed.stdout,
        counter_set.counters,
        kernel_name_regex=kernel_name_regex,
    )
    unsupported_metric = bool(
        re.search(r"(unknown metric|unsupported metric|not supported)", completed.stderr, re.IGNORECASE)
    )
    status = ProfileStatus.SUCCESS
    notes = None
    attribution_failed = matched_kernel_name is None or diagnostics.get("kernel_attribution_status") != "matched"
    if completed.returncode != 0 and unsupported_metric:
        status = ProfileStatus.UNSUPPORTED_COUNTER
        notes = completed.stderr.strip() or completed.stdout.strip() or "unsupported counter"
    elif completed.returncode != 0:
        status = ProfileStatus.INVOCATION_FAILED
        notes = completed.stderr.strip() or completed.stdout.strip() or "ncu invocation failed"
    elif attribution_failed:
        status = ProfileStatus.NO_PROFILE_DATA
        notes = f"no attributable profiler row: {diagnostics.get('kernel_attribution_status')}"
    elif missing_counters:
        status = ProfileStatus.UNSUPPORTED_COUNTER
        notes = "missing or unsupported counters: " + ", ".join(sorted(missing_counters))

    measurement = ProfileMeasurement(
        run_id=run_id,
        strategy_id=strategy_id,
        kernel_id=kernel_id,
        shape_id=shape.shape_id,
        config_id=candidate.config_id,
        counter_set_id=counter_set.counter_set_id,
        profile_status=status,
        counter_map=counter_map,
        profiler_metadata={
            **base_metadata,
            "returncode": completed.returncode,
            "duration_s": time.perf_counter() - command_started,
            "matched_kernel_name": matched_kernel_name,
            "missing_counters": missing_counters,
            **diagnostics,
        },
        notes=notes,
    )
    if experiment_spec.profiling_settings.cooldown_s > 0.0:
        time.sleep(experiment_spec.profiling_settings.cooldown_s)
    return ProfileOutcome(measurement=measurement, stdout=completed.stdout, stderr=completed.stderr)


def profile_experiment(
    experiment_spec: ExperimentSpec,
    *,
    experiment_path: str | Path | None = None,
) -> dict[str, object]:
    if not experiment_spec.counter_set_id:
        raise ValueError("profile command requires experiment_spec.counter_set_id")
    counter_set = load_counter_set(counter_set_path(experiment_spec.counter_set_id, experiment_path))
    candidates = generate_candidate_records(experiment_spec, experiment_path=experiment_path)
    from kernel_tuner.experiments.orchestrator import _profile_shapes, _shape_split

    calibration_shapes, _ = _shape_split(experiment_spec)
    selected_shapes = _profile_shapes(experiment_spec, calibration_shapes)
    measurements = []
    for index, shape in enumerate(selected_shapes):
        shape_candidates = [candidate for candidate in candidates if candidate.shape_id == shape.shape_id]
        candidate = next((item for item in shape_candidates if item.is_valid), None)
        if candidate is None:
            candidate = shape_candidates[0]
        outcome = profile_candidate(
            run_id="standalone",
            strategy_id="profile_cli",
            kernel_id=experiment_spec.kernels[0],
            shape=shape,
            candidate=candidate,
            counter_set=counter_set,
            experiment_spec=experiment_spec,
            experiment_path=experiment_path,
        )
        measurements.append(outcome.measurement.model_dump(mode="json"))
    return {
        "experiment_id": experiment_spec.experiment_id,
        "profile_shape_count": len(measurements),
        "measurements": measurements,
    }


def profile_once_entrypoint(payload: str) -> None:
    import torch

    request = json.loads(payload)
    spec = load_kernel_spec(Path(request["kernel_path"]))
    kernel = resolve_kernel(spec)
    shape = ProblemShape.model_validate(request["shape"])
    config = request["config"]
    inputs = kernel.make_inputs(shape, seed=int(request.get("seed", 0)))
    kernel.run_kernel(inputs, shape, config)
    torch.cuda.synchronize()
