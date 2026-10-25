"""Calibration-patient-only LOPO selection, learning curve, and frozen models."""
from __future__ import annotations

import json
from collections import Counter

import numpy as np
from threadpoolctl import threadpool_limits

import inventory082 as i
import prepare082 as p
import run082 as r
import model082 as m
import fold_prior082 as fp
from verifact_research.evaluation.metrics import classification_metrics

ROOT, OUT = i.ROOT, i.OUT


def evaluate_labels(rows, predicted):
    result = {}
    for arm_index, arm in enumerate(("B", "F4")):
        truth = [x["GT"] for x in rows]
        labels = [m.LABELS[int(z[arm_index])] for z in predicted]
        ev = classification_metrics(truth, labels)
        non_s = sum(x != "Supported" for x in truth)
        false_s = sum(t != "Supported" and y == "Supported" for t, y in zip(truth, labels))
        result[arm] = {"mcc": ev["mcc"], "pa": ev["percent_agreement"],
                       "false_s": false_s, "false_s_rate": false_s / non_s,
                       "n": len(rows)}
    result["mean_mcc"] = float(np.mean([result[a]["mcc"] for a in ("B", "F4")]))
    result["mean_pa"] = float(np.mean([result[a]["pa"] for a in ("B", "F4")]))
    result["mean_false_s_rate"] = float(np.mean([result[a]["false_s_rate"] for a in ("B", "F4")]))
    return result


def lopo(rows, family, regularization):
    result, models = {}, []
    for sid in sorted({x["sid"] for x in rows}):
        train = [x for x in rows if x["sid"] != sid]
        held = [x for x in rows if x["sid"] == sid]
        assert train and held and not {sid} & {x["sid"] for x in train}
        fit = m.fit(train, family, regularization)
        labels = m.predict(held, fit)
        models.append({"heldout_patient": sid, "family": family,
                       "regularization": regularization, "model": fit})
        for x, y in zip(held, labels):
            assert x["id"] not in result
            result[x["id"]] = y.tolist()
    assert len(result) == len(rows)
    return np.array([result[x["id"]] for x in rows], dtype=int), models


