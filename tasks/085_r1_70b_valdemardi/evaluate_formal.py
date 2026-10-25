"""GT-blind materialization followed by frozen same-ID four-arm evaluation.

Call only after all 360 R1 HTTP200 receipts have been saved. No model calls.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

import formal_runner as runner
import preflight as p

sys.path.insert(0, str(p.ROOT / "tasks/085_r1_70b_model_swap"))
import evaluate085 as ev


def materialize_without_gt():
    jobs, indexed = runner.frozen_jobs()
    completion = p.read(p.PUBLIC / "formal_completion.json")
    if completion["frozen_slots"] != 360 or not completion["all_HTTP200"]:
        raise ValueError("formal completion not established")
    parser_path = p.PUBLIC / "parser_profile.json"
    parser_record = p.read(parser_path)
    if parser_record["model"] != p.MODEL or parser_record["parse_source_sha256"] != p.sha(p.ROOT / "tasks/085_r1_70b_model_swap/parse_r1.py"):
        raise ValueError("parser source identity changed")
    parser = p.ParserProfile.from_json(parser_record)
    predictions = []
    for job in jobs:
        response = runner.success(job)
        if response is None:
            raise ValueError("one of 360 R1 positions lacks HTTP200")
        receipt, folder = response
        raw_path = folder / "response.raw"
        raw = raw_path.read_bytes()
        envelope = json.loads(raw)
        if envelope.get("model") != p.MODEL:
            raise ValueError("R1 model identity mismatch")
        observed = p.inspect(folder, indexed[job["request_id"]]["local_input_tokens"])
        if not observed["local_server_prompt_tokens_match"] or not observed["full_output_budget_fits_20k"]:
            raise ValueError("R1 input altered or context overflow")
        parsed = p.parse(raw, parser)
        predictions.append({"id": job["id"], "sid": job["sid"], "arm": job["arm"],
                            "request_id": job["request_id"], "body_sha256": job["body_sha256"],
                            "raw_response_sha256": p.digest(raw), "private_response_path": str(raw_path.relative_to(p.ROOT)),
                            "parser_profile_sha256": p.sha(parser_path),
                            "valid": parsed["valid"], "invalid_reason": parsed["invalid_reason"],
                            "verdict": parsed["verdict"], "label_scores": parsed["label_scores"],
                            "score_valid": parsed["label_scores"] is not None,
                            "finish_reason": parsed["finish"],
                            "prompt_tokens": observed["prompt_tokens"],
                            "completion_tokens": observed["completion_tokens"],
                            "total_tokens": observed["total_tokens"],
                            "elapsed_seconds": receipt["elapsed_seconds"]})
    if len(predictions) != 360 or len({(x["id"], x["arm"]) for x in predictions}) != 360:
        raise ValueError("R1 prediction coverage mismatch")
    private_path = p.PRIVATE / "r1_predictions.jsonl"
    encoded = b"".join(p.encoded(x) + b"\n" for x in predictions)
    if private_path.exists():
        if private_path.read_bytes() != encoded:
            raise ValueError("existing private predictions differ")
    else:
        p.put(private_path, encoded)
    coverage = {arm: {"HTTP200": 180,
                      "raw_valid": sum(x["arm"] == arm and x["valid"] for x in predictions),
                      "scores_valid": sum(x["arm"] == arm and x["score_valid"] for x in predictions),
                      "finish_reasons": dict(Counter(x["finish_reason"] for x in predictions if x["arm"] == arm)),
                      "completion_tokens": {"min": min(x["completion_tokens"] for x in predictions if x["arm"] == arm),
                                            "median": statistics.median(x["completion_tokens"] for x in predictions if x["arm"] == arm),
                                            "max": max(x["completion_tokens"] for x in predictions if x["arm"] == arm)},
                      "request_seconds_sum": sum(x["elapsed_seconds"] for x in predictions if x["arm"] == arm)}
                for arm in ("B", "F4")}
    summary = {"status": "R1_360_MATERIALIZED_NO_GT", "frozen_n": 180, "rows": len(predictions),
               "model": p.MODEL, "profile_sha256": p.sha(p.PUBLIC / "profile.json"),
               "parser_profile_sha256": p.sha(parser_path),
               "private_predictions_sha256": p.digest(encoded), "coverage": coverage,
               "invalid_raw_ids": [{"id": x["id"], "arm": x["arm"], "reason": x["invalid_reason"]} for x in predictions if not x["valid"]],
               "invalid_score_ids": [{"id": x["id"], "arm": x["arm"]} for x in predictions if x["valid"] and not x["score_valid"]],
               "GT_read": False, "no_imputation": True}
    public_path = p.PUBLIC / "r1_materialization.json"
    if public_path.exists():
        old = p.read(public_path)
        for key in ("private_predictions_sha256", "coverage", "invalid_raw_ids", "invalid_score_ids"):
            if old[key] != summary[key]:
                raise ValueError("existing materialization differs")
    else:
        p.put_json(public_path, summary)
    return predictions, summary


def evaluate_after_complete(predictions):
    frozen = p.rows(p.OLD / "frozen_cohort_manifest.jsonl")
    old = p.rows(p.ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl")
    if len(frozen) != 180 or len(old) != 180 or len({x["sid"] for x in frozen}) != 21:
        raise ValueError("084 frozen cohort changed")
    by_id = {x["id"]: x for x in old}
    if len(by_id) != 180 or set(by_id) != {x["id"] for x in frozen}:
        raise ValueError("084 and 085 IDs differ")
    r1 = {(x["id"], x["arm"]): x for x in predictions}
    main = []
    excluded = []
    secondary = []
    for item in frozen:
        case_id, sid = item["id"], item["sid"]
        v4 = by_id[case_id]
        b, f = r1[case_id, "B"], r1[case_id, "F4"]
        if sid != v4["sid"] or b["sid"] != sid or f["sid"] != sid:
            raise ValueError("patient mismatch")
        arms = v4["arms"]
        valid = b["valid"] and f["valid"] and arms["B"]["valid"] and arms["F4"]["valid"] and v4["original_verifact"] in p.LABELS
        if not valid:
            excluded.append({"id": case_id, "sid": sid, "R1_B_raw_valid": b["valid"],
                             "R1_F4_raw_valid": f["valid"], "V4_B_valid": arms["B"]["valid"],
                             "V4_F4_valid": arms["F4"]["valid"],
                             "Original_valid": v4["original_verifact"] in p.LABELS})
            continue
        labels = {"Original-VeriFact": v4["original_verifact"],
                  "V4-B": arms["B"]["raw"], "V4-F4": arms["F4"]["raw"],
                  "R1-B": b["verdict"], "R1-F4": f["verdict"]}
        if any(label not in p.LABELS for label in labels.values()):
            raise ValueError("valid four-arm label invalid")
        main.append({"id": case_id, "sid": sid, "GT": v4["GT"], "labels": labels})
        if b["score_valid"] and f["score_valid"]:
            score_labels = {}
            for arm, row in (("B", b), ("F4", f)):
                scores = row["label_scores"]
                score_labels[f"R1-{arm}-raw"] = row["verdict"]
                score_labels[f"R1-{arm}-U0"] = ev.decision(scores, 0)
                score_labels[f"R1-{arm}-U2"] = ev.decision(scores, 2)
                score_labels[f"R1-{arm}-FrozenPriorG"] = ev.priorg(scores)
            secondary.append({"id": case_id, "sid": sid, "GT": v4["GT"], "labels": score_labels})
    if not main:
        raise ValueError("no common valid cases")
    main_arms = ("Original-VeriFact", "V4-B", "V4-F4", "R1-B", "R1-F4")
    compare_arms = (("V4-B", "R1-B"), ("R1-B", "R1-F4"),
                    ("V4-F4", "R1-F4"), ("V4-B", "V4-F4"))
    by_patient = defaultdict(list)
    for row in main:
        by_patient[row["sid"]].append(row)
    patient_results = {sid: {"n": len(rows), **{arm: sum(x["GT"] == x["labels"][arm] for x in rows) for arm in main_arms}}
                       for sid, rows in sorted(by_patient.items())}
    result = {"status": "FORMAL_085_VALDEMARDI_COMPLETE", "frozen_n": 180,
              "common_valid_n": len(main), "common_valid_patients": len(by_patient),
              "excluded_from_common": excluded,
              "primary": {arm: ev.summary(main, arm) for arm in main_arms},
              "comparisons": {f"{candidate} minus {base}": ev.compare(main, base, candidate)
                              for base, candidate in compare_arms},
              "F4_cross_model_effect": ev.effect_difference(main),
              "patient_results": patient_results,
              "secondary_score_valid_pair_n": len(secondary),
              "secondary": {arm: ev.summary(secondary, arm) for arm in secondary[0]["labels"]} if secondary else {},
              "secondary_note": "U0/U2/Frozen PriorG only for truly valid R1 scores on both arms; Frozen PriorG was not refitted to R1.",
              "metrics_profile": "research_patient, 1000 patient-cluster bootstrap draws, seeds 0..999",
              "GT_first_read_after_360_R1_HTTP200": True,
              "no_R1_imputation": True, "default_system_unchanged": True,
              "original_084_predictions_sha256": p.sha(p.ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl"),
              "r1_materialization_sha256": p.sha(p.PUBLIC / "r1_materialization.json")}
    private_cases = p.PRIVATE / "formal_case_ledger.jsonl"
    data = b"".join(p.encoded(row) + b"\n" for row in main)
    if not private_cases.exists():
        p.put(private_cases, data)
    elif private_cases.read_bytes() != data:
        raise ValueError("private case ledger differs")
    path = p.PUBLIC / "formal_evaluation.json"
    if path.exists():
        raise FileExistsError("evaluation already exists; do not overwrite")
    p.put_json(path, result)
    return result


def main():
    predictions, materialized = materialize_without_gt()
    print(json.dumps({"materialized": len(predictions), "raw_valid": {arm: materialized["coverage"][arm]["raw_valid"] for arm in ("B", "F4")}}, ensure_ascii=False), flush=True)
    result = evaluate_after_complete(predictions)
    print(json.dumps({"common_valid": result["common_valid_n"],
                      "correct": {arm: data["correct"] for arm, data in result["primary"].items()},
                      "secondary_pair_n": result["secondary_score_valid_pair_n"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
