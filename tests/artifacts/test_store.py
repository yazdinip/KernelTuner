from datetime import datetime, timezone

from kernel_tuner.common.provenance import capture_environment_metadata, capture_invocation_metadata
from kernel_tuner.common.schema import (
    ArtifactFile,
    CandidateConfig,
    EnvironmentMetadata,
    ExperimentResult,
    Manifest,
    RunStatus,
)
from kernel_tuner.storage import RunStore


def _dummy_environment() -> EnvironmentMetadata:
    return capture_environment_metadata(".")


def test_run_store_writes_manifest_and_table(tmp_path):
    store = RunStore(tmp_path, "exp", "run_001")
    manifest = Manifest(
        experiment_id="exp",
        run_id="run_001",
        created_at_utc=datetime.now(timezone.utc),
        environment=_dummy_environment(),
        invocation=capture_invocation_metadata("pytest"),
        artifact_files=[],
    )
    store.initialize_manifest(manifest)
    record = CandidateConfig(
        experiment_id="exp",
        kernel_id="gemm",
        shape_id="gemm_m128_n128_k128_fp16_row_major",
        config_id="cfg_123",
        block_m=128,
        block_n=128,
        block_k=32,
        num_warps=4,
        num_stages=2,
        is_valid=True,
    )
    path = store.write_table("candidates", [record])
    assert path.exists()
    frame = store.load_table("candidates")
    assert len(frame) == 1
    assert frame.iloc[0]["config_id"] == "cfg_123"


def test_run_store_writes_summary(tmp_path):
    store = RunStore(tmp_path, "exp", "run_002")
    manifest = Manifest(
        experiment_id="exp",
        run_id="run_002",
        created_at_utc=datetime.now(timezone.utc),
        environment=_dummy_environment(),
        invocation=capture_invocation_metadata("pytest"),
        artifact_files=[
            ArtifactFile(logical_name="manifest", relative_path="manifest.json", schema_version=1)
        ],
    )
    store.initialize_manifest(manifest)
    summary = ExperimentResult(
        experiment_id="exp",
        run_id="run_002",
        terminal_status="success",
        strategies=["default_config"],
        best_configs={"default_config": "cfg_123"},
    )
    path = store.write_summary(summary)
    assert path.exists()
    assert store.load_summary()["best_configs"]["default_config"] == "cfg_123"
    store.finalize(RunStatus.SUCCESS)
