"""Deterministic source, leakage-order, request, pack, and result self-checks."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import blind081 as b
import run081 as r
import stage_u081 as u


def check(condition, name, results):
    if not condition:
        raise AssertionError(name)
    results.append(name)


def main():
    passed = []
    sf = r.read(b.OUT / "sample_freeze.json")
    check(sf["status"] == "SAMPLE_AND_U_PLAN_FROZEN_BEFORE_GT_AND_API", "sample_frozen", passed)
    for path, expected in sf["source_sha256"].items():
        check(b.sha(b.ROOT / path) == expected, "source_sha:" + path, passed)
    for name, key in (("sample_blind.jsonl", "sample_blind_sha256"),
                      ("overlap_manifest.jsonl", "overlap_manifest_sha256"),
                      ("u_plan_jobs.jsonl", "u_plan_jobs_sha256")):
        check(b.sha(b.OUT / name) == sf[key], "sample_artifact:" + name, passed)
    sample = b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl")
    check(len(sample) == 192 and len({x["id"] for x in sample}) == 192, "sample_192_unique", passed)
    check(Counter((x["sid"], x["stage"]) for x in sample) ==
          Counter({(sid, stage): 4 for sid in {x["sid"] for x in sample} for stage in (1, 2)}),
          "24_patients_4_each_disjoint", passed)
    calibration = set(r.read(b.ROOT / "outputs/051_thinking_mode_validation/freeze.json")["patient_pool"])
    check(not calibration & {x["sid"] for x in sample}, "PriorG_calibration_patient_isolation", passed)
    eligible, _, _, _, _ = b.load()
    for x in sample:
        check(x["id"] in eligible and x["baseline_ids"] == eligible[x["id"]]["baseline_ids"],
              "blind_source:" + x["id"], passed)
    code = (b.ROOT / "tasks/081_gt_blind_evidence_selection")
    for name in ("blind081.py", "selector081.py", "prepare_blind081.py", "stage_u081.py"):
        source = (code / name).read_text(encoding="utf-8")
        check("cohort_master.csv" not in source and "outputs/066_oracle_headroom/" not in source
              and "stage_t081" not in source and "human_gt" not in source,
              "U_code_no_GT_prediction_oracle_source:" + name, passed)
    uf = r.read(b.OUT / "u_packs_freeze.json")
    gf = r.read(b.OUT / "gt_join_freeze.json")
    check(uf["u_packs_sha256"] == b.sha(b.OUT / "u_packs.jsonl"), "U_pack_hash", passed)
    check(gf["u_pack_freeze_sha256"] == b.sha(b.OUT / "u_packs_freeze.json"), "GT_join_after_U_hash", passed)
    check((b.OUT / "u_packs_freeze.json").stat().st_mtime < (b.OUT / "stage1_labels.jsonl").stat().st_mtime,
          "U_freeze_precedes_GT_join", passed)
    stage1 = {x["id"]: x for x in sample if x["stage"] == 1}
    ups = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/u_packs.jsonl")}
    tps = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/t_packs.jsonl")}
    check(set(stage1) == set(ups) == set(tps), "complete_pack_IDs", passed)
    for pid, x in stage1.items():
        c48 = {z["passage_id"] for z in x["candidates"]}
        for arm, pack in (("U", ups[pid]), ("T", tps[pid])):
            ids = pack["pack"]["selected_ids"]
            check(len(ids) <= 16 and set(ids) <= c48 and len(ids) == len(set(ids)),
                  f"{arm}_C48_only:{pid}", passed)
            if pack["selector"]["status"] != "valid":
                check(pack["pack"]["reference"] == x["baseline_reference"],
                      f"{arm}_predeclared_fallback:{pid}", passed)
            else:
                passes = {z["passage_id"]: z for z in x["candidates"]}
                order = pack["pack"]["relevance_order"]
                rebuilt = u.evidence.select_evidence(order, {q: len(order)-i for i, q in enumerate(order)},
                                                      passes, x["admission"], cap=8000, max_items=16, max_per_note=2)
                check(rebuilt["reference"] == pack["pack"]["reference"] and rebuilt["selected_ids"] == ids,
                      f"{arm}_verbatim_formatter:{pid}", passed)
    for stage in r.STAGES:
        jobs = r.jobs(stage)
        check(len(jobs) == (288 if stage == "judge" else 144 if stage == "repeat" else 96),
              stage + "_job_count", passed)
        check((b.OUT / f"{stage}_jobs.jsonl").stat().st_mtime <=
              min((b.ROOT / x["path"]).stat().st_mtime for x in r.state()[0] if x["stage"] == stage),
              stage + "_jobs_before_attempts", passed)
    for phase in ("plan", "compose"):
        uj = {x["id"]: x for x in r.jobs("u_" + phase)}
        tj = {x["id"]: x for x in r.jobs("t_" + phase)}
        for pid in stage1:
            ub, tb = uj[pid]["body"], tj[pid]["body"]
            check({k: v for k, v in ub.items() if k != "messages"} ==
                  {k: v for k, v in tb.items() if k != "messages"} and
                  ub["messages"][0] == tb["messages"][0],
                  "paired_selector_settings:" + phase + ":" + pid, passed)
            up, tp = json.loads(ub["messages"][1]["content"]), json.loads(tb["messages"][1]["content"])
            check("clinician_label" not in up and tp.pop("clinician_label") in
                  ("Supported", "Not Supported", "Not Addressed") and
                  (up == tp if phase == "plan" else
                   up["proposition"] == tp["proposition"] and up["candidates"] == tp["candidates"]),
                  "T_only_GT_extra_input:" + phase + ":" + pid, passed)
    judges = r.jobs("judge")
    check([j["request_id"] for j in judges] ==
          [j["request_id"] for j in sorted(judges, key=lambda j: hashlib.sha256(("081/judge/v1:"+j["id"]+j["arm"]).encode()).hexdigest())],
          "judge_hash_interleave", passed)
    for job in judges:
        data = json.loads(job["body"]["messages"][1]["content"])
        x = stage1[job["id"]]
        ref = x["baseline_reference"] if job["arm"] == "B" else (ups if job["arm"] == "U" else tps)[job["id"]]["pack"]["reference"]
        check(set(data) == {"proposition", "reference"} and data["proposition"] == x["claim"] and data["reference"] == ref,
              "judge_no_leak_and_exact_reference:" + job["request_id"], passed)
    attempts, success = r.state()
    check(len(success) == 816 and set(success) == {j["request_id"] for stage in r.STAGES for j in r.jobs(stage)},
          "all_816_logical_success", passed)
    check(sum(x["cost_cny"] for x in attempts) <= 20, "cost_cap", passed)
    result = r.read(b.OUT / "results.json")
    check(result["n"] == 96 and result["patients"] == 24 and result["logical_requests"] == 672,
          "complete_result", passed)
    repeat = r.read(b.OUT / "repeat_results.json")
    check(repeat["n_claims"] == 48 and repeat["repeat_requests"] == 144 and
          repeat["task_total_cost_cny"] <= 20, "repeat_diagnostic_complete", passed)
    report = {"status": "PASS", "checks": len(passed), "cost_cny": sum(x["cost_cny"] for x in attempts),
              "sample_sha256": b.sha(b.OUT / "sample_blind.jsonl"),
              "results_sha256": b.sha(b.OUT / "results.json"),
              "scope": "executor self-check only; no independent audit"}
    output = b.OUT / "self_check.json"
    if output.exists():
        check(r.read(output) == report, "saved_self_check_replay", passed)
    else:
        with output.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
