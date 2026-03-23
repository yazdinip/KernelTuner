"""Campaign execution for research rounds."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from kernel_tuner.analysis.comparison import compare_runs_from_path
from kernel_tuner.common.config import (
    campaign_config_path,
    experiment_config_path,
    load_campaign_spec,
    load_experiment_spec,
    load_study_spec,
    resolve_artifact_root,
    study_config_path,
)
from kernel_tuner.common.ids import make_run_id, stable_hash
from kernel_tuner.common.provenance import (
    capture_environment_metadata,
    capture_invocation_metadata,
    capture_slurm_metadata,
)
from kernel_tuner.common.schema import CampaignSpec, Manifest, RunStatus
from kernel_tuner.experiments.orchestrator import run_experiment
from kernel_tuner.storage import RunStore


def materialize_campaign(
    campaign_spec: CampaignSpec,
    *,
    campaign_path: str | Path | None = None,
    campaign_run_id: str | None = None,
) -> dict[str, object]:
    artifact_root = resolve_artifact_root(campaign_spec.artifact_root, campaign_path)
    run_id = campaign_run_id or make_run_id()
    store = RunStore(artifact_root, campaign_spec.campaign_id, run_id)
    environment = capture_environment_metadata(Path.cwd())
    manifest = Manifest(
        experiment_id=campaign_spec.campaign_id,
        run_id=run_id,
        created_at_utc=datetime.now(timezone.utc),
        git_commit=environment.git_commit,
        git_branch=environment.git_branch,
        git_dirty=environment.git_dirty,
        environment=environment,
        invocation=capture_invocation_metadata(
            "ktune materialize-campaign",
            campaign_config_path=str(Path(campaign_path).resolve()) if campaign_path else None,
            campaign_id=campaign_spec.campaign_id,
        ),
        slurm=capture_slurm_metadata(),
        artifact_files=[],
        status=RunStatus.CREATED,
        warnings=[],
    )
    store.initialize_manifest(manifest)
    matrix = _materialize_run_matrix(campaign_spec, campaign_path)
    store.write_yaml_artifact("campaign_spec", campaign_spec.model_dump(mode="json"), filename="campaign_spec.yaml")
    store.write_csv_artifact("campaign_run_matrix", pd.DataFrame(matrix), filename="campaign_run_matrix.csv")
    status_payload = {
        "campaign_id": campaign_spec.campaign_id,
        "campaign_run_id": run_id,
        "round_id": campaign_spec.round_id,
        "job_count": len(matrix),
        "completed_jobs": 0,
        "failed_jobs": 0,
        "study_results": [],
        "jobs": matrix,
        "terminal_status": RunStatus.CREATED,
    }
    store.write_json_artifact("campaign_status", status_payload, filename="campaign_status.json")
    store.write_json_artifact(
        "campaign_manifest",
        {
            "campaign_id": campaign_spec.campaign_id,
            "campaign_run_id": run_id,
            "round_id": campaign_spec.round_id,
            "artifact_root": str(artifact_root),
        },
        filename="campaign_manifest.json",
    )
    return {
        "campaign_id": campaign_spec.campaign_id,
        "campaign_run_id": run_id,
        "run_dir": str(store.run_dir),
        "job_count": len(matrix),
    }


def materialize_campaign_from_path(campaign_path: str | Path) -> dict[str, object]:
    path = Path(campaign_path).resolve()
    return materialize_campaign(load_campaign_spec(path), campaign_path=path)


def run_campaign(
    campaign_spec: CampaignSpec,
    *,
    campaign_path: str | Path | None = None,
    campaign_run_id: str | None = None,
) -> dict[str, object]:
    materialized = materialize_campaign(
        campaign_spec,
        campaign_path=campaign_path,
        campaign_run_id=campaign_run_id,
    )
    return _execute_campaign(Path(materialized["run_dir"]))


def run_campaign_from_path(campaign_path: str | Path) -> dict[str, object]:
    path = Path(campaign_path).resolve()
    return run_campaign(load_campaign_spec(path), campaign_path=path)


def resume_campaign_from_path(campaign_path: str | Path) -> dict[str, object]:
    path = Path(campaign_path).resolve()
    campaign_spec = load_campaign_spec(path)
    artifact_root = resolve_artifact_root(campaign_spec.artifact_root, path)
    campaign_root = artifact_root / campaign_spec.campaign_id
    if not campaign_root.exists():
        raise FileNotFoundError(f"no campaign runs found under '{campaign_root}'")
    candidates = sorted([entry for entry in campaign_root.iterdir() if entry.is_dir()], key=lambda entry: entry.name)
    for run_dir in reversed(candidates):
        status_path = run_dir / "campaign_status.json"
        if not status_path.exists():
            continue
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        if payload.get("terminal_status") not in {RunStatus.SUCCESS.value, RunStatus.FAILED.value}:
            return _execute_campaign(run_dir)
    raise RuntimeError(f"no resumable campaign run found for '{campaign_spec.campaign_id}'")


def _materialize_run_matrix(
    campaign_spec: CampaignSpec,
    campaign_path: str | Path | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for template in campaign_spec.templates:
        for experiment_id in template.experiment_ids:
            experiment_path = experiment_config_path(experiment_id, campaign_path)
            base_spec = load_experiment_spec(experiment_path)
            seeds = template.seeds or [base_spec.seed]
            counter_set_ids = template.counter_set_ids or [base_spec.counter_set_id or ""]
            selector_revision_ids = template.selector_revision_ids or [base_spec.selector_revision_id or ""]
            for seed in seeds:
                for repeat_index in range(template.repeats):
                    for counter_set_id in counter_set_ids:
                        for selector_revision_id in selector_revision_ids:
                            job_id = "job_" + stable_hash(
                                {
                                    "campaign_id": campaign_spec.campaign_id,
                                    "template_id": template.template_id,
                                    "experiment_id": experiment_id,
                                    "seed": seed,
                                    "repeat_index": repeat_index,
                                    "counter_set_id": counter_set_id,
                                    "selector_revision_id": selector_revision_id,
                                },
                                length=10,
                            )
                            rows.append(
                                {
                                    "job_id": job_id,
                                    "template_id": template.template_id,
                                    "experiment_id": experiment_id,
                                    "experiment_path": str(experiment_path),
                                    "seed": seed,
                                    "repeat_index": repeat_index,
                                    "counter_set_id": counter_set_id or None,
                                    "selector_revision_id": selector_revision_id or None,
                                    "execution_mode": (
                                        template.execution_mode.value
                                        if hasattr(template.execution_mode, "value")
                                        else str(template.execution_mode)
                                        if template.execution_mode is not None
                                        else None
                                    ),
                                    "status": "pending",
                                    "run_dir": None,
                                    "error": None,
                                }
                            )
    return rows


def _execute_campaign(run_dir: Path) -> dict[str, object]:
    store = RunStore.from_run_dir(run_dir)
    campaign_spec = load_campaign_spec(run_dir / "campaign_spec.yaml")
    status_path = run_dir / "campaign_status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    jobs = list(status_payload["jobs"])
    study_results: list[dict[str, object]] = list(status_payload.get("study_results", []))

    for job in jobs:
        if job["status"] == "success":
            continue
        try:
            experiment_spec = load_experiment_spec(job["experiment_path"])
            experiment_spec.seed = int(job["seed"])
            if job.get("counter_set_id"):
                experiment_spec.counter_set_id = str(job["counter_set_id"])
                if experiment_spec.profile_policy is not None:
                    experiment_spec.profile_policy.counter_set_id = str(job["counter_set_id"])
            if job.get("selector_revision_id"):
                experiment_spec.selector_revision_id = str(job["selector_revision_id"])
            if job.get("execution_mode"):
                experiment_spec.study_kind = job["execution_mode"]
            result = run_experiment(
                experiment_spec,
                experiment_path=job["experiment_path"],
                repeat_index=int(job["repeat_index"]),
                campaign_id=campaign_spec.campaign_id,
                round_id=campaign_spec.round_id,
            )
            job["status"] = "success"
            job["run_dir"] = result["run_dir"]
            job["error"] = None
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
        status_payload["jobs"] = jobs
        status_payload["completed_jobs"] = sum(1 for item in jobs if item["status"] == "success")
        status_payload["failed_jobs"] = sum(1 for item in jobs if item["status"] == "failed")
        terminal = RunStatus.RUNNING
        if all(item["status"] == "success" for item in jobs):
            terminal = RunStatus.SUCCESS
        elif any(item["status"] == "failed" for item in jobs):
            terminal = RunStatus.PARTIAL_FAILURE
        status_payload["terminal_status"] = terminal.value
        store.write_json_artifact("campaign_status", status_payload, filename="campaign_status.json")

    if all(job["status"] == "success" for job in jobs):
        study_results = []
        available_templates = {str(job["template_id"]) for job in jobs if job.get("template_id")}
        for study_binding in campaign_spec.studies:
            required_templates = set(study_binding.requires_templates)
            missing_templates = sorted(required_templates - available_templates)
            if missing_templates:
                study_results.append(
                    {
                        "study_id": study_binding.study_id,
                        "status": "skipped_requires_templates",
                        "missing_templates": missing_templates,
                    }
                )
                continue
            study_path = (
                Path(study_binding.study_path).resolve()
                if study_binding.study_path
                else study_config_path(study_binding.study_id, run_dir)
            )
            result = compare_runs_from_path(study_path)
            study_results.append({"study_id": study_binding.study_id, **result})
        status_payload["study_results"] = study_results
        status_payload["terminal_status"] = RunStatus.SUCCESS.value
    else:
        status_payload["study_results"] = study_results
    summary = {
        "campaign_id": campaign_spec.campaign_id,
        "campaign_run_id": run_dir.name,
        "round_id": campaign_spec.round_id,
        "job_count": len(jobs),
        "completed_jobs": sum(1 for item in jobs if item["status"] == "success"),
        "failed_jobs": sum(1 for item in jobs if item["status"] == "failed"),
        "study_results": study_results,
        "run_dirs": [job["run_dir"] for job in jobs if job.get("run_dir")],
    }
    store.write_json_artifact("campaign_summary", summary, filename="campaign_summary.json")
    store.write_json_artifact("campaign_status", status_payload, filename="campaign_status.json")
    final_status = RunStatus.SUCCESS if status_payload["terminal_status"] == RunStatus.SUCCESS.value else RunStatus.PARTIAL_FAILURE
    store.finalize(final_status, warnings=[job["error"] for job in jobs if job.get("error")])
    return {
        "campaign_id": campaign_spec.campaign_id,
        "campaign_run_id": run_dir.name,
        "run_dir": str(run_dir),
        "terminal_status": status_payload["terminal_status"],
        "summary_path": str(run_dir / "campaign_summary.json"),
    }
