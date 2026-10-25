"""Join the frozen calibration views to paired B/F4 scores, without evaluation GT."""
from __future__ import annotations

import json
import sys
from collections import Counter

import inventory082 as i
import prepare082 as p
import run082 as r

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
from common053 import VALID, parse_response


def main():
    views = r.read(OUT / "train_views.json")
    jobs = r.jobs("train_F4")
    _, answers = r.answers("train_F4")
    assert len(answers) == len(jobs), "Do not fit on partial F4 answers"
    bscore = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/train_B_scored.jsonl")}
    by_job = {x["id"]: x for x in jobs}
    blind = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/train_screen_blind.jsonl")}
    pairs, invalid = [], []
    for pid in sorted(set(views["R_ids"]) | set(views["E_ids"])):
        b = bscore[pid]
        if not b["valid"]:
            invalid.append({"id": pid, "sid": b["sid"], "arm": "B", "status": b["status"]})
            continue
        j = by_job[pid]
        ans = answers[j["request_id"]]
        parsed = parse_response(ans["transport"], True, True)
        assert parsed.get("model_returned") in (None, r.MODEL)
        valid = parsed["status"] in VALID and parsed.get("scores") is not None
        if not valid:
            invalid.append({"id": pid, "sid": b["sid"], "arm": "F4", "status": parsed["status"], "errors": parsed.get("errors")})
            continue
        pairs.append({"id": pid, "sid": b["sid"], "author": b["author"], "GT": b["GT"],
                      "B": b["scores"], "F4": parsed["scores"],
                      "B_raw": b["raw"], "F4_raw": parsed["verdict"],
                      "B_body_sha256": b["body_sha256"], "F4_body_sha256": j["body_sha256"],
                      "B_mode": b["mode"], "F4_mode": ans["mode"],
                      "R": pid in views["R_ids"], "E": pid in views["E_ids"],
                      "screen_rank": blind[pid]["rank"],
                      "B_receipt_source": b["source"],
                      "F4_receipt_source": ans.get("receipt_source") or ans.get("attempt", {}).get("receipt_source")})
    R = [x for x in pairs if x["R"]]
    E = [x for x in pairs if x["E"]]
    assert len(pairs) <= 378 and len(R) >= 280 and len(E) >= 280
    before = {"R": len(R), "E": len(E)}
    target = min(len(R), len(E))
    trimmed = {"R": [], "E": []}
    for name, rows in (("R", R), ("E", E)):
        while len(rows) > target:
            counts = Counter(x["sid"] for x in rows)
            sid = sorted((s for s, n in counts.items() if n > 1), key=lambda s: (-counts[s], s))[0]
            victim = max((x for x in rows if x["sid"] == sid),
                         key=lambda x: p.stable("082/effective-trim/v1:", x["id"]))
            rows.remove(victim)
            trimmed[name].append(victim["id"])
    assert len(R) == len(E) == target
    old = i.lines("outputs/080_final_decision_adaptation/calibration.jsonl")
    assert len(old) == 112 and not ({x["id"] for x in old} & {x["id"] for x in pairs})
    assert {x["sid"] for x in R} == {x["sid"] for x in E} == set(r.read(OUT / "blind_freeze.json")["train_patients"])
    p.write("training_pairs.jsonl", pairs)
    p.write("training_effective.json", {"status": "PAIRED_CALIBRATION_ONLY_BEFORE_EVALUATION_GT",
                                      "R_ids": [x["id"] for x in R], "E_ids": [x["id"] for x in E],
                                      "old112_ids": [x["id"] for x in old],
                                      "R_n": len(R), "E_n": len(E), "union_n": len(pairs),
                                      "untrimmed_valid_n": before, "trimmed_ids": trimmed,
                                      "equal_size_rule_sha256": p.sha(OUT / "effective_view_amendment_before_scores.md"),
                                      "R_patients": len({x["sid"] for x in R}),
                                      "E_patients": len({x["sid"] for x in E}),
                                      "R_GT": dict(Counter(x["GT"] for x in R)),
                                      "E_GT": dict(Counter(x["GT"] for x in E)),
                                      "old_GT": dict(Counter(x["GT"] for x in old)),
                                      "invalid": invalid,
                                      "new_views_plus_old_view_unique": len(i.lines("outputs/082_anchor_configuration_adaptation/train_labels_accessed.jsonl")) + 114,
                                      "historical_reference_prior_label_rows": 1378,
                                      "B_screen_scored_unique": 420,
                                      "F4_union_scored_unique": len(jobs),
                                      "same_claim_B_F4_not_new_label": True,
                                      "train_F4_jobs_sha256": p.sha(OUT / "train_F4_jobs.jsonl"),
                                      "training_pairs_sha256": p.sha(OUT / "training_pairs.jsonl")})
    print(json.dumps({"R_effective": len(R), "E_effective": len(E), "union": len(pairs),
                      "old": len(old), "invalid": len(invalid),
                      "R_GT": dict(Counter(x["GT"] for x in R)),
                      "E_GT": dict(Counter(x["GT"] for x in E))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
