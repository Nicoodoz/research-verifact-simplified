"""Secondary same-180 comparison to the current frozen V4-B+PriorG system.

V4's three core-invalid rows retain the 084 frozen fallback. R1 scores are
required to be genuinely valid; no R1 fallback or refitting is introduced.
"""
from __future__ import annotations

import json
import sys

import preflight as p

sys.path.insert(0, str(p.ROOT / "tasks/085_r1_70b_model_swap"))
import evaluate085 as ev


def main():
    if not p.read(p.PUBLIC / "formal_completion.json")["all_HTTP200"]:
        raise ValueError("formal R1 run incomplete")
    if not (p.PUBLIC / "formal_evaluation.json").exists():
        raise ValueError("raw primary evaluation required first")
    preds = {(x["id"], x["arm"]): x for x in p.rows(p.PRIVATE / "r1_predictions.jsonl")}
    frozen = p.rows(p.OLD / "frozen_cohort_manifest.jsonl")
    v4 = {x["id"]: x for x in p.rows(p.ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl")}
    if len(preds) != 360 or len(frozen) != 180 or len(v4) != 180:
        raise ValueError("same-ID cohort incomplete")
    rows = []
    for item in frozen:
        case_id, sid = item["id"], item["sid"]
        old, b, f = v4[case_id], preds[case_id, "B"], preds[case_id, "F4"]
        if old["sid"] != sid or b["sid"] != sid or f["sid"] != sid:
            raise ValueError("patient mismatch")
        if not (b["valid"] and f["valid"] and b["score_valid"] and f["score_valid"]):
            raise ValueError("R1 score-invalid row requires separate coverage policy, not fallback")
        labels = {"Original-VeriFact": old["original_verifact"],
                  "V4-B-PriorG": old["methods"]["B"]["PriorG"],
                  "V4-F4-PriorG": old["methods"]["F4"]["PriorG"],
                  "R1-B-raw": b["verdict"], "R1-F4-raw": f["verdict"],
                  "R1-B-U0": ev.decision(b["label_scores"], 0),
                  "R1-F4-U0": ev.decision(f["label_scores"], 0),
                  "R1-B-U2": ev.decision(b["label_scores"], 2),
                  "R1-F4-U2": ev.decision(f["label_scores"], 2),
                  "R1-B-PriorG": ev.priorg(b["label_scores"]),
                  "R1-F4-PriorG": ev.priorg(f["label_scores"])}
        if any(label not in p.LABELS for label in labels.values()):
            raise ValueError("invalid final label")
        rows.append({"id": case_id, "sid": sid, "GT": old["GT"], "labels": labels})
    comparisons = (("V4-B-PriorG", "R1-B-PriorG"),
                   ("V4-B-PriorG", "R1-F4-PriorG"),
                   ("V4-F4-PriorG", "R1-F4-PriorG"),
                   ("R1-B-PriorG", "R1-F4-PriorG"),
                   ("V4-B-PriorG", "V4-F4-PriorG"))
    result = {"status": "SECONDARY_FROZEN_FINAL_SYSTEM_COMPARISON", "n": 180,
              "patients": 21, "r1_score_valid_n": 180,
              "v4_core_invalid_fallback_n": {
                  arm: sum(not old["arms"][arm]["valid"] for old in v4.values()) for arm in ("B", "F4")},
              "method": "V4 original 084 PriorG/fallback; R1 genuine scores with unchanged PriorG, no R1 fallback or fitting",
              "summary": {arm: ev.summary(rows, arm) for arm in rows[0]["labels"]},
              "comparisons": {f"{candidate} minus {base}": ev.compare(rows, base, candidate)
                              for base, candidate in comparisons},
              "GT_read_after_360": True,
              "source_084_predictions_sha256": p.sha(p.ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl"),
              "source_r1_predictions_sha256": p.sha(p.PRIVATE / "r1_predictions.jsonl")}
    private_path = p.PRIVATE / "final_system_case_ledger.jsonl"
    data = b"".join(p.encoded(row) + b"\n" for row in rows)
    if not private_path.exists():
        p.put(private_path, data)
    elif private_path.read_bytes() != data:
        raise ValueError("private final-system ledger differs")
    path = p.PUBLIC / "final_system_comparison.json"
    if path.exists():
        raise FileExistsError("final-system comparison already saved")
    p.put_json(path, result)
    print(json.dumps({"n": 180, "correct": {k: v["correct"] for k, v in result["summary"].items()},
                      "false_S": {k: v["false_S"] for k, v in result["summary"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
