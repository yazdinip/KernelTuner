from pathlib import Path

from kernel_tuner.common.config import load_experiment_spec
from kernel_tuner.config_space import generate_candidate_configs


def test_generate_candidate_configs_example():
    spec = load_experiment_spec(Path("configs/experiments/gemm_smoke.example.yaml"))
    result = generate_candidate_configs(spec, experiment_path=Path("configs/experiments/gemm_smoke.example.yaml"))
    assert result["candidate_count"] == 16
    config_ids = [record["config_id"] for record in result["records"]]
    assert len(config_ids) == len(set(config_ids))
