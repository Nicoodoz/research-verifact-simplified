#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
WORK_ROOT="${1:?workspace}"
STAGE="${2:?probe or train_eval}"
PY="$WORK_ROOT/venv103/bin/python"
BUNDLE="$WORK_ROOT/bundle"
OUT="$WORK_ROOT/results"
MODELS="$WORK_ROOT/models"
mkdir -p "$OUT"
run_worker() {
  "$PY" "$TASK_DIR/gpu_worker103.py" --bundle "$BUNDLE" --out "$OUT" --model-root "$MODELS" "$@" &
  WORKER_PID=$!
  printf '%s\n' "$WORKER_PID" > "$OUT/active_worker.pid"
  wait "$WORKER_PID"
}
mapfile -t CANDIDATES < <("$PY" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["candidates"]))' "$BUNDLE/gpu_plan.json")
if [[ "$STAGE" == "probe" ]]; then
  "$PY" "$TASK_DIR/gpu_download103.py" --bundle "$BUNDLE" --model-root "$MODELS"
  for MODEL in "${CANDIDATES[@]}"; do
    run_worker --model "$MODEL" --phase probe
    run_worker --model "$MODEL" --phase eval --arm native_base --speed
    run_worker --model "$MODEL" --phase eval --arm label_base --speed
  done
  "$PY" "$TASK_DIR/gpu_bridge_check103.py" --out "$OUT" --bundle "$BUNDLE"
  "$PY" "$TASK_DIR/gpu_plan_after_probe103.py" --out "$OUT" --bundle "$BUNDLE"
elif [[ "$STAGE" == "train_eval" ]]; then
  LIMIT=$("$PY" -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="GO"; print(r["samples_each"])' "$OUT/scale_decision.json")
  for MODEL in "${CANDIDATES[@]}"; do
    # Bridge results are inspected before this stage; successful full results skip on resume.
    run_worker --model "$MODEL" --phase eval --arm native_base
    run_worker --model "$MODEL" --phase eval --arm label_base
    EXTRA=()
    if [[ -f "$OUT/$MODEL/train/resume.json" ]]; then EXTRA+=(--resume); fi
    run_worker --model "$MODEL" --phase train --limit "$LIMIT" "${EXTRA[@]}"
    run_worker --model "$MODEL" --phase eval --arm lora_label
  done
else
  printf 'Unknown stage\n' >&2
  exit 2
fi
