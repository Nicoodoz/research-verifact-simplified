"""Offline executor integrity audit for frozen 071; never sends API calls."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(ROOT / "tasks/071_judge_icl_feasibility"))
import run071  # noqa: E402


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


checks = []


def ck(name, value):
    checks.append({"name": name, "ok": bool(value)})


freeze = read(OUT / "freeze.json")
for relative, sha in freeze["source_sha256"].items():
    ck("frozen_source:" + relative, run071.sha(ROOT / relative) == sha)
examples = lines(OUT / "examples.jsonl")
ev = lines(OUT / "evaluation_blind.jsonl")
gt = lines(OUT / "evaluation_gt.jsonl")
jobs = lines(OUT / "main_jobs.jsonl")
ck("four_examples", len(examples) == 4 and Counter(x["physician_label"] for x in examples) == {"Supported": 2, "Not Supported": 1, "Not Addressed": 1})
ck("patient_isolation", set(x["sid"] for x in examples).isdisjoint({x["sid"] for x in ev}))
ck("evaluation_complete", len(ev) == len(gt) == 96 and {x["id"] for x in ev} == {x["id"] for x in gt})
ck("evaluation_class_counts", Counter(x["GT"] for x in gt) == {"Supported": 78, "Not Supported": 5, "Not Addressed": 13})
ck("three_exact_arms", len(jobs) == 288 and Counter(x["arm"] for x in jobs) == {"B": 96, "E": 96, "C": 96})
ck("job_ids_unique", len({x["request_id"] for x in jobs}) == len(jobs))
by = {(x["id"], x["arm"]): x for x in jobs}
old = {(x["id"], x["condition"]): x for x in lines(ROOT / "outputs/053_thinking_prior_validation/main_jobs.jsonl")}
for item in ev:
    pid = item["id"]
    b, e, c = (by[(pid, a)] for a in ("B", "E", "C"))
    ck("baseline_exact:" + pid, b["body"] == old[(pid, "T-S")]["body"])
    ck("target_payload_fixed:" + pid, all(x["body"]["messages"][-1]["content"] == b["body"]["messages"][-1]["content"] for x in (e, c)))
    ck("system_only_change:" + pid, all({k: v for k, v in x["body"].items() if k != "messages"} ==
        {k: v for k, v in b["body"].items() if k != "messages"} for x in (e, c)))
    ck("label_histogram_length:" + pid, len(e["body"]["messages"][0]["content"]) == len(c["body"]["messages"][0]["content"]))
    ck("body_hash:" + pid, all(x["body_sha256"] == run071.digest(x["body"]) for x in (b, e, c)))
attempts, terminal = run071.resolved_state()
ck("no_duplicate_attempt", len(attempts) == len({x["id"] for x in attempts}))
ck("preflight_valid", "071_preflight_001" in terminal and terminal["071_preflight_001"]["parsed"]["status"] in ("valid", "valid_with_format_anomaly"))
main = [x for x in attempts if x["stage"] == "main"]
complete = len(main) == 288 and all(x["http_status"] == 200 for x in main)
stopped = (OUT / "execution_diagnosis.json").exists()
continued = (OUT / "continuation_001_freeze.json").exists()
if continued:
    recovery = [x for x in attempts if x["stage"] == "recovery"]
    recovery_jobs = lines(OUT / "recovery_jobs.jsonl")
    original_jobs = {j["request_id"]: j for j in jobs}
    ck("six_exact_recovery_jobs", len(recovery_jobs) == 6 and all(j["body"] == original_jobs[j["source_request_id"]]["body"] for j in recovery_jobs))
    ck("recovery_complete", len(recovery) == 6 and all(x["http_status"] == 200 for x in recovery))
    ck("original_unknown_preserved", sum(x["http_status"] == 0 for x in main) == 6)
    ck("all_main_resolved", len(main) == 288 and all(j["request_id"] in terminal for j in jobs))
elif stopped:
    diagnosis = read(OUT / "execution_diagnosis.json")
    ck("frozen_transport_stop", diagnosis["task_status"] == "STOPPED_AFTER_TRANSPORT_UNKNOWN"
       and diagnosis["main_http200"] == 108 and diagnosis["main_unknown"] == 6
       and diagnosis["main_unsent"] == 174 and len(main) == 114)
    ck("no_partial_method_gate", not (OUT / "stage1_gate.json").exists()
       and not (OUT / "repeat_jobs.jsonl").exists()
       and not (OUT / "stage1_analysis.json").exists())
else:
    ck("main_complete", complete)
ck("task_cap", 0.60 + sum(x["cost_cny"] for x in attempts) <= 20)
if (OUT / "stage1_analysis.json").exists():
    stage = read(OUT / "stage1_analysis.json")
    ck("stage1_denominator", stage["n"] == 96 and stage["patients"] == 16)
    predictions = lines(OUT / "stage1_predictions.jsonl")
    for arm in ("B", "E", "C"):
        ck("stage1_arm_correct:" + arm, stage["final_metrics"][arm]["correct"] == sum(x["GT"] == y["PriorG"] for x in gt for y in predictions if x["id"] == y["id"] and y["arm"] == arm))
    gate = read(OUT / "stage1_gate.json")
    ck("gate_formula", gate["effect_gate"] == all(gate["frozen_gate_conditions"].values()))
    ck("frozen_budget_gate", gate["budget_gate"] ==
       (stage["cost_used_reserved_cny"] + gate["projected_repeat_cny"] * 1.2 + 0.8 <= 20))
    ck("repeat_stop_respected", gate["stage2_authorized_by_frozen_gate"] or
       not (OUT / "repeat_jobs.jsonl").exists())
    if (OUT / "stage1_changed_cases.jsonl").exists():
        changed = set()
        for pair in list(stage["final_pairs"].values()) + list(stage["raw_pairs"].values()) + [stage["B_vs_historical"]]:
            changed.update(pair["rescue_ids"])
            changed.update(pair["harm_ids"])
        cases = lines(OUT / "stage1_changed_cases.jsonl")
        ck("changed_case_ledger_complete", {x["id"] for x in cases} == changed and len(cases) == len(changed))
        ck("changed_case_references_intact", all(
            hashlib.sha256(x["reference"].encode()).hexdigest() == x["reference_sha256"] for x in cases))
    if (OUT / "cost_summary.json").exists():
        summary = read(OUT / "cost_summary.json")
        ck("cost_summary_matches_receipts", summary["071_api_attempts"] == len(attempts) and
           abs(summary["task_used_or_reserved_cny"] - (0.60 + sum(x["cost_cny"] for x in attempts))) < 1e-8)
    if gate["stage2_authorized_by_frozen_gate"]:
        repjobs = lines(OUT / "repeat_jobs.jsonl")
        ck("repeat_exact_bodies", len(repjobs) == 192 and all(j["body"] == by[(j["id"], j["arm"])]["body"] for j in repjobs))
        if (OUT / "repeat_analysis.json").exists():
            rep = read(OUT / "repeat_analysis.json")
            ck("repeat_complete", rep["n"] == 96 and sum(x["stage"] == "repeat" for x in attempts) == 192)
result = {"status": "PASS" if all(x["ok"] for x in checks) else "FAIL", "checks": len(checks),
          "failures": [x for x in checks if not x["ok"]], "api_attempts_071": len(attempts),
          "cost_plus_prior_reserve_cny": 0.60 + sum(x["cost_cny"] for x in attempts),
          "method_gate_evaluated": (OUT / "stage1_gate.json").exists(),
          "independent_audit": False}
(OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: result[k] for k in ("status", "checks", "failures", "api_attempts_071", "cost_plus_prior_reserve_cny")}, ensure_ascii=False))
if result["status"] != "PASS":
    raise SystemExit(1)
