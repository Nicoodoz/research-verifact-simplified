"""Offline integrity and budget audit for 072 artifacts; no API calls."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import run072  # noqa: E402


def main():
    checks = []

    def ck(name, truth):
        checks.append({"name": name, "ok": bool(truth)})

    frozen = run072.check_frozen("pilot")
    blind = run072.lines(OUT / "target_blind.jsonl")
    gt = run072.lines(OUT / "target_gt.jsonl")
    pool = run072.lines(OUT / "example_pool.jsonl")
    ck("target_n", len(blind) == len(gt) == 96 and {x["id"] for x in blind} == {x["id"] for x in gt})
    ck("split_n", len(frozen["pilot_patients"]) == 6 and len(frozen["confirmation_patients"]) == 10 and
       set(frozen["pilot_patients"]).isdisjoint(frozen["confirmation_patients"]))
    ck("teaching_patient_isolation", {x["sid"] for x in pool}.isdisjoint({x["sid"] for x in blind}))
    ck("pool_counts", len(pool) == 12 and Counter(x["physician_label"] for x in pool) ==
       {"Supported": 6, "Not Supported": 3, "Not Addressed": 3})
    ck("all_pool_annotation_unanimous", all(x["annotation"]["initial_agreement"] == "3" and
       all(x["annotation"][f"verdict{i}"] == x["physician_label"] for i in (1, 2, 3)) for x in pool))
    ck("all_pool_ehr_hashes", all(hashlib.sha256(x["reference"].encode()).hexdigest() == x["selected_reference_sha256"] for x in pool))
    old = {(j["id"], j["arm"]): j for j in run072.lines(ROOT / "outputs/071_judge_icl_feasibility/main_jobs.jsonl")}
    attempted, answered = run072.attempt_state()
    ck("task_cap", sum(x["cost_cny"] for x in attempted) <= 30 + 1e-8)
    ck("attempt_ids_unique", len({x["attempt_id"] for x in attempted}) == len(attempted))
    ck("no_answer_resend", all(sum(x["http_status"] == 200 for x in attempted if x["logical_id"] == rid) == 1 for rid in answered))
    ck("attempt_limit", all(n <= 3 for n in Counter(x["logical_id"] for x in attempted).values()))
    for stage in ("pilot", "adaptive", "confirmation"):
        jobpath = OUT / f"{stage}_jobs.jsonl"
        if not jobpath.exists():
            continue
        if stage != "pilot":
            run072.check_frozen(stage)
        jobs = run072.jobs_for(stage)
        ck(stage + "_jobs_unique", len(jobs) == len({j["request_id"] for j in jobs}))
        ck(stage + "_logical_coverage", all(j["request_id"] in answered for j in jobs))
        for job in jobs:
            pid, arm = job["id"], job["arm"]
            ck(stage + "_body_hash:" + job["request_id"], job["body_sha256"] == run072.digest(job["body"]))
            ck(stage + "_target_fixed:" + job["request_id"], job["body"]["messages"][-1]["content"] ==
               old[(pid, "B")]["body"]["messages"][-1]["content"])
            if arm in ("B", "F4"):
                source_arm = "B" if arm == "B" else "E"
                ck(stage + "_exact_071:" + job["request_id"], job["body"] == old[(pid, source_arm)]["body"])
        resultpath = OUT / f"{stage}_analysis.json"
        if resultpath.exists():
            result = run072.read(resultpath)
            predictions = run072.lines(OUT / f"{stage}_predictions.jsonl")
            g = {x["id"]: x["GT"] for x in gt}
            for arm in result["arms"]:
                count = sum(g[x["id"]] == x["PriorG"] for x in predictions if x["arm"] == arm)
                ck(stage + "_correct:" + arm, result["final_metrics"][arm]["correct"] == count)
            ck(stage + "_n", result["n"] == (36 if stage in ("pilot", "adaptive") else 60))
    if (OUT / "confirmation_freeze.json").exists():
        confirmation = run072.read(OUT / "confirmation_freeze.json")
        decision = run072.read(OUT / "pilot_decision.json")
        ck("candidate_selected_before_confirmation", confirmation["selected_arm"] == decision["selected_arm"] and
           confirmation["decision_sha256"] == run072.sha(OUT / decision["decision_file"]))
    result = {"status": "PASS" if all(x["ok"] for x in checks) else "FAIL", "checks": len(checks),
              "failures": [x for x in checks if not x["ok"]],
              "api_attempts": len(attempted), "http200": sum(x["http_status"] == 200 for x in attempted),
              "unknown_attempts": sum(x["http_status"] in (0, None) for x in attempted),
              "task_used_or_reserved_cny": sum(x["cost_cny"] for x in attempted),
              "independent_audit": False}
    (OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("status", "checks", "failures", "api_attempts", "task_used_or_reserved_cny")}, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
