"""Build and freeze all Stage 1 U artifacts without loading GT or old predictions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import blind081 as b
import selector081 as s
import run081 as r

sys.path.insert(0, str(b.ROOT / "tasks/008_retrieval_planning"))
import planning_core as evidence


def rows():
    sample = b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl")
    return [x for x in sample if x["stage"] == 1]


def write(path, value):
    with (b.OUT / path).open("x", encoding="utf-8", newline="\n") as f:
        if isinstance(value, list):
            for x in value:
                f.write(s.compact(x) + "\n")
        else:
            f.write(s.compact(value) + "\n")


def freeze(stage, source, jobs):
    path = b.OUT / f"{stage}_jobs.jsonl"
    write(path.name, jobs)
    write(f"{stage}_freeze.json", {"stage": stage, "status": "FROZEN_BEFORE_STAGE_API",
                                     "source_sha256": b.sha(b.OUT / source),
                                     "jobs_sha256": b.sha(path), "n": len(jobs)})


def require_complete(stage):
    jobs = r.jobs(stage)
    _, success = r.state()
    missing = [x["request_id"] for x in jobs if x["request_id"] not in success]
    assert not missing, (stage, "missing", len(missing), missing[:3])
    return jobs, success


def planfreeze():
    stage = "u_plan"
    source = b.OUT / "u_plan_jobs.jsonl"
    assert b.sha(source) == json.loads((b.OUT / "sample_freeze.json").read_text())["u_plan_jobs_sha256"]
    write(f"{stage}_freeze.json", {"stage": stage, "status": "FROZEN_BEFORE_STAGE_API",
                                     "source_sha256": b.sha(b.OUT / "sample_freeze.json"),
                                     "jobs_sha256": b.sha(source), "n": 96})
    print("U planner 96 requests frozen")


def composefreeze():
    jobs, success = require_complete("u_plan")
    by_id = {j["id"]: j for j in jobs}
    parsed, compose = [], []
    for x in rows():
        pid = x["id"]
        result = s.parse_plan(success[by_id[pid]["request_id"]]["transport"])
        if result["status"] != "valid":
            result["requirements"] = [x["claim"]]
            result["fallback"] = "claim_as_single_requirement"
        parsed.append({"id": pid, "result": result,
                       "receipt_sha256": b.sha(b.ROOT / success[by_id[pid]["request_id"]]["attempt"]["path"].replace("request.json", "receipt.json"))})
        cand_lines = [s.candidate_line(c["short_id"], c) for c in x["candidates"]]
        body = s.compose_body(x["claim"], result["requirements"], cand_lines)
        compose.append({"request_id": "081_s1_U_compose_" + pid, "id": pid,
                        "stage": "u_compose", "body": body, "body_sha256": b.digest(body)})
    write("u_plan_parsed.jsonl", parsed)
    freeze("u_compose", "u_plan_parsed.jsonl", compose)
    print(json.dumps({"u_plan_valid": sum(x["result"]["status"] == "valid" for x in parsed),
                      "u_compose_frozen": len(compose)}))


def packfreeze():
    jobs, success = require_complete("u_compose")
    by_id = {j["id"]: j for j in jobs}
    packs = []
    for x in rows():
        pid = x["id"]
        allowed = {c["short_id"]: c for c in x["candidates"]}
        tr = success[by_id[pid]["request_id"]]["transport"]
        result = s.parse_compose(tr, allowed)
        if result["status"] == "valid":
            selected = [allowed[q]["passage_id"] for q in result["selected"]]
            passages = {c["passage_id"]: c for c in x["candidates"]}
            scores = {q: float(len(selected) - j) for j, q in enumerate(selected)}
            pack = evidence.select_evidence(selected, scores, passages, x["admission"],
                                            cap=8000, max_items=16, max_per_note=2)
            if not pack["selected_ids"]:
                result["status"] = "invalid_empty_final_pack"
        if result["status"] != "valid":
            pack = {"selected_ids": x["baseline_ids"], "relevance_order": x["baseline_ids"],
                    "selection_skips": [], "reference": x["baseline_reference"],
                    "reference_sha256": b.digest(x["baseline_reference"]),
                    "body_characters": len(x["baseline_reference"]), "character_ceiling": 8000}
            result["fallback"] = "baseline_reference"
        assert set(pack["selected_ids"]) <= {c["passage_id"] for c in x["candidates"]}
        assert len(pack["selected_ids"]) <= 16
        packs.append({"id": pid, "sid": x["sid"], "arm": "U", "selector": result,
                      "pack": pack, "compose_body_sha256": by_id[pid]["body_sha256"],
                      "receipt_sha256": b.sha(b.ROOT / success[by_id[pid]["request_id"]]["attempt"]["path"].replace("request.json", "receipt.json"))})
    write("u_packs.jsonl", packs)
    write("u_packs_freeze.json", {"status": "ALL_96_U_PACKS_FROZEN_BEFORE_GT",
                                   "sample_sha256": b.sha(b.OUT / "sample_blind.jsonl"),
                                   "u_plan_jobs_sha256": b.sha(b.OUT / "u_plan_jobs.jsonl"),
                                   "u_compose_jobs_sha256": b.sha(b.OUT / "u_compose_jobs.jsonl"),
                                   "u_packs_sha256": b.sha(b.OUT / "u_packs.jsonl"),
                                   "n": 96,
                                   "fallback_n": sum(x["selector"]["status"] != "valid" for x in packs)})
    print(json.dumps({"u_packs_frozen": 96,
                      "fallback_n": sum(x["selector"]["status"] != "valid" for x in packs)}))


if __name__ == "__main__":
    {"planfreeze": planfreeze, "composefreeze": composefreeze, "packfreeze": packfreeze}[sys.argv[1]]()
