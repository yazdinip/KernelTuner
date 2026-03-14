from kernel_tuner.common.ids import canonical_config_id, canonical_shape_id


def test_canonical_shape_id_is_deterministic():
    payload = {"m": 128, "n": 128, "k": 128, "dtype": "fp16", "layout": "row_major"}
    assert canonical_shape_id("gemm", payload) == "gemm_m128_n128_k128_fp16_rowmajor"


def test_canonical_config_id_is_stable():
    config = {"block_m": 128, "block_n": 128, "block_k": 32, "num_stages": 2, "num_warps": 4}
    assert canonical_config_id(config) == canonical_config_id(dict(reversed(list(config.items()))))
