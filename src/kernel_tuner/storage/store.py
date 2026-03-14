"""Artifact storage for KernelTuner runs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence, TypeVar

import pandas as pd

from kernel_tuner.common.config import dump_yaml
from kernel_tuner.common.schema import (
    ArtifactFile,
    ExperimentResult,
    ExperimentSpec,
    KTModel,
    Manifest,
    RunStatus,
    SCHEMA_VERSION,
)

T = TypeVar("T", bound=KTModel)


class RunStore:
    """Write and read run artifacts with manifest bookkeeping."""

    def __init__(self, artifact_root: str | Path, experiment_id: str, run_id: str) -> None:
        self.run_dir = Path(artifact_root) / experiment_id / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = self.run_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.run_dir / "manifest.json"
        self._manifest: Manifest | None = None

    @property
    def manifest(self) -> Manifest:
        if self._manifest is None:
            raise RuntimeError("manifest has not been initialized")
        return self._manifest

    def initialize_manifest(self, manifest: Manifest) -> None:
        self._manifest = manifest
        self._write_json_atomic(self.manifest_path, manifest.model_dump(mode="json"))

    def write_experiment_spec(self, spec: ExperimentSpec) -> None:
        payload = spec.model_dump(mode="json")
        path = self.run_dir / "experiment_spec.yaml"
        self._write_yaml_atomic(path, payload)
        self._register_artifact(
            ArtifactFile(
                logical_name="experiment_spec",
                relative_path=path.relative_to(self.run_dir).as_posix(),
                schema_version=SCHEMA_VERSION,
                row_count=None,
                content_hash=self._hash_file(path),
            )
        )

    def write_table(self, logical_name: str, records: Sequence[KTModel]) -> Path:
        path = self.run_dir / f"{logical_name}.parquet"
        frame = pd.DataFrame([self._serialize_model(record) for record in records])
        self._write_parquet_atomic(path, frame)
        self._register_artifact(
            ArtifactFile(
                logical_name=logical_name,
                relative_path=path.relative_to(self.run_dir).as_posix(),
                schema_version=SCHEMA_VERSION,
                row_count=len(frame),
                content_hash=self._hash_file(path),
            )
        )
        return path

    def write_summary(self, result: ExperimentResult) -> Path:
        path = self.run_dir / "summary.json"
        self._write_json_atomic(path, result.model_dump(mode="json"))
        self._register_artifact(
            ArtifactFile(
                logical_name="summary",
                relative_path=path.relative_to(self.run_dir).as_posix(),
                schema_version=SCHEMA_VERSION,
                row_count=None,
                content_hash=self._hash_file(path),
            )
        )
        return path

    def register_log_file(self, relative_name: str, content: str) -> Path:
        path = self.logs_dir / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def finalize(self, status: RunStatus, warnings: Iterable[str] | None = None) -> None:
        manifest = self.manifest.model_copy(deep=True)
        manifest.status = status
        manifest.warnings = list(warnings or manifest.warnings)
        self._manifest = manifest
        self._write_json_atomic(self.manifest_path, manifest.model_dump(mode="json"))

    def load_table(self, logical_name: str) -> pd.DataFrame:
        return pd.read_parquet(self.run_dir / f"{logical_name}.parquet")

    def load_summary(self) -> dict[str, Any]:
        with (self.run_dir / "summary.json").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _register_artifact(self, artifact: ArtifactFile) -> None:
        manifest = self.manifest.model_copy(deep=True)
        manifest.artifact_files = [
            existing
            for existing in manifest.artifact_files
            if existing.logical_name != artifact.logical_name
        ]
        manifest.artifact_files.append(artifact)
        self._manifest = manifest
        self._write_json_atomic(self.manifest_path, manifest.model_dump(mode="json"))

    def _serialize_model(self, record: KTModel) -> dict[str, Any]:
        payload = record.model_dump(mode="json")
        for key, value in list(payload.items()):
            if isinstance(value, (dict, list)):
                payload[key] = json.dumps(value, sort_keys=True)
        return payload

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, indent=2, sort_keys=False)
        self._write_text_atomic(path, data)

    def _write_yaml_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            dump_yaml(tmp_path, payload)
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _write_parquet_atomic(self, path: Path, frame: pd.DataFrame) -> None:
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            frame.to_parquet(tmp_path, index=False)
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _write_text_atomic(self, path: Path, content: str) -> None:
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(8192):
                digest.update(chunk)
        return digest.hexdigest()
