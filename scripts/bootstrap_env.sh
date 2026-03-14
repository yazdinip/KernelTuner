#!/usr/bin/env bash
set -euo pipefail

CUDA_HOME_DEFAULT="/usr/local/cuda-12.9"
CUDA_HOME="${CUDA_HOME:-$CUDA_HOME_DEFAULT}"
PATH="$CUDA_HOME/bin:$PATH"
export CUDA_HOME PATH
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"

SCRATCH_BASE="$(ls -d /scratch/scratch-space/expires-* 2>/dev/null | sort | tail -n 1 || true)"
if [[ -n "$SCRATCH_BASE" ]]; then
  KTUNE_SCRATCH="${KTUNE_SCRATCH:-$SCRATCH_BASE/$USER/kerneltuner}"
else
  KTUNE_SCRATCH="${KTUNE_SCRATCH:-/tmp/$USER/kerneltuner}"
fi
export KTUNE_SCRATCH
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$KTUNE_SCRATCH/pip-cache}"

mkdir -p "$KTUNE_SCRATCH"

VENV_PATH="${1:-$KTUNE_SCRATCH/venv-py312}"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[gpu,dev]'

python - <<'PY'
import platform
import pandas
import pyarrow
import pydantic
import typer
print("python", platform.python_version())
print("pandas", pandas.__version__)
print("pyarrow", pyarrow.__version__)
print("pydantic", pydantic.__version__)
print("typer", typer.__version__)
try:
    import torch
    print("torch", torch.__version__)
except Exception as exc:
    print("torch", f"import failed: {exc}")
try:
    import triton
    print("triton", triton.__version__)
except Exception as exc:
    print("triton", f"import failed: {exc}")
PY
