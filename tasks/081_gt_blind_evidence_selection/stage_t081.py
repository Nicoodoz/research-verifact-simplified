"""After U pack freeze, build GT-aware teacher and concurrent B/U/T Judge jobs."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys

import blind081 as b
import selector081 as s
import run081 as r
import stage_u081 as u

LABELS = ("Supported", "Not Supported", "Not Addressed")
COHORT = "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
TEMPLATE = "outputs/053_thinking_prior_validation/main_jobs.jsonl"


def require_u_frozen():
    x = r.read(b.OUT / "u_packs_freeze.json")
    assert x["status"] == "ALL_96_U_PACKS_FROZEN_BEFORE_GT"
    assert x["u_packs_sha256"] == b.sha(b.OUT / "u_packs.jsonl")
    assert x["sample_sha256"] == b.sha(b.OUT / "sample_blind.jsonl")
    return x


def gt():
    require_u_frozen()
    with (b.ROOT / COHORT).open(encoding="utf-8-sig", newline="") as f:
        return {x["proposition_id"]: x for x in csv.DictReader(f)}


def planfreeze():
    records = gt()
    jobs, labels = [], []
    for x in u.rows():
        m = records[x["id"]]
        assert m["subject_id"] == x["sid"] and m["author_type"] == x["author"]
        assert m["invalid"] == "False" and m["proposition_type"] == "claim"
        label = m["human_gt"]
        assert label in LABELS
        labels.append({"id": x["id"], "sid": x["sid"], "author": x["author"], "GT": label})
        body = s.plan_body(x["claim"], label)
        jobs.append({"request_id": "081_s1_T_plan_" + x["id"], "id": x["id"],
                     "stage": "t_plan", "body": body, "body_sha256": b.digest(body)})
    u.write("stage1_labels.jsonl", labels)
    u.freeze("t_plan", "stage1_labels.jsonl", jobs)
    u.write("gt_join_freeze.json", {"status": "AFTER_ALL_U_PACKS_FROZEN",
                                    "u_pack_freeze_sha256": b.sha(b.OUT / "u_packs_freeze.json"),
                                    "gt_source_sha256": b.sha(b.ROOT / COHORT),
                                    "labels_sha256": b.sha(b.OUT / "stage1_labels.jsonl"), "n": 96})
    print(json.dumps({"t_plan_frozen": 96, "gt_counts": {k: sum(x["GT"] == k for x in labels) for k in LABELS}}))


def composefreeze():
    require_u_frozen()
    jobs, success = u.require_complete("t_plan")
    by_id = {j["id"]: j for j in jobs}
    labels = {x["id"]: x["GT"] for x in b.lines("outputs/081_gt_blind_evidence_selection/stage1_labels.jsonl")}
    parsed, compose = [], []
    for x in u.rows():
        pid = x["id"]
        result = s.parse_plan(success[by_id[pid]["request_id"]]["transport"])
        if result["status"] != "valid":
            result["requirements"] = [x["claim"]]
            result["fallback"] = "claim_as_single_requirement"
        parsed.append({"id": pid, "result": result})
        cand_lines = [s.candidate_line(c["short_id"], c) for c in x["candidates"]]
        body = s.compose_body(x["claim"], result["requirements"], cand_lines, labels[pid])
        compose.append({"request_id": "081_s1_T_compose_" + pid, "id": pid,
                        "stage": "t_compose", "body": body, "body_sha256": b.digest(body)})
    u.write("t_plan_parsed.jsonl", parsed)
    u.freeze("t_compose", "t_plan_parsed.jsonl", compose)
    print(json.dumps({"t_plan_valid": sum(x["result"]["status"] == "valid" for x in parsed),
                      "t_compose_frozen": 96}))


def packfreeze():
    require_u_frozen()
    jobs, success = u.require_complete("t_compose")
    by_id = {j["id"]: j for j in jobs}
    packs = []
    for x in u.rows():
        pid = x["id"]
        allowed = {c["short_id"]: c for c in x["candidates"]}
        result = s.parse_compose(success[by_id[pid]["request_id"]]["transport"], allowed)
        if result["status"] == "valid":
            selected = [allowed[q]["passage_id"] for q in result["selected"]]
            passages = {c["passage_id"]: c for c in x["candidates"]}
            scores = {q: float(len(selected) - j) for j, q in enumerate(selected)}
            pack = u.evidence.select_evidence(selected, scores, passages, x["admission"], cap=8000,
                                               max_items=16, max_per_note=2)
            if not pack["selected_ids"]:
                result["status"] = "invalid_empty_final_pack"
        if result["status"] != "valid":
            pack = {"selected_ids": x["baseline_ids"], "relevance_order": x["baseline_ids"],
                    "selection_skips": [], "reference": x["baseline_reference"],
                    "reference_sha256": hashlib.sha256(x["baseline_reference"].encode()).hexdigest(),
                    "body_characters": len(x["baseline_reference"]), "character_ceiling": 8000}
            result["fallback"] = "baseline_reference"
        packs.append({"id": pid, "sid": x["sid"], "arm": "T", "selector": result,
                      "pack": pack, "compose_body_sha256": by_id[pid]["body_sha256"]})
    u.write("t_packs.jsonl", packs)
    u.write("t_packs_freeze.json", {"status": "ALL_96_T_PACKS_FROZEN", "n": 96,
                                   "t_packs_sha256": b.sha(b.OUT / "t_packs.jsonl"),
                                   "u_packs_sha256": b.sha(b.OUT / "u_packs.jsonl"),
                                   "fallback_n": sum(x["selector"]["status"] != "valid" for x in packs)})
    print(json.dumps({"t_packs_frozen": 96,
                      "fallback_n": sum(x["selector"]["status"] != "valid" for x in packs)}))


def judgefreeze():
    require_u_frozen()
    assert r.read(b.OUT / "t_packs_freeze.json")["t_packs_sha256"] == b.sha(b.OUT / "t_packs.jsonl")
    templates = [x for x in b.lines(TEMPLATE) if x["condition"] == "T-S"]
    assert templates
    template = templates[0]["body"]
    assert template["model"] == "deepseek-v4-flash-0731"
    assert template["enable_thinking"] is True and template["reasoning_effort"] == "high"
    sample = u.rows()
    us = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/u_packs.jsonl")}
    ts = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/t_packs.jsonl")}
    jobs = []
    for x in sample:
        for arm, ref in (("B", x["baseline_reference"]), ("U", us[x["id"]]["pack"]["reference"]),
                         ("T", ts[x["id"]]["pack"]["reference"])):
            body = copy.deepcopy(template)
            body["messages"][1]["content"] = json.dumps({"proposition": x["claim"], "reference": ref},
                                                            ensure_ascii=False, separators=(",", ":"))
            assert "clinician_label" not in body["messages"][1]["content"]
            jobs.append({"request_id": "081_s1_Judge_" + arm + "_" + x["id"],
                         "id": x["id"], "sid": x["sid"], "arm": arm, "stage": "judge",
                         "body": body, "body_sha256": b.digest(body)})
    jobs.sort(key=lambda j: hashlib.sha256(("081/judge/v1:" + j["id"] + j["arm"]).encode()).hexdigest())
    assert len(jobs) == 288
    u.freeze("judge", "t_packs_freeze.json", jobs)
    u.write("judge_extra_freeze.json", {"template_source_sha256": b.sha(b.ROOT / TEMPLATE),
                                        "sample_sha256": b.sha(b.OUT / "sample_blind.jsonl"),
                                        "u_packs_sha256": b.sha(b.OUT / "u_packs.jsonl"),
                                        "t_packs_sha256": b.sha(b.OUT / "t_packs.jsonl"),
                                        "jobs_sha256": b.sha(b.OUT / "judge_jobs.jsonl"), "n": 288})
    print("288 interleaved B/U/T Judge requests frozen")


if __name__ == "__main__":
    {"planfreeze": planfreeze, "composefreeze": composefreeze,
     "packfreeze": packfreeze, "judgefreeze": judgefreeze}[sys.argv[1]]()
