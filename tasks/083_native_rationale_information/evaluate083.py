"""Apply frozen 083 models to fixed patient-out cohorts after the GT gate."""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

import inventory083 as base
import features083 as feat
from verifact_research.evaluation import evaluate, paired_compare

ROOT, OUT = base.ROOT, base.OUT
METHODS = ("OriginalVeriFact", "B_FrozenPriorG", "F4_raw", "F4_U0", "F4_U2",
           "F4_FrozenPriorG", "N", "C", "T", "G", "R", "P_aux", "R_permuted")
PAIRS = (("N", "R"), ("C", "R"), ("G", "R"), ("T", "R"),
         ("F4_FrozenPriorG", "R"), ("B_FrozenPriorG", "R"),
         ("C", "T"), ("C", "G"), ("C", "P_aux"),
         ("R_permuted", "R"))


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def pred(rows, method):
    return [{"proposition_id": x["id"], "verdict": x["predictions"][method]} for x in rows]


def probabilities(rows, method):
    valid = [x for x in rows if x["f4_core_valid"] and x["probabilities"].get(method) is not None]
    if not valid:
        return None
    p = np.asarray([x["probabilities"][method] for x in valid], dtype=float)
    y = np.asarray([feat.LABELS.index(x["GT"]) for x in valid], dtype=int)
    assert np.allclose(p.sum(axis=1), 1, atol=1e-6)
    logloss = float(-np.log(np.maximum(p[np.arange(len(y)), y], 1e-12)).mean())
    brier = float(np.mean(np.sum((p - np.eye(3)[y]) ** 2, axis=1)))
    aucs = {}
    for a, b in ((0, 1), (0, 2), (1, 2)):
        keep = np.isin(y, (a, b))
        if len(set(y[keep])) != 2:
            value = None
        else:
            ratio = p[keep, a] / np.maximum(p[keep, a] + p[keep, b], 1e-12)
            value = float(roc_auc_score((y[keep] == a).astype(int), ratio))
        aucs[feat.LABELS[a] + "_vs_" + feat.LABELS[b]] = value
    return {"n": len(valid), "NLL": logloss, "multiclass_Brier": brier, "pair_auc": aucs}


def metric(rows, method):
    outcome = evaluate(cohort(rows), pred(rows, method), profile="research_patient", iterations=1000)
    non_s = sum(x["GT"] != "Supported" for x in rows)
    false_s = sum(x["GT"] != "Supported" and x["predictions"][method] == "Supported" for x in rows)
    return {"method": method, "n": len(rows), "patients": len({x["sid"] for x in rows}),
            "correct": sum(x["GT"] == x["predictions"][method] for x in rows),
            "MCC": outcome["mcc"], "PA": outcome["percent_agreement"],
            "AC1": outcome["gwet_ac1"],
            "Macro_F1": float(np.mean([outcome["per_class"][lab]["f1"] or 0 for lab in feat.LABELS])),
            "false_S": false_s, "nonS_denominator": non_s,
            "false_S_rate": false_s / non_s,
            "per_class": outcome["per_class"],
            "confusion_matrix": outcome["confusion_matrix"],
            "CI95": outcome["confidence_intervals"],
            "probability_diagnostic_core_valid": probabilities(rows, method)}


def pair(rows, a, b):
    outcome = paired_compare(cohort(rows), pred(rows, a), pred(rows, b), iterations=1000)
    rescue = [x for x in rows if x["predictions"][a] != x["GT"] and x["predictions"][b] == x["GT"]]
    harm = [x for x in rows if x["predictions"][a] == x["GT"] and x["predictions"][b] != x["GT"]]
    by_patient = {sid: sum(int(x in rescue) - int(x in harm) for x in rows if x["sid"] == sid)
                  for sid in sorted({x["sid"] for x in rows})}
    false_delta = sum(int(x["GT"] != "Supported" and x["predictions"][b] == "Supported")
                      - int(x["GT"] != "Supported" and x["predictions"][a] == "Supported") for x in rows)
    return {"base": a, "candidate": b, "rescue": len(rescue), "harm": len(harm),
            "net": len(rescue) - len(harm), "rescue_ids": [x["id"] for x in rescue],
            "harm_ids": [x["id"] for x in harm],
            "GT_rescue": dict(Counter(x["GT"] for x in rescue)),
            "GT_harm": dict(Counter(x["GT"] for x in harm)),
            "patient_wins": sum(z > 0 for z in by_patient.values()),
            "patient_losses": sum(z < 0 for z in by_patient.values()),
            "patient_ties": sum(z == 0 for z in by_patient.values()),
            "patient_net": by_patient, "delta_false_S": false_delta,
            "metrics": outcome["metrics"]}


