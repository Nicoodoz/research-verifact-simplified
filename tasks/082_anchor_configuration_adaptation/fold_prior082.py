"""Rebuild historical PriorG within calibration folds, excluding each held-out patient."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter

import numpy as np

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "tasks/051_thinking_mode_validation"))
sys.path.insert(0, str(ROOT / "tasks/052_first_tier_validation"))
import run051
import common051 as c51
import fit_calibration052 as fit052
from model082 import LABELS, TIE_ORDER


def build():
    cases = i.lines("outputs/051_thinking_mode_validation/screen_cases.jsonl") + i.lines("outputs/051_thinking_mode_validation/confirmation_cases_frozen.jsonl")
    ids = {x["id"] for x in cases}
    _, terminal = run051.state()
    scored = {}
    for item in terminal.values():
        job = item["job"]
        if job.get("condition") == "T-S" and job.get("id") in ids:
            parsed = item["parsed"]
            if parsed["status"] in c51.VALID and parsed.get("scores") is not None:
                scored[job["id"]] = parsed["scores"]
    rows = [dict(id=x["id"], sid=x["sid"], GT=x["GT"], scores=scored[x["id"]])
            for x in cases if x["id"] in scored]
    assert len(rows) == 143
    prior = i.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")
    assert len(prior) == 1378
    fold_patients = json.loads((OUT / "blind_freeze.json").read_text(encoding="utf-8"))["train_patients"]
    folds = {}
    for sid in fold_patients:
        tr = [x for x in rows if x["sid"] != sid]
        ref = [x for x in prior if x["sid"] != sid]
        assert not {sid} & ({x["sid"] for x in tr} | {x["sid"] for x in ref})
        z = fit052.z_from_scores([x["scores"] for x in tr])
        y = np.array([LABELS.index(x["GT"]) for x in tr], dtype=int)
        fitted = fit052.fit(z, y, "G")
        assert fitted["success"]
        refs = Counter(x["GT"] for x in ref)
        cal = Counter(x["GT"] for x in tr)
        assert all(refs[k] > 0 and cal[k] > 0 for k in LABELS)
        folds[sid] = {"G": fitted["theta"][0], "reference_counts": dict(refs),
                      "calibration_counts": dict(cal), "training_ids": [x["id"] for x in tr],
                      "reference_ids": [x["id"] for x in ref], "heldout_patient": sid,
                      "n_calibration": len(tr), "n_reference": len(ref)}
    return folds


def apply(scores, fold):
    ref, cal = fold["reference_counts"], fold["calibration_counts"]
    z = np.log(np.maximum(np.array([float(scores[k]) / 100 for k in LABELS]), 1e-6))
    z[0] += fold["G"]
    z += np.log(np.array([ref[k] / sum(ref.values()) for k in LABELS]) /
                np.array([cal[k] / sum(cal.values()) for k in LABELS]))
    return LABELS[int(TIE_ORDER[np.argmax(z[TIE_ORDER])])]


def main():
    folds = build()
    p.write("fold_prior_baselines.json", {"status": "CALIBRATION_ONLY_LOPO_NO_HELDOUT_REFERENCE_STATISTICS",
                                          "folds": folds,
                                          "sources": {name: p.sha(ROOT / name) for name in (
                                              "outputs/051_thinking_mode_validation/screen_cases.jsonl",
                                              "outputs/051_thinking_mode_validation/confirmation_cases_frozen.jsonl",
                                              "outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")}})
    print(json.dumps({"folds": len(folds), "G_range": [min(v["G"] for v in folds.values()),
                                                     max(v["G"] for v in folds.values())]}))


if __name__ == "__main__":
    main()
