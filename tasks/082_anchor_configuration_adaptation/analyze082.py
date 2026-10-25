"""Apply frozen 082 models to old/new patient-out evaluation and compare matched IDs."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict

import numpy as np

import inventory082 as i
import prepare082 as p
import run082 as r
import model082 as m

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
from common053 import VALID, parse_response, decision
from common066 import priorg
from verifact_research.evaluation import evaluate, paired_compare

CORE_METHODS = ("raw", "U0", "U2", "PriorG", "independent_R", "shared_R", "adapted_R", "selected_R")
MORE_METHODS = ("independent_E", "independent_old112", "curve_s0_7", "curve_s0_14", "curve_s1_7", "curve_s1_14")


def doctor_gt(ids):
    out = {}
    source = ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    with source.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["proposition_id"] in ids:
                assert row["proposition_type"] == "claim" and row["invalid"] == "False"
                assert row["human_gt"] in m.LABELS
                out[row["proposition_id"]] = row
    assert set(out) == ids
    return out, p.sha(source)


def published_original():
    out = {}
    for author in ("human", "llm"):
        source = ROOT / f"outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv"
        with source.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                out[row["proposition_id"]] = row["verdict"]
    return out


def apply_models(scores, valid, fallback, models):
    # Each arm's transform depends only on its own score; a placeholder for an invalid
    # opposite arm is ignored, and that arm itself receives the frozen U2 fallback.
    supplied = {arm: scores[arm] if valid[arm] else {k: (100 if k == "Not Addressed" else 0) for k in m.LABELS}
                for arm in ("B", "F4")}
    row = dict(B=supplied["B"], F4=supplied["F4"])
    mapping = {"independent_R": models["full_R_models"]["independent"],
               "shared_R": models["full_R_models"]["shared"],
               "adapted_R": models["full_R_models"]["adapted"],
               "selected_R": models["full_R_models"][models["selected_family"]],
               "independent_E": models["equal_size_and_old"]["E_independent"],
               "independent_old112": models["equal_size_and_old"]["old112_independent"]}
    for curve in models["learning_curve_models"]:
        if curve["per_patient"] in (7, 14):
            mapping[f"curve_s{curve['seed']}_{curve['per_patient']}"] = curve["model"]
    out = {arm: {} for arm in ("B", "F4")}
    for name, model in mapping.items():
        label = m.predict([row], model)[0]
        for j, arm in enumerate(("B", "F4")):
            out[arm][name] = m.LABELS[int(label[j])] if valid[arm] else fallback
    return out


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def pred(rows, config, method):
    return [{"proposition_id": x["id"], "verdict": x["methods"][config][method]} for x in rows]


def metric(rows, config, method, bootstrap=True):
    ev = evaluate(cohort(rows), pred(rows, config, method),
                  profile="research_patient" if bootstrap else "none", missing="error", iterations=1000)
    non_s = sum(x["GT"] != "Supported" for x in rows)
    false_s = sum(x["GT"] != "Supported" and x["methods"][config][method] == "Supported" for x in rows)
    macro = float(np.mean([ev["per_class"][lab]["f1"] or 0 for lab in m.LABELS]))
    return {"config": config, "method": method, "n": len(rows), "patients": len({x["sid"] for x in rows}),
            "correct": sum(x["GT"] == x["methods"][config][method] for x in rows),
            "MCC": ev["mcc"], "PA": ev["percent_agreement"], "AC1": ev["gwet_ac1"],
            "macro_F1": macro, "false_S": false_s, "false_S_rate_nonS": false_s / non_s,
            "nonS_denominator": non_s, "per_class": ev["per_class"],
            "confusion_matrix": ev["confusion_matrix"], "CI95": ev.get("confidence_intervals"),
            "coverage": ev["coverage"]}


def pair(rows, ba, bm, ca, cm):
    ev = paired_compare(cohort(rows), pred(rows, ba, bm), pred(rows, ca, cm), iterations=1000)
    rescue = [x for x in rows if x["methods"][ba][bm] != x["GT"] and x["methods"][ca][cm] == x["GT"]]
    harm = [x for x in rows if x["methods"][ba][bm] == x["GT"] and x["methods"][ca][cm] != x["GT"]]
    patient_net = {sid: sum(int(x in rescue) - int(x in harm) for x in rows if x["sid"] == sid)
                   for sid in sorted({x["sid"] for x in rows})}
    return {"base": f"{ba}:{bm}", "candidate": f"{ca}:{cm}",
            "rescue": len(rescue), "harm": len(harm), "net": len(rescue) - len(harm),
            "rescue_ids": [x["id"] for x in rescue], "harm_ids": [x["id"] for x in harm],
            "patient_wins": sum(v > 0 for v in patient_net.values()),
            "patient_losses": sum(v < 0 for v in patient_net.values()),
            "patient_ties": sum(v == 0 for v in patient_net.values()),
            "patient_net": patient_net,
            "GT_rescue": dict(Counter(x["GT"] for x in rescue)),
            "GT_harm": dict(Counter(x["GT"] for x in harm)),
            "delta_false_S": sum(int(x["GT"] != "Supported" and x["methods"][ca][cm] == "Supported")
                                 - int(x["GT"] != "Supported" and x["methods"][ba][bm] == "Supported") for x in rows),
            "metrics": ev["metrics"]}


def main():
    apply_freeze = r.read(OUT / "evaluation_apply_freeze.json")
    assert apply_freeze["status"] == "ALL_MODELS_AND_OLD_NEW_EVALUATION_INPUTS_FROZEN_BEFORE_GT"
    models = r.read(OUT / "models_frozen.json")
    assert apply_freeze["models_frozen_sha256"] == p.sha(OUT / "models_frozen.json")
    old_blind = i.lines(i.OLD_EVAL)
    new_blind = i.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    ids = {x["id"] for x in old_blind + new_blind}
    assert len(ids) == 532
    gt, gt_sha = doctor_gt(ids)
    original = published_original()
    old_predictions = {x["id"]: x for x in i.lines("outputs/078_component_ablation/f4_extension_001/predictions.jsonl")}
    fallback_new = {x["proposition_id"]: m.LABELS[int(x["u2"])]
                    for x in i.lines("outputs/031_training_expansion_confirmation/inference_001/confirmation_predictions_blind.jsonl")}
    eval_jobs = r.jobs("eval")
    _, new_answers = r.answers("eval")
    assert len(new_answers) == 360
    job_map = {(x["id"], x["arm"]): x for x in eval_jobs}
    records, invalid = [], []
    for queue, cohort_name in ((old_blind, "old352"), (new_blind, "new180")):
        for x in queue:
            pid = x["id"]
            meta = gt[pid]
            assert meta["subject_id"] == x["sid"] and meta["author_type"] == x["author"]
            fallback = (old_predictions[pid]["methods"]["NS_U2"]["label"] if cohort_name == "old352"
                        else fallback_new[pid])
            assert fallback in m.LABELS and original[pid] in m.LABELS
            record = {"id": pid, "sid": x["sid"], "author": x["author"], "GT": meta["human_gt"],
                      "cohort": cohort_name, "original_verifact": original[pid], "fallback_label": fallback,
                      "arms": {}, "methods": {}}
            scores, valid = {}, {}
            for config, historical in (("B", "TS"), ("F4", "F4")):
                if cohort_name == "old352":
                    info = x["arms"][historical]
                    parsed = {"status": info["status"], "scores": info["scores"], "verdict": info["raw"]}
                    okay = bool(info["valid"]) and parsed["scores"] is not None
                    body_hash = info["body_sha256"]
                    provenance = info["receipt_source"]
                    mode = info["mode"]
                    usage = info.get("usage")
                else:
                    j = job_map[pid, config]
                    answer = new_answers[j["request_id"]]
                    parsed = parse_response(answer["transport"], True, True)
                    assert parsed.get("model_returned") in (None, r.MODEL)
                    okay = parsed["status"] in VALID and parsed.get("scores") is not None
                    body_hash = j["body_sha256"]
                    provenance = answer.get("receipt_source") or answer.get("attempt", {}).get("receipt_source")
                    mode = answer["mode"]
                    usage = parsed.get("usage")
                scores[config], valid[config] = parsed.get("scores"), okay
                record["arms"][config] = {"status": parsed["status"], "valid": okay,
                                           "raw": parsed.get("verdict"), "scores": parsed.get("scores"),
                                           "body_sha256": body_hash, "receipt_source": provenance,
                                           "mode": mode, "usage": usage}
                if not okay:
                    invalid.append({"id": pid, "sid": x["sid"], "cohort": cohort_name,
                                    "config": config, "status": parsed["status"],
                                    "fallback": fallback})
                record["methods"][config] = {
                    "raw": parsed["verdict"] if okay else fallback,
                    "U0": decision(parsed["scores"], 0) if okay else fallback,
                    "U2": decision(parsed["scores"], 2) if okay else fallback,
                    "PriorG": priorg(parsed["scores"]) if okay else fallback}
            learned = apply_models(scores, valid, fallback, models)
            for config in ("B", "F4"):
                record["methods"][config].update(learned[config])
            if cohort_name == "old352":
                expected = old_predictions[pid]["methods"]
                for config, historical in (("B", "TS"), ("F4", "F4")):
                    for method, key in (("raw", historical + "_raw"), ("U0", historical + "_U0"),
                                        ("U2", historical + "_U2"), ("PriorG", historical + "_PriorG")):
                        assert record["methods"][config][method] == expected[key]["label"], (pid, config, method)
            records.append(record)
    assert len(records) == 532 and len({x["id"] for x in records}) == 532
    old_rows = [x for x in records if x["cohort"] == "old352"]
    assert sum(x["methods"]["B"]["PriorG"] == x["GT"] for x in old_rows) == 294
    assert sum(x["methods"]["F4"]["PriorG"] == x["GT"] for x in old_rows) == 298
    cohorts = {"old352": old_rows,
               "new180": [x for x in records if x["cohort"] == "new180"],
               "combined532": records}
    metrics, pairs, strata = {}, {}, {}
    comparisons = [("B", "PriorG", "F4", "PriorG"),
                   ("B", "PriorG", "B", "independent_R"),
                   ("F4", "PriorG", "F4", "independent_R"),
                   ("B", "independent_R", "F4", "independent_R"),
                   ("B", "PriorG", "F4", "selected_R"),
                   ("F4", "independent_R", "F4", "shared_R"),
                   ("F4", "independent_R", "F4", "adapted_R"),
                   ("F4", "independent_R", "F4", "selected_R"),
                   ("B", "independent_R", "B", "adapted_R"),
                   ("F4", "independent_R", "F4", "independent_E"),
                   ("F4", "independent_old112", "F4", "independent_R")]
    for cohort_name, rows in cohorts.items():
        metrics[cohort_name] = [metric(rows, config, method, method in CORE_METHODS)
                                for config in ("B", "F4") for method in CORE_METHODS + MORE_METHODS]
        pairs[cohort_name] = [pair(rows, *q) for q in comparisons]
        strata[cohort_name] = {author: {"n": sum(x["author"] == author for x in rows),
                                         "correct": {f"{config}:{method}": sum(x["author"] == author and x["methods"][config][method] == x["GT"] for x in rows)
                                                     for config, method in (("B", "PriorG"), ("F4", "PriorG"),
                                                                            ("B", "independent_R"), ("F4", "independent_R"),
                                                                            ("F4", "adapted_R"), ("F4", "selected_R"))}}
                               for author in ("human", "llm")}
    same_score = {}
    for config in ("B", "F4"):
        groups = defaultdict(list)
        for x in records:
            if x["arms"][config]["valid"]:
                key = tuple(float(x["arms"][config]["scores"][lab]) for lab in m.LABELS)
                groups[key].append(x)
        conflicting = [{"scores": list(key), "n": len(rows),
                        "GT": dict(Counter(x["GT"] for x in rows)),
                        "patients": len({x["sid"] for x in rows})}
                       for key, rows in groups.items() if len({x["GT"] for x in rows}) >= 2]
        same_score[config] = sorted(conflicting, key=lambda x: (-x["n"], x["scores"]))
    original_metrics = {}
    for name, rows in cohorts.items():
        ev = evaluate(cohort(rows),
                      [{"proposition_id": x["id"], "verdict": x["original_verifact"]} for x in rows],
                      profile="research_patient", missing="error", iterations=1000)
        original_metrics[name] = {"n": len(rows), "patients": len({x["sid"] for x in rows}),
                                  "correct": sum(x["original_verifact"] == x["GT"] for x in rows),
                                  "MCC": ev["mcc"], "PA": ev["percent_agreement"], "AC1": ev["gwet_ac1"],
                                  "macro_F1": float(np.mean([ev["per_class"][lab]["f1"] or 0 for lab in m.LABELS])),
                                  "false_S": sum(x["GT"] != "Supported" and x["original_verifact"] == "Supported" for x in rows),
                                  "per_class": ev["per_class"], "confusion_matrix": ev["confusion_matrix"],
                                  "CI95": ev["confidence_intervals"]}
    p.write("evaluation_predictions.jsonl", records)
    p.write("evaluation_results.json", {"status": "EVALUATED_AFTER_FROZEN_MODELS", "cohorts": {k: {"n": len(v), "patients": len({x["sid"] for x in v}),
                                                                      "GT": dict(Counter(x["GT"] for x in v))}
                                                                 for k, v in cohorts.items()},
                                        "metrics": metrics, "paired": pairs, "by_author": strata,
                                        "invalid": invalid, "same_score_different_GT": same_score,
                                        "original_verifact": original_metrics,
                                        "GT_source_sha256": gt_sha,
                                        "evaluation_apply_freeze_sha256": p.sha(OUT / "evaluation_apply_freeze.json"),
                                        "model_sha256": p.sha(OUT / "models_frozen.json")})
    main = [x for x in metrics["combined532"] if x["method"] in ("PriorG", "independent_R", "shared_R", "adapted_R", "selected_R")]
    print(json.dumps({"combined_n": 532, "new_n": 180,
                      "selected_family": models["selected_family"],
                      "main": [(x["config"], x["method"], x["correct"], round(x["MCC"], 4), x["false_S"]) for x in main],
                      "invalid_outputs": len(invalid)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
