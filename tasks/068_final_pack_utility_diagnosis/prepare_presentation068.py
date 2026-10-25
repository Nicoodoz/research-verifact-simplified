"""Freeze a pure line-break presentation perturbation before 068 answer analysis."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def main():
    if (OUT / "presentation_freeze.json").exists():
        raise RuntimeError("presentation already frozen")
    repeat = jsonl(OUT / "jobs_002.jsonl")
    selected = {x["id"]: x["group"] for x in repeat if x["condition"] == "added_repeat"}
    assert len(selected) == 39
    formal = {x["id"]: x for x in jsonl(ROOT / "outputs/067_conservative_evidence_packing/stage2_jobs.jsonl")}
    assert all(pid in formal for pid in selected)
    jobs = []
    identical = []
    for pid in sorted(selected, key=lambda x: hashlib.sha256(x.encode()).hexdigest()):
        original = formal[pid]["body"]
        body = json.loads(json.dumps(original))
        content = json.loads(body["messages"][1]["content"])
        ref = content["reference"]
        corrected = ref.replace("\\n", "\n")
        if corrected == ref:
            identical.append(pid)
            continue
        content["reference"] = corrected
        body["messages"][1]["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        assert content["proposition"] == json.loads(original["messages"][1]["content"])["proposition"]
        assert corrected.replace("\n", " ").replace("\\n", " ") == ref.replace("\n", " ").replace("\\n", " ")
        assert body["model"] == c.MODELS["deepseek"] and body["reasoning_effort"] == "high"
        job = {
            "request_id": "068_linebreak_" + hashlib.sha256(pid.encode()).hexdigest()[:24],
            "id": pid,
            "condition": "linebreak_presentation",
            "group": selected[pid],
            "model_key": "deepseek",
            "body": body,
            "body_sha256": c.digest(body),
            "conservative_reservation_cny": c.bound({"model_key": "deepseek", "body": body}),
        }
        jobs.append(job)
    with (OUT / "presentation_jobs.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(json.dumps(job, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    freeze = {
        "condition": "literal-backslash-n to true LF in 067 short pack only",
        "selected_cases": len(selected),
        "identical_input_ids": identical,
        "planned_jobs": len(jobs),
        "conservative_bound_cny": sum(c.bound(job) for job in jobs),
        "hard_cap_shared_with_repeats_cny": 10.0,
        "dispatch_rule": "SHA256(ID) prefix while actual used/unknown reserve + each conservative reservation <=10",
        "jobs_sha256": hashlib.sha256((OUT / "presentation_jobs.jsonl").read_bytes()).hexdigest(),
        "formal_stage2_sha256": c.sha(ROOT / "outputs/067_conservative_evidence_packing/stage2_jobs.jsonl"),
        "amendment_sha256": c.sha(ROOT / "tasks/068_final_pack_utility_diagnosis/protocol_amendment_003.md"),
        "GT_in_API": False,
        "selection_after_new_answers": False,
    }
    (OUT / "presentation_freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: freeze[k] for k in ("selected_cases", "planned_jobs", "conservative_bound_cny", "hard_cap_shared_with_repeats_cny")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
