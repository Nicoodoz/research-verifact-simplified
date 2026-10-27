#!/usr/bin/env bash
set -euo pipefail
# Run only after gpu_lifecycle103 init/watch on the user-provided instance.
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
WORK_ROOT="${1:?task workspace path required}"
python3.12 -m venv "$WORK_ROOT/venv103"
PY="$WORK_ROOT/venv103/bin/python"
"$PY" -m pip install --require-hashes -r "$TASK_DIR/requirements_gpu.lock"
"$PY" -m pip check
"$PY" -m pip freeze --all > "$WORK_ROOT/installed_gpu.lock"
"$PY" -c 'import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); print(torch.__version__,torch.version.cuda,torch.cuda.get_device_name(),torch.cuda.get_arch_list()); assert torch.cuda.get_device_capability()[0] >= 8'
