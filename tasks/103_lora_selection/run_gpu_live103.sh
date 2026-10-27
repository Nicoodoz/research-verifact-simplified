#!/usr/bin/env bash
set -euo pipefail
ROOT=/root/autodl-tmp/verifact103
cd "$ROOT"
export OMP_NUM_THREADS=8 MAX_JOBS=8 TORCHINDUCTOR_COMPILE_THREADS=8
export TORCH_DISABLE_ADDR2LINE=1 HF_HUB_OFFLINE=1
export HF_HOME="$ROOT/cache" TMPDIR="$ROOT/tmp"
echo $$ > "$ROOT/results/active_worker.pid"
exec "$ROOT/venv103/bin/python" -u "$ROOT/task/gpu_batch103.py" --bundle "$ROOT/bundle" --out "$ROOT/results" --model-root "$ROOT/models" "$@"
