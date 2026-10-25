"""Diagnose exact-body repeat variation; preserve initial Stage 1 as canonical."""
from __future__ import annotations

import copy
import json

import analyze081 as a
import blind081 as b
import run081 as r
from common053 import VALID, parse_response, decision
from common066 import priorg


def main():
    jobs = r.jobs("repeat")
    attempts, success = r.state()
    assert len(jobs) == 144 and all(j["request_id"] in success for j in jobs)
    first = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/case_results.jsonl")}
    original = {(x["id"], x["arm"]): x for x in r.jobs("judge")}
    fallback, _ = a.old_u2()
    repeat_rows, invalid = [], []
    for pid in sorted({j["id"] for j in jobs}):
        source = first[pid]
        row = copy.deepcopy(source)
        row["methods"] = {}
        row["arms"] = {}
        for arm in ("B", "U", "T"):
            j = next(x for x in jobs if x["id"] == pid and x["arm"] == arm)
            assert j["body_sha256"] == original[pid, arm]["body_sha256"]
            parsed = parse_response(success[j["request_id"]]["transport"], True, True)
            valid = parsed["status"] in VALID and parsed.get("scores") is not None
            method = ({"raw": parsed["verdict"], "U0": decision(parsed["scores"], 0),
                       "PriorG": priorg(parsed["scores"])} if valid else
                      {"raw": fallback[pid], "U0": fallback[pid], "PriorG": fallback[pid]})
            if not valid:
                invalid.append({"id": pid, "arm": arm, "status": parsed["status"],
                                "errors": parsed.get("errors"), "fallback": fallback[pid]})
            row["methods"][arm] = method
            row["arms"][arm] = {"valid": valid, "status": parsed["status"],
                                "scores": parsed.get("scores"), "raw_verdict": parsed.get("verdict"),
                                "body_sha256": j["body_sha256"],
                                "attempt_id": success[j["request_id"]]["attempt"]["attempt_id"]}
        repeat_rows.append(row)
    initial_rows = [first[x["id"]] for x in repeat_rows]
    flips = {mode: {arm: sum(x["methods"][arm][mode] != first[x["id"]]["methods"][arm][mode]
                             for x in repeat_rows) for arm in ("B", "U", "T")}
             for mode in ("raw", "U0", "PriorG")}
    pairs = {run: [a.pair(rows, base, cand, mode)
                    for mode in ("raw", "U0", "PriorG") for base, cand in (("B", "U"), ("B", "T"), ("U", "T"))]
             for run, rows in (("initial", initial_rows), ("repeat", repeat_rows))}
    metrics = {run: [a.score(rows, arm, mode) for mode in ("raw", "U0", "PriorG") for arm in ("B", "U", "T")]
               for run, rows in (("initial", initial_rows), ("repeat", repeat_rows))}
    event_consistency = {}
    for arm in ("U", "T"):
        initial_benefit = {x["id"] for x in initial_rows if x["methods"]["B"]["PriorG"] != x["GT"]
                           and x["methods"][arm]["PriorG"] == x["GT"]}
        initial_harm = {x["id"] for x in initial_rows if x["methods"]["B"]["PriorG"] == x["GT"]
                        and x["methods"][arm]["PriorG"] != x["GT"]}
        repeat_benefit = {x["id"] for x in repeat_rows if x["methods"]["B"]["PriorG"] != x["GT"]
                          and x["methods"][arm]["PriorG"] == x["GT"]}
        repeat_harm = {x["id"] for x in repeat_rows if x["methods"]["B"]["PriorG"] == x["GT"]
                       and x["methods"][arm]["PriorG"] != x["GT"]}
        event_consistency[arm] = {"initial_beneficial": sorted(initial_benefit),
                                  "repeat_beneficial": sorted(repeat_benefit),
                                  "both_beneficial": sorted(initial_benefit & repeat_benefit),
                                  "initial_harmful": sorted(initial_harm),
                                  "repeat_harmful": sorted(repeat_harm),
                                  "both_harmful": sorted(initial_harm & repeat_harm)}
    total = sum(x["cost_cny"] for x in attempts)
    assert total <= 20
    result = {"n_claims": 48, "patients": 24, "repeat_requests": 144,
              "initial_canonical_unchanged": True, "all_body_hashes_exact": True,
              "invalid_repeat": invalid, "first_to_repeat_flips": flips,
              "metrics": metrics, "pairs": pairs, "event_consistency": event_consistency,
              "task_total_cost_cny": total,
              "repeat_cost_cny": sum(x["cost_cny"] for x in attempts if x["stage"] == "repeat"),
              "attempts": len(attempts)}
    a.write("repeat_case_results.jsonl", repeat_rows)
    a.write("repeat_results.json", result)
    a.write("cost_ledger_final.json", {"cap_cny": 20, "task_total_estimated_cny": total,
                                       "stage_costs": {stage: sum(x["cost_cny"] for x in attempts if x["stage"] == stage)
                                                       for stage in r.STAGES},
                                       "attempts": attempts,
                                       "unknown_attempts": [x for x in attempts if x["http_status"] == 0]})
    print(json.dumps({"cost": total, "repeat_cost": result["repeat_cost_cny"],
                      "flips": flips["PriorG"], "initial_repeat_pairs":
                      [(run, p["base"], p["candidate"], p["net"])
                       for run, ps in pairs.items() for p in ps if p["mode"] == "PriorG"]}))


if __name__ == "__main__":
    main()
