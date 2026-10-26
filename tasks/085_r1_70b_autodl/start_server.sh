#!/usr/bin/env bash
set -euo pipefail
export HF_HOME="${HF_HOME:-/root/autodl-tmp/huggingface}"
export VLLM_USE_V1=1
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python "$SCRIPT_DIR/remote_server.py" launch "$@"
