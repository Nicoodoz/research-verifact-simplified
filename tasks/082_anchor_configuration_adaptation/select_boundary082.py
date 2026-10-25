"""Use calibration patients only to freeze the enriched view and paired F4 jobs."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict

import inventory082 as i
import prepare082 as p
import run082 as r

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
from common053 import LABELS, VALID, parse_response
from common066 import priorg

PAIRS = (("Supported", "Not Supported"), ("Supported", "Not Addressed"),
         ("Not Supported", "Not Addressed"))


def train_gt(train_patients):
    path = ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["subject_id"] not in train_patients:
                continue  # Evaluation human_gt is never accessed or retained here.
            if row["proposition_type"] == "claim" and row["invalid"] == "False":
                assert row["human_gt"] in LABELS
                out[row["proposition_id"]] = row
    return out, p.sha(path)


def attributes(scores):
    order = sorted(LABELS, key=lambda lab: (-float(scores[lab]), LABELS.index(lab)))
    a, b = order[:2]
    pair = next((pair for pair in PAIRS if set(pair) == {a, b}), None)
    assert pair is not None
    margin = math.log(max(float(scores[a]) / 100, 1e-6)) - math.log(max(float(scores[b]) / 100, 1e-6))
    return {"pair": "/".join(pair), "margin": margin, "raw_top": a,
            "PriorG": priorg(scores), "raw_prior_disagree": a != priorg(scores)}


def main():
    jobs = r.jobs("screen_B")
    attempts, answered = r.answers("screen_B")
    assert len(answered) == len(jobs) == 420, "No partial view construction"
    blind = i.lines("outputs/082_anchor_configuration_adaptation/train_screen_blind.jsonl")
    by_job = {j["id"]: j for j in jobs}
    gt, gt_sha = train_gt({x["sid"] for x in blind})
    scored, invalid = {}, []
    for x in blind:
        pid = x["id"]
        assert pid in gt and gt[pid]["subject_id"] == x["sid"] and gt[pid]["author_type"] == x["author"]
        ans = answered[by_job[pid]["request_id"]]
        parsed = parse_response(ans["transport"], True, True)
        assert parsed.get("model_returned") in (None, r.MODEL)
        valid = parsed["status"] in VALID and parsed.get("scores") is not None
        item = {"id": pid, "sid": x["sid"], "GT": gt[pid]["human_gt"], "author": x["author"],
                "rank": x["rank"], "is_R": x["is_R"], "is_E_core": x["is_E_core"],
                "status": parsed["status"], "valid": valid, "scores": parsed.get("scores"),
                "raw": parsed.get("verdict"), "body_sha256": by_job[pid]["body_sha256"],
                "mode": ans["mode"], "source": ans.get("receipt_source") or ans.get("attempt", {}).get("receipt_source")}
        if valid:
            item.update(attributes(parsed["scores"]))
        else:
            invalid.append({"id": pid, "sid": x["sid"], "status": parsed["status"], "errors": parsed.get("errors")})
        scored[pid] = item
    core = [x for x in blind if x["is_E_core"]]
    pool = [scored[x["id"]] for x in blind if not x["is_E_core"] and scored[x["id"]]["valid"]]
    buckets = defaultdict(list)
    for x in pool:
        buckets[x["pair"], x["GT"]].append(x)
    for key in buckets:
        buckets[key].sort(key=lambda x: (x["margin"], not x["raw_prior_disagree"],
                                         p.stable("082/boundary/v1:", x["id"]), x["id"]))
    keys = [("/".join(pair), gt) for pair in PAIRS for gt in LABELS]
    selected, used, patient_n = [], set(), Counter()
    while len(selected) < 70:
        moved = False
        for key in keys:
            queue = buckets[key]
            while queue and (queue[0]["id"] in used or patient_n[queue[0]["sid"]] >= 8):
                queue.pop(0)
            if queue and len(selected) < 70:
                x = queue.pop(0)
                selected.append(x)
                used.add(x["id"])
                patient_n[x["sid"]] += 1
                moved = True
        if not moved:
            break
    if len(selected) < 70:
        rest = sorted((x for x in pool if x["id"] not in used),
                      key=lambda x: (not x["raw_prior_disagree"], x["margin"],
                                     p.stable("082/boundary-fill/v1:", x["id"])))
        for x in rest:
            if len(selected) >= 70:
                break
            if patient_n[x["sid"]] < 10:
                selected.append(x)
                used.add(x["id"])
                patient_n[x["sid"]] += 1
    assert len(selected) == 70
    R = [x["id"] for x in blind if x["is_R"]]
    E = [x["id"] for x in core] + [x["id"] for x in selected]
    assert len(R) == len(E) == 308 and len(set(R) & set(E)) >= 238
    union = set(R) | set(E)
    paired = [x for x in blind if x["id"] in union and scored[x["id"]]["valid"]]
    f4template = i.lines("outputs/079_f4_priorg_adaptation/main_jobs.jsonl")[0]["body"]
    f4jobs = [p.job(x["id"], x["sid"], "F4", "train_F4",
                    p.score_body(f4template, x["claim"], x["reference"])) for x in paired]
    f4jobs.sort(key=lambda x: p.stable("082/train-F4-send/v1:", x["id"]))
    p.write("train_B_scored.jsonl", list(scored.values()))
    p.write("train_labels_accessed.jsonl", [{"id": x["id"], "sid": x["sid"], "GT": x["GT"]} for x in scored.values()])
    p.write("train_views.json", {"status": "R_E_FROZEN_BEFORE_F4_AND_EVALUATION_GT", "R_ids": R, "E_ids": E,
                                 "E_selected_ids": [x["id"] for x in selected], "E_core_n": 238,
                                 "R_planned_n": len(R), "E_planned_n": len(E),
                                 "R_B_valid_n": sum(scored[pid]["valid"] for pid in R),
                                 "E_B_valid_n": sum(scored[pid]["valid"] for pid in E),
                                 "F4_union_B_valid_n": len(paired),
                                 "selected_patient_counts": dict(patient_n),
                                 "selected_GT_counts": dict(Counter(x["GT"] for x in selected)),
                                 "selected_pair_counts": dict(Counter(x["pair"] for x in selected)),
                                 "selected_raw_prior_disagree_n": sum(x["raw_prior_disagree"] for x in selected),
                                 "screen_GT_counts": dict(Counter(x["GT"] for x in scored.values())),
                                 "R_GT_counts": dict(Counter(scored[pid]["GT"] for pid in R)),
                                 "E_GT_counts": dict(Counter(scored[pid]["GT"] for pid in E)),
                                 "B_invalid": invalid,
                                 "train_gt_source_sha256": gt_sha,
                                 "selection_no_eval_GT": True,
                                 "boundary_inclusion_probabilities": "unknown; deterministic score/GT enriched within a 30-per-patient screen",
                                 "weight_definition": "R unit weights for equal-patient target; E patient-normalized 308/(14*n_patient), not an exact population propensity"})
    p.write("train_F4_jobs.jsonl", f4jobs)
    plan = r.read(OUT / "cost_plan.json")
    assert len(f4jobs) <= plan["max_new_logical"]["train_F4"]
    p.write("train_F4_freeze.json", {"stage": "train_F4", "status": "FROZEN_BEFORE_STAGE_API",
                                     "jobs_sha256": p.sha(OUT / "train_F4_jobs.jsonl"),
                                     "blind_freeze_sha256": p.sha(OUT / "blind_freeze.json"),
                                     "cost_plan_sha256": p.sha(OUT / "cost_plan.json"),
                                     "train_views_sha256": p.sha(OUT / "train_views.json"),
                                     "train_B_scored_sha256": p.sha(OUT / "train_B_scored.jsonl")})
    print(json.dumps({"screen": 420, "screen_valid": 420 - len(invalid), "R_valid_B": sum(scored[pid]["valid"] for pid in R),
                      "E_valid_B": sum(scored[pid]["valid"] for pid in E), "F4_jobs": len(f4jobs),
                      "E_GT": dict(Counter(scored[pid]["GT"] for pid in E)),
                      "R_GT": dict(Counter(scored[pid]["GT"] for pid in R))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
