"""Offline operational diagnosis after frozen stop; no partial outcome claims."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(ROOT / "tasks/071_judge_icl_feasibility"))
import run071  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


jobs = run071.lines(OUT / "main_jobs.jsonl")
attempts, terminal = run071.state()
main_attempts = [x for x in attempts if x["stage"] == "main"]
started = {x["id"] for x in main_attempts}
byrid = {j["request_id"]: j for j in jobs}
byarm = {arm: {j["id"] for j in jobs if j["arm"] == arm and j["request_id"] in terminal} for arm in ("B", "E", "C")}
costs = defaultdict(float)
for x in attempts:
    if x["id"] in byrid:
        costs[byrid[x["id"]]["arm"]] += x["cost_cny"]
    else:
        costs["preflight"] += x["cost_cny"]
unknown = []
for x in main_attempts:
    if x["http_status"] != 0:
        continue
    path = ROOT / x["request_path"]
    req, receipt = read(path), read(path.parent / "receipt.json")
    unknown.append({"request_id": x["id"], "id": req["job"]["id"], "arm": req["job"]["arm"],
                    "reservation_cny": req["reservation_cny"],
                    "transport_diagnostic": receipt["transport"].get("transport_diagnostic"),
                    "request_path": x["request_path"], "receipt_path": str((path.parent / "receipt.json").relative_to(ROOT)).replace("\\", "/")})
out = {"task_status": "STOPPED_AFTER_TRANSPORT_UNKNOWN", "frozen_main_jobs": len(jobs),
       "preflight_http200": "071_preflight_001" in terminal,
       "main_http200": sum(x["http_status"] == 200 for x in main_attempts),
       "main_unknown": len(unknown), "main_unsent": len(jobs)-len(started),
       "attempts_total": len(attempts),
       "answered_by_arm": {arm: len(byarm[arm]) for arm in byarm},
       "all_three_answered_cases": len(set.intersection(*(byarm[arm] for arm in byarm))),
       "parsed_status": dict(Counter(terminal[x["id"]]["parsed"].get("status") for x in main_attempts if x["id"] in terminal)),
       "unknown_receipts": unknown,
       "actual_or_reserved_by_arm_cny": dict(costs),
       "prior_key_checks_conservative_reserve_cny": run071.PRIOR_RESERVED,
       "cumulative_actual_plus_unknown_reserve_cny": run071.PRIOR_RESERVED + sum(x["cost_cny"] for x in attempts),
       "cap_cny": run071.CAP, "method_gate_evaluated": False,
       "reason": "Five RemoteDisconnected and one DNS gaierror among six concurrent in-flight requests; each outcome unknown. No resend or additional dispatch."}
assert out["frozen_main_jobs"] == 288
assert out["main_http200"] + out["main_unknown"] + out["main_unsent"] == 288
assert out["main_unknown"] == 6 and out["main_unsent"] == 174
assert out["cumulative_actual_plus_unknown_reserve_cny"] <= 20
(OUT / "execution_diagnosis.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: out[k] for k in ("task_status", "preflight_http200", "main_http200", "main_unknown", "main_unsent", "answered_by_arm", "all_three_answered_cases", "parsed_status", "cumulative_actual_plus_unknown_reserve_cny")}, ensure_ascii=False))
