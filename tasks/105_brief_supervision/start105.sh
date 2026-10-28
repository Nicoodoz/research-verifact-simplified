#!/usr/bin/env bash
set -euo pipefail
ROOT=/root/autodl-tmp/verifact105
PY=/root/autodl-tmp/verifact103/venv103/bin/python
exec "$PY" "$ROOT/bundle/tasks/105_brief_supervision/start_gpu105.py" --root "$ROOT" "$@"