def main():
    views = r.read(OUT / "training_effective.json")
    assert views["status"] == "PAIRED_CALIBRATION_ONLY_BEFORE_EVALUATION_GT"
    pair = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/training_pairs.jsonl")}
    R = [pair[x] for x in views["R_ids"]]
    E = [pair[x] for x in views["E_ids"]]
    old = i.lines("outputs/080_final_decision_adaptation/calibration.jsonl")
    assert len(R) == views["R_n"] and len(E) == views["E_n"] and len(old) == 112
    folds = r.read(OUT / "fold_prior_baselines.json")["folds"]
    baseline_predictions = np.array([[m.LABELS.index(fp.apply(x[arm], folds[x["sid"]]))
                                      for arm in ("B", "F4")] for x in R], dtype=int)
    baseline = evaluate_labels(R, baseline_predictions)
    finite = m.finite_difference_check(R[:min(30, len(R))])
    oof_rows, fold_models, options = [], [], []
    with threadpool_limits(limits=1):
        for family in m.FAMILIES:
            for regularization in m.REG_GRID:
                labels, fitted = lopo(R, family, regularization)
                fold_models.extend(fitted)
                metric = evaluate_labels(R, labels)
                feasible = (metric["mean_pa"] >= baseline["mean_pa"] - 0.01 - 1e-12 and
                            metric["mean_false_s_rate"] <= baseline["mean_false_s_rate"] + 0.03 + 1e-12)
                options.append({"family": family, "regularization": regularization,
                                "metrics": metric, "feasible": feasible,
                                "parameter_count": m.num_parameters(family)})
                for x, y in zip(R, labels):
                    oof_rows.append({"id": x["id"], "sid": x["sid"], "GT": x["GT"],
                                     "family": family, "regularization": regularization,
                                     "B": m.LABELS[int(y[0])], "F4": m.LABELS[int(y[1])]})
        chosen = {}
        for family in m.FAMILIES:
            group = [x for x in options if x["family"] == family]
            candidates = [x for x in group if x["feasible"]] or group
            selected = max(candidates, key=lambda x: (round(x["metrics"]["mean_mcc"], 12),
                                                      round(x["metrics"]["mean_pa"], 12),
                                                      x["regularization"]))
            chosen[family] = {"regularization": selected["regularization"],
                              "feasible": selected["feasible"], "OOF": selected["metrics"]}
        family_candidates = [name for name in m.FAMILIES if chosen[name]["feasible"]] or list(m.FAMILIES)
        selected_family = max(family_candidates, key=lambda name: (
            round(chosen[name]["OOF"]["mean_mcc"], 12),
            round(chosen[name]["OOF"]["mean_pa"], 12),
            -m.num_parameters(name), chosen[name]["regularization"]))
        full = {family: m.fit(R, family, chosen[family]["regularization"]) for family in m.FAMILIES}
        equal_size = {"E_independent": m.fit(E, "independent", chosen["independent"]["regularization"]),
                      "old112_independent": m.fit(old, "independent", chosen["independent"]["regularization"])}
        curves = []
        by_patient = sorted({x["sid"] for x in R})
        for seed in (0, 1):
            for per_patient in (7, 14, 22):
                ids = []
                for sid in by_patient:
                    subset = [x for x in R if x["sid"] == sid]
                    if seed == 0:
                        subset.sort(key=lambda x: (x["screen_rank"], x["id"]))
                    else:
                        subset.sort(key=lambda x: (p.stable("082/curve/seed1:", x["id"]), x["id"]))
                    ids.extend(x["id"] for x in subset[:per_patient])
                rows = [pair[x] for x in ids]
                if len(ids) == len(R) and seed == 1:
                    model = full["independent"]
                else:
                    model = m.fit(rows, "independent", chosen["independent"]["regularization"])
                curves.append({"seed": seed, "per_patient": per_patient, "n": len(rows),
                               "patients": len({x["sid"] for x in rows}), "ids": ids, "model": model})
    p.write("oof_predictions.jsonl", oof_rows)
    p.write("fold_models.jsonl", fold_models)
    p.write("training_selection.json", {"status": "SELECTED_ON_CALIBRATION_ONLY", "baseline_fold_priorg": baseline,
                                        "baseline_source": "051 T-S G and 080 reference rows re-fit/recount excluding heldout patient",
                                        "options": options, "chosen_by_family": chosen,
                                        "selected_family": selected_family,
                                        "selection_rule": "feasible PA >= fold-PriorG -0.01 and false-S rate <= fold-PriorG +0.03; max mean B/F4 MCC, PA, simpler family, stronger regularization",
                                        "finite_difference_max_error": finite,
                                        "R_n": len(R), "E_n": len(E),
                                        "R_E_intersection": len(set(views["R_ids"]) & set(views["E_ids"])),
                                        "evaluation_GT_used": False})
    p.write("models_frozen.json", {"status": "FROZEN_BEFORE_082_EVALUATION_GT", "selected_family": selected_family,
                                  "selected_regularizations": {k: v["regularization"] for k, v in chosen.items()},
                                  "full_R_models": full, "equal_size_and_old": equal_size,
                                  "learning_curve_models": curves,
                                  "training_selection_sha256": p.sha(OUT / "training_selection.json"),
                                  "training_effective_sha256": p.sha(OUT / "training_effective.json"),
                                  "fold_prior_baselines_sha256": p.sha(OUT / "fold_prior_baselines.json"),
                                  "model_code_sha256": p.sha(ROOT / "tasks/082_anchor_configuration_adaptation/model082.py"),
                                  "fit_code_sha256": p.sha(ROOT / "tasks/082_anchor_configuration_adaptation/fit082.py"),
                                  "evaluation_GT_used": False})
    print(json.dumps({"R": len(R), "E": len(E), "old": len(old),
                      "selected_family": selected_family, "regularizations": {k: v["regularization"] for k, v in chosen.items()},
                      "feasible": {k: v["feasible"] for k, v in chosen.items()},
                      "baseline_mean_MCC": baseline["mean_mcc"],
                      "selected_mean_MCC": chosen[selected_family]["OOF"]["mean_mcc"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
