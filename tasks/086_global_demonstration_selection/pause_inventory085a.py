"""Local-only 085A asset inventory; no AWS, credentials, or endpoint access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/"tasks/085_r1_70b_model_swap"
OUT=ROOT/"outputs/085_r1_70b_model_swap"
CACHE=ROOT/".local_models/085a_r1_tokenizer"
VENV=ROOT/".local_models/085a_tokenizer_venv"
TARGET=ROOT/"outputs/086_global_demonstration_selection/085A_pause_inventory.json"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    task=[p for p in TASK.iterdir() if p.is_file()]
    outputs=[p for p in OUT.iterdir() if p.is_file()]
    cache=[p for p in CACHE.iterdir() if p.is_file()]
    assert any(p.name=="sagemaker_provider.py" for p in task)
    assert any(p.name=="tokenizer_length_audit.json" for p in outputs)
    assert len(cache)==4 and VENV.is_dir()
    result={"status":"PREDEPLOY_READY_PAUSED_BY_USER","aws_calls_this_task":0,
        "shared_code_entry_changed_by_085A":False,"shared_docs_changed_by_085A":[
            "AGENTS.md","README.md","docs/PROJECT_STATUS.md"],
        "task_files":{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(task)},
        "output_files":{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(outputs)},
        "ignored_tokenizer_cache":{p.name:{"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(cache)},
        "ignored_venv_exists":True,"weights_downloaded":False,
        "future_recovery":"separate user authorization; see tasks/085_r1_70b_model_swap/PAUSED_BY_USER.md"}
    with TARGET.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(result,f,ensure_ascii=False,indent=2,sort_keys=True);f.write("\n")
    print(json.dumps({"status":result["status"],"task_files":len(task),
                      "output_files":len(outputs),"tokenizer_cache_files":len(cache)},ensure_ascii=False))


if __name__=="__main__":main()
