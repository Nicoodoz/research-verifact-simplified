"""Freeze outcome-independent patient-stratified exact-body repeats after Stage 1."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import blind081 as b
import run081 as r
import stage_u081 as u


def h(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    results = r.read(b.OUT / "results.json")
    assert results["teacher_gate"] and results["blind_gate"]
    assert results["old_B_fluctuation"]["PriorG"]["flips"] >= 1
    assert not (b.OUT / "repeat_jobs.jsonl").exists()
    by_patient = defaultdict(list)
    for x in u.rows():
        by_patient[x["sid"]].append(x["id"])
    selected = sorted(pid for sid, ids in by_patient.items()
                      for pid in sorted(ids, key=lambda z: h("081/repeat/v1:" + z))[:2])
    assert len(selected) == 48 and len({next(x["sid"] for x in u.rows() if x["id"] == pid) for pid in selected}) == 24
    original = {(j["id"], j["arm"]): j for j in r.jobs("judge")}
    attempts, success = r.state()
    first_cost = sum(success[original[pid, arm]["request_id"]]["attempt"]["cost_cny"]
                     for pid in selected for arm in ("B", "U", "T"))
    current = sum(x["cost_cny"] for x in attempts)
    assert current + 1.5 * first_cost <= 20, (current, first_cost)
    jobs = []
    for pid in selected:
        for arm in ("B", "U", "T"):
            prior = original[pid, arm]
            jobs.append({"request_id": "081_repeat_" + arm + "_" + pid, "id": pid,
                         "sid": prior["sid"], "arm": arm, "stage": "repeat",
                         "body": prior["body"], "body_sha256": prior["body_sha256"],
                         "first_request_id": prior["request_id"]})
    jobs.sort(key=lambda j: h("081/repeat_send/v1:" + j["id"] + j["arm"]))
    decision = {"status": "FROZEN_AFTER_STAGE1_BEFORE_REPEAT_SEND", "reason": "Stage 1 gates pass narrowly and old/new exact B flips may alter interpretation; no first-pass answer used for ID selection",
                "selection": "two of four Stage1 IDs per patient, smallest SHA256(081/repeat/v1:id)",
                "n_claims": 48, "patients": 24, "requests": 144,
                "selection_ids": selected, "first_pass_results_sha256": b.sha(b.OUT / "results.json"),
                "first_pass_cost_cny": current, "selected_first_pass_judge_cost_cny": first_cost,
                "repeat_conservative_estimate_cny": 1.5 * first_cost,
                "remaining_after_estimate_cny": 20 - current - 1.5 * first_cost,
                "interpretation": "Diagnostic only; do not replace initial answers or revise frozen gates"}
    u.write("repeat_decision.json", decision)
    u.freeze("repeat", "repeat_decision.json", jobs)
    print(json.dumps({"repeat_n": 48, "requests": 144, "first_cost": first_cost,
                      "current": current, "estimate_1_5x": 1.5 * first_cost,
                      "remaining_buffer": 20 - current - 1.5 * first_cost}))


if __name__ == "__main__":
    main()
