"""Train-only patient LOPO selection and full frozen low-capacity models."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

import inventory083 as base
import features083 as feat

ROOT, OUT = base.ROOT, base.OUT
CS = (0.03, 0.3, 3.0)


def class_weight_map(sample, source):
    sc = Counter(x["GT"] for x in sample)
    rc = Counter(x["GT"] for x in source)
    assert set(sc) == set(rc) == set(feat.LABELS)
    n, m = len(sample), len(source)
    return {lab: (rc[lab] / m) / (sc[lab] / n) for lab in feat.LABELS}


def weight(rows, mapping):
    return np.asarray([mapping[x["GT"]] for x in rows], dtype=float)


def fit_one(x, y, w, c):
    scaler = StandardScaler()
    transformed = scaler.fit_transform(x)
    model = LogisticRegression(C=c, penalty="l2", solver="lbfgs", max_iter=1000, tol=1e-7)
    model.fit(transformed, y, sample_weight=w)
    assert model.n_iter_[0] < 1000 and list(model.classes_) == [0, 1, 2]
    return scaler, model


def prob(scaler, model, x):
    value = model.predict_proba(scaler.transform(x))
    assert value.shape[1] == 3 and np.all(np.isfinite(value))
    return value


def permutation(rows):
    groups = defaultdict(list)
    for row in rows:
        score = row["scores"]
        if isinstance(score, dict):
            try:
                values = sorted([float(score[z]) for z in feat.LABELS], reverse=True)
                margin = (values[0] - values[1]) / 100
            except (KeyError, TypeError, ValueError):
                margin = 0.0
        else:
            margin = 0.0
        bucket = 0 if margin < .1 else 1 if margin < .5 else 2
        groups[row["phase"], row["raw"] or "missing", bucket].append(row)
    mapping, sizes = {}, {}
    for key, group in groups.items():
        group.sort(key=lambda x: (hashlib.sha256(("083/perm/v1:" + x["id"]).encode()).hexdigest(), x["id"]))
        sizes["|".join(map(str, key))] = len(group)
        for j, row in enumerate(group):
            mapping[row["id"]] = group[(j + 1) % len(group)]["id"]
    assert len(mapping) == len(rows)
    return mapping, sizes


def main():
    rows = feat.build_rows()
    train = [x for x in rows if x["phase"] == "train"]
    evaluation = [x for x in rows if x["phase"] in ("old352", "new180")]
    labels = {x["id"]: x for x in base.lines("outputs/083_native_rationale_information/train_labels.jsonl")}
    assert len(train) == len(labels) == 459
    assert all(x["id"] in labels and x["sid"] == labels[x["id"]]["sid"] for x in train)
    for x in train:
        x["GT"] = labels[x["id"]]["GT"]
    patients = sorted({x["sid"] for x in train})
    assert len(patients) == 14
    ref = base.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")
    source = [x for x in ref if x["sid"] in patients]
    assert len(source) == 1218 and len({x["sid"] for x in source}) == 14
    assert not ({x["sid"] for x in evaluation} & set(patients))
    score = {(arm, c): [0.0, 0.0] for arm in feat.ARMS for c in CS}
    oof = []
    fold_manifest = []
    with threadpool_limits(limits=1):
        for sid in patients:
            training = [x for x in train if x["sid"] != sid]
            held = [x for x in train if x["sid"] == sid]
            source_fold = [x for x in source if x["sid"] != sid]
            weights = class_weight_map(training, source_fold)
            train_y = np.asarray([feat.LABELS.index(x["GT"]) for x in training])
            held_y = np.asarray([feat.LABELS.index(x["GT"]) for x in held])
            train_w, held_w = weight(training, weights), weight(held, weights)
            enc = feat.FeatureMap().fit(training)
            train_blocks, held_blocks = enc.blocks(training), enc.blocks(held)
            fold_manifest.append({"heldout_patient": sid, "training_n": len(training),
                                  "held_n": len(held), "source_n": len(source_fold),
                                  "weights": weights,
                                  "train_ids_sha256": base.digest("\n".join(x["id"] for x in training).encode()),
                                  "source_ids_sha256": base.digest("\n".join(x["id"] for x in source_fold).encode())})
            for arm in feat.ARMS:
                x_train, x_held = feat.select(train_blocks, arm), feat.select(held_blocks, arm)
                for c in CS:
                    scaler, model = fit_one(x_train, train_y, train_w, c)
                    probabilities = prob(scaler, model, x_held)
                    nll = -np.log(np.maximum(probabilities[np.arange(len(held)), held_y], 1e-12))
                    score[arm, c][0] += float(np.dot(held_w, nll))
                    score[arm, c][1] += float(held_w.sum())
                    for row, label, pred in zip(held, held_y, probabilities):
                        oof.append({"id": row["id"], "sid": sid, "GT": row["GT"],
                                    "arm": arm, "C": c, "prob": pred.tolist(),
                                    "prediction": feat.LABELS[int(np.argmax(pred))]})
            print(json.dumps({"fold": sid, "held": len(held), "done": len(fold_manifest)}), flush=True)
        selection = {}
        for arm in feat.ARMS:
            table = [{"C": c, "oof_weighted_nll": score[arm, c][0] / score[arm, c][1]}
                     for c in CS]
            chosen = min(table, key=lambda x: (round(x["oof_weighted_nll"], 12), x["C"]))
            selection[arm] = {"chosen_C": chosen["C"], "candidates": table}
        full_weights = class_weight_map(train, source)
        full_enc = feat.FeatureMap().fit(train)
        train_blocks = full_enc.blocks(train)
        train_y = np.asarray([feat.LABELS.index(x["GT"]) for x in train])
        train_w = weight(train, full_weights)
        models = {}
        for arm in feat.ARMS:
            x = feat.select(train_blocks, arm)
            scaler, model = fit_one(x, train_y, train_w, selection[arm]["chosen_C"])
            models[arm] = {"scaler": scaler, "model": model, "C": selection[arm]["chosen_C"],
                           "dimension": x.shape[1]}
    mapping, sizes = permutation(evaluation)
    bundle = {"feature_map": full_enc, "models": models, "labels": feat.LABELS,
              "full_training_weights": full_weights,
              "training_ids": [x["id"] for x in train], "training_patients": patients}
    joblib.dump(bundle, OUT / "models_frozen.joblib", compress=3)
    base.write("oof_predictions.jsonl", oof)
    base.write("fold_manifest.jsonl", fold_manifest)
    base.write("permutation_frozen.json", {"status": "GT_BLIND_CASE_ALIGNMENT_NEGATIVE_CONTROL",
                                            "mapping": mapping, "group_sizes": sizes,
                                            "changed": sum(k != v for k,v in mapping.items()),
                                            "evaluation_GT_read": False})
    base.write("models_frozen.json", {
        "status": "MODELS_FROZEN_BEFORE_083_EVALUATION_GT",
        "evaluation_GT_read": False, "training_n": 459, "training_patients": patients,
        "evaluation_n": 532, "evaluation_patients": sorted({x["sid"] for x in evaluation}),
        "source_n": len(source), "source_class_count": dict(Counter(x["GT"] for x in source)),
        "training_class_count": dict(Counter(x["GT"] for x in train)),
        "full_weights": full_weights, "selection": selection,
        "arm_dimensions": {arm: x["dimension"] for arm, x in models.items()},
        "model_joblib_sha256": base.digest((OUT / "models_frozen.joblib").read_bytes()),
        "feature_code_sha256": base.digest((ROOT / "tasks/083_native_rationale_information/features083.py").read_bytes()),
        "fit_code_sha256": base.digest(Path(__file__).read_bytes()),
        "source_reference_sha256": base.digest((ROOT / "outputs/080_final_decision_adaptation/reference_prior_rows.jsonl").read_bytes()),
        "structured_arguments_sha256": base.digest((OUT / "structured_arguments.jsonl").read_bytes()),
        "train_labels_sha256": base.digest((OUT / "train_labels.jsonl").read_bytes()),
        "permutation_sha256": base.digest((OUT / "permutation_frozen.json").read_bytes()),
    })
    print(json.dumps({"selection": {k:v["chosen_C"] for k,v in selection.items()},
                      "dimensions": {k:v["dimension"] for k,v in models.items()},
                      "permuted": sum(k != v for k,v in mapping.items())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
