"""Deterministic ID helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def stable_hash(payload: dict[str, Any], length: int = 12) -> str:
    digest = hashlib.sha1(_stable_json(payload).encode("utf-8")).hexdigest()
    return digest[:length]


def canonical_shape_id(family: str, shape: dict[str, Any]) -> str:
    family_token = _normalize_token(family)
    dtype = _normalize_token(shape.get("dtype", "unknown"))
    layout = _normalize_token(shape.get("layout", "default"))
    dimensions = dict(shape.get("dimensions") or {})
    if not dimensions:
        for key in ("m", "n", "k", "rows", "hidden"):
            if key in shape:
                dimensions[key] = shape[key]

    if family_token == "gemm":
        if not {"m", "n", "k"} <= set(dimensions):
            raise ValueError("gemm shape IDs require dimensions m, n, and k")
        return (
            f"gemm_m{dimensions['m']}_n{dimensions['n']}_k{dimensions['k']}_"
            f"{dtype}_{layout}"
        )

    if family_token == "layernorm":
        if not {"rows", "hidden"} <= set(dimensions):
            raise ValueError("layernorm shape IDs require dimensions rows and hidden")
        return f"layernorm_rows{dimensions['rows']}_hidden{dimensions['hidden']}_{dtype}_{layout}"

    dim_suffix = "_".join(
        f"{_normalize_token(name)}{dimensions[name]}"
        for name in sorted(dimensions)
    )
    return f"{family_token}_{dim_suffix}_{dtype}_{layout}"


def canonical_config_id(config: dict[str, Any]) -> str:
    return f"cfg_{stable_hash(config)}"


def make_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{stable_hash({'timestamp': timestamp}, length=8)}"