def apply_learned(rows, bundle, perm=None):
    blocks = bundle["feature_map"].blocks(rows)
    output = {name: [] for name in feat.ARMS}
    for arm in feat.ARMS:
        x = feat.select(blocks, arm)
        obj = bundle["models"][arm]
        p = obj["model"].predict_proba(obj["scaler"].transform(x))
        output[arm] = p.tolist()
    if perm is not None:
        lookup = {row["id"]: j for j, row in enumerate(rows)}
        donors = np.asarray([lookup[perm[row["id"]]] for row in rows], dtype=int)
        changed = feat.select(blocks, "R", coarse_override=blocks["coarse"][donors],
                              fine_override=blocks["fine"][donors])
        obj = bundle["models"]["R"]
        output["R_permuted"] = obj["model"].predict_proba(obj["scaler"].transform(changed)).tolist()
    return output


def main():
    freeze = base.read(OUT / "evaluation_apply_freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_083_EVALUATION_GT_JOIN"
    assert freeze["model_joblib_sha256"] == base.digest((OUT / "models_frozen.joblib").read_bytes())
    assert freeze["structured_arguments_sha256"] == base.digest((OUT / "structured_arguments.jsonl").read_bytes())
    perm = base.read(OUT / "permutation_frozen.json")["mapping"]
    bundle = joblib.load(OUT / "models_frozen.joblib")
    all_features = feat.build_rows()
    eval_features = [x for x in all_features if x["phase"] in ("old352", "new180")]
    repeat_features = [x for x in all_features if x["phase"] == "repeat"]
    assert [x["id"] for x in eval_features] == freeze["evaluation_ids"]
    learned = apply_learned(eval_features, bundle, perm)
    learned_repeat = apply_learned(repeat_features, bundle)
    history = {x["id"]: x for x in base.lines(
        "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")}
    assert len(history) == 532
    records = []
    for j, row in enumerate(eval_features):
        h = history[row["id"]]
        assert h["sid"] == row["sid"] and h["arms"]["F4"]["body_sha256"] == row["body_sha256"]
        valid = h["arms"]["F4"]["valid"]
        if valid:
            assert all(abs(float(row["scores"][lab]) - float(h["arms"]["F4"]["scores"][lab])) < 1e-8
                       for lab in feat.LABELS), (row["id"], "native_score_mismatch")
            assert row["raw"] == h["arms"]["F4"]["raw"]
        fallback = h["fallback_label"]
        predictions = {"OriginalVeriFact": h["original_verifact"],
                       "B_FrozenPriorG": h["methods"]["B"]["PriorG"],
                       "F4_raw": h["methods"]["F4"]["raw"],
                       "F4_U0": h["methods"]["F4"]["U0"],
                       "F4_U2": h["methods"]["F4"]["U2"],
                       "F4_FrozenPriorG": h["methods"]["F4"]["PriorG"]}
        prob = {}
        for arm in feat.ARMS + ("R_permuted",):
            p = learned[arm][j]
            predictions[arm if arm != "P" else "P_aux"] = (feat.LABELS[int(np.argmax(p))] if valid else fallback)
            prob[arm if arm != "P" else "P_aux"] = p if valid else None
        records.append({"id": row["id"], "sid": row["sid"], "GT": h["GT"],
                        "author": h["author"], "cohort": h["cohort"],
                        "f4_core_valid": valid, "fallback": fallback,
                        "raw_verdict": row["raw"], "scores": row["scores"],
                        "body_sha256": row["body_sha256"],
                        "structured_accepted": row["structured_accepted"],
                        "structured_malformed": row["structured_malformed"],
                        "perm_donor_id": perm[row["id"]],
                        "predictions": predictions, "probabilities": prob})
    assert len(records) == 532
    repeat_history = {x["id"]: x for x in base.lines(
        "outputs/082_anchor_configuration_adaptation/repeat_predictions.jsonl")}
    repeat = []
    for j, row in enumerate(repeat_features):
        h = repeat_history[row["id"]]
        first = history[row["id"]]
        assert h["sid"] == row["sid"] and h["arms"]["F4"]["body_sha256"] == row["body_sha256"]
        valid = h["arms"]["F4"]["valid"]
        predictions = {"B_FrozenPriorG": h["methods"]["B"]["PriorG"],
                       "F4_raw": h["methods"]["F4"]["raw"],
                       "F4_U0": h["methods"]["F4"]["U0"],
                       "F4_U2": h["methods"]["F4"]["U2"],
                       "F4_FrozenPriorG": h["methods"]["F4"]["PriorG"]}
        for arm in feat.ARMS:
            p = learned_repeat[arm][j]
            predictions[arm if arm != "P" else "P_aux"] = (
                feat.LABELS[int(np.argmax(p))] if valid else first["fallback_label"])
        repeat.append({"id": row["id"], "sid": row["sid"], "GT": first["GT"],
                       "f4_core_valid": valid, "body_sha256": row["body_sha256"],
                       "structured_accepted": row["structured_accepted"],
                       "predictions": predictions})
    base.write("evaluation_predictions.jsonl", records)
    base.write("repeat_predictions.jsonl", repeat)
    groups = {"old352": [x for x in records if x["cohort"] == "old352"],
              "new180": [x for x in records if x["cohort"] == "new180"],
              "combined532": records,
              "common_core_valid": [x for x in records if x["f4_core_valid"]]}
    results = {}
    for name, rows in groups.items():
        results[name] = {"n": len(rows), "patients": len({x["sid"] for x in rows}),
                         "GT": dict(Counter(x["GT"] for x in rows)),
                         "metrics": [metric(rows, method) for method in METHODS],
                         "paired": [pair(rows, a, b) for a, b in PAIRS]}
    author = {}
    for kind in ("human", "llm"):
        rows = [x for x in records if x["author"] == kind]
        author[kind] = {"n": len(rows), "patients": len({x["sid"] for x in rows}),
                        "metrics": [metric(rows, m) for m in ("F4_FrozenPriorG", "N", "C", "T", "G", "R")],
                        "paired": [pair(rows, a, b) for a,b in (("C", "R"), ("G", "R"),
                                                                   ("F4_FrozenPriorG", "R"))]}
    score_groups = defaultdict(list)
    for x in records:
        if x["f4_core_valid"] and isinstance(x["scores"], dict):
            score_groups[tuple(float(x["scores"][z]) for z in feat.LABELS)].append(x)
    conflict = [x for group in score_groups.values() if len({r["GT"] for r in group}) > 1 for x in group]
    same_score = {"groups": sum(len({r["GT"] for r in group}) > 1 for group in score_groups.values()),
                  "n": len(conflict), "patients": len({x["sid"] for x in conflict}),
                  "correct": {m: sum(x["predictions"][m] == x["GT"] for x in conflict)
                              for m in ("N", "C", "T", "G", "R", "F4_FrozenPriorG")},
                  "pairs": [pair(conflict, a, "R") for a in ("N", "G")]} if conflict else {}
    first = {x["id"]: x for x in records}
    repeat_summary = {"n": len(repeat), "patients": len({x["sid"] for x in repeat}),
                      "first_correct": {m: sum(first[x["id"]]["predictions"][m] == x["GT"] for x in repeat)
                                        for m in ("F4_FrozenPriorG", "N", "C", "T", "G", "R")},
                      "repeat_correct": {m: sum(x["predictions"][m] == x["GT"] for x in repeat)
                                         for m in ("F4_FrozenPriorG", "N", "C", "T", "G", "R")},
                      "label_flips": {m: sum(x["predictions"][m] != first[x["id"]]["predictions"][m] for x in repeat)
                                      for m in ("F4_raw", "F4_FrozenPriorG", "N", "C", "T", "G", "R")},
                      "first_false_S": {m: sum(x["GT"] != "Supported" and first[x["id"]]["predictions"][m] == "Supported" for x in repeat)
                                        for m in ("F4_FrozenPriorG", "R")},
                      "repeat_false_S": {m: sum(x["GT"] != "Supported" and x["predictions"][m] == "Supported" for x in repeat)
                                         for m in ("F4_FrozenPriorG", "R")}}
    base.write("evaluation_results.json", {"status": "EVALUATED_AFTER_083_FREEZE",
                                           "cohorts": results, "author": author,
                                           "same_score_conflicts": same_score,
                                           "repeat": repeat_summary,
                                           "invalid_F4": [x["id"] for x in records if not x["f4_core_valid"]],
                                           "raw_equals_U0": sum(x["predictions"]["F4_raw"] == x["predictions"]["F4_U0"] for x in records),
                                           "freeze_sha256": base.digest((OUT / "evaluation_apply_freeze.json").read_bytes()),
                                           "history_082_sha256": base.digest((ROOT / "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl").read_bytes())})
    main = {x["method"]: x for x in results["combined532"]["metrics"]}
    print(json.dumps({"combined_n": len(records), "methods": {m: (main[m]["correct"], round(main[m]["MCC"], 4), main[m]["false_S"])
                                                           for m in ("F4_FrozenPriorG", "N", "C", "T", "G", "R", "P_aux")},
                      "repeat": repeat_summary["first_correct"], "invalid_F4": 532-len(groups["common_core_valid"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
