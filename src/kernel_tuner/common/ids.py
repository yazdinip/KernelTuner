"""Deterministic ID helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: dict[str, Any], length: int = 12) -> str:
    digest = hashlib.sha1(_stable_json(payload).encode("utf-8")).hexdigest()
    return digest[:length]


def canonical_shape_id(family: str, shape: dict[str, Any]) -> str:
    if family != "gemm":
        raise ValueError(f"unsupported family for shape ID: {family}")
    layout = re.sub(r"[^a-z0-9]+", "", str(shape["layout"]).lower())
    return (
        f"gemm_m{shape['m']}_n{shape['n']}_k{shape['k']}_"
        f"{shape['dtype']}_{layout}"
    )


def canonical_config_id(config: dict[str, Any]) -> str:
    return f"cfg_{stable_hash(config)}"


def make_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{stable_hash({'timestamp': timestamp}, length=8)}"
