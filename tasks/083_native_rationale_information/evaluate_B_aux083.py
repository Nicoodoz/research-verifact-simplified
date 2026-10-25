"""Zero-API transfer diagnostic: frozen F4 N/C/T models on native B answers."""
from __future__ import annotations

import json

import joblib
import numpy as np

import inventory083 as base
import features083 as feat
import evaluate083 as ev

OUT = base.OUT


def main():
    freeze = base.read(OUT / "evaluation_apply_freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_083_EVALUATION_GT_JOIN"
    bundle = joblib.load(OUT / "models_frozen.joblib")
    cleaned = {(x["phase"], x["arm"], x["id"]): x for x in base.lines(
        "outputs/083_native_rationale_information/cleaned_inputs.jsonl")}
    native = [x for x in base.lines("outputs/083_native_rationale_information/native_texts.jsonl")
              if x["arm"] == "B" and x["phase"] in ("old352", "new180")]
    assert len(native) == 532
    rows = []
    for x in native:
        c = cleaned[x["phase"], "B", x["id"]]
        rows.append({"id": x["id"], "sid": x["sid"], "claim": x["claim"],
                     "rationale": c["cleaned_text"],
                     "thinking": (x["reasoning_content"] or "")[:2048],
                     "numeric": feat.numeric(x["native_scores"], x["native_verdict"]),
                     "coarse": [0]*13, "fine": [0]*26})
    blocks = bundle["feature_map"].blocks(rows)
    predicted = {}
    for arm in ("N", "C", "T"):
        model = bundle["models"][arm]
        x = feat.select(blocks, arm)
        predicted[arm] = model["model"].predict_proba(model["scaler"].transform(x))
    historical = {x["id"]: x for x in base.lines(
        "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")}
    output = []
    for j, x in enumerate(rows):
        h = historical[x["id"]]
        assert h["sid"] == x["sid"]
        okay = h["arms"]["B"]["valid"]
        labels = {"B_FrozenPriorG": h["methods"]["B"]["PriorG"]}
        for arm in ("N", "C", "T"):
            labels[arm] = feat.LABELS[int(np.argmax(predicted[arm][j]))] if okay else h["fallback_label"]
        output.append({"id": x["id"], "sid": x["sid"], "GT": h["GT"],
                       "cohort": h["cohort"], "author": h["author"],
                       "b_core_valid": okay, "f4_core_valid": False,
                       "probabilities": {}, "predictions": labels})
    groups = {"old352": [x for x in output if x["cohort"] == "old352"],
              "new180": [x for x in output if x["cohort"] == "new180"],
              "combined532": output}
    result = {name: {"n": len(rows),
                     "metrics": [ev.metric(rows, arm) for arm in ("B_FrozenPriorG", "N", "C", "T")],
                     "paired": [ev.pair(rows, "B_FrozenPriorG", arm) for arm in ("N", "C", "T")]}
              for name, rows in groups.items()}
    base.write("B_aux_predictions.jsonl", output)
    base.write("B_aux_results.json", {"status": "ZERO_API_F4_TRAINED_MODEL_TRANSFER_TO_B_DIAGNOSTIC",
                                      "F4_model_sha256": base.digest((OUT / "models_frozen.joblib").read_bytes()),
                                      "new_B_structure_API": 0,
                                      "cohorts": result})
    print(json.dumps({name: [(x["method"], x["correct"], round(x["MCC"], 4), x["false_S"])
                            for x in value["metrics"]] for name, value in result.items()}))


if __name__ == "__main__":
    main()
