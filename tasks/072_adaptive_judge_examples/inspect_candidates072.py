"""Offline teaching-pool reading list; no evaluation labels or API calls."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ROOT / "outputs/053_thinking_prior_validation/evaluation_cases.jsonl",
    ROOT / "outputs/052_first_tier_validation/evaluation_cases.jsonl",
    ROOT / "outputs/051_thinking_mode_validation/screen_cases.jsonl",
    ROOT / "outputs/044_incremental_evidence_recovery/planning_001/train_cases.jsonl",
    ROOT / "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl",
]
CM = ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
F071 = ROOT / "outputs/071_judge_icl_feasibility/freeze.json"


def main():
    train = set(json.loads(F071.read_text(encoding="utf-8-sig"))["training_patients"])
    annotations = {r["proposition_id"]: r for r in csv.DictReader(CM.open(encoding="utf-8-sig", newline=""))}
    cases = [json.loads(s) for src in SOURCES for s in src.read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    cases = [{"id": x.get("id", x.get("proposition_id")), "sid": str(x.get("sid", x.get("subject_id"))),
              "GT": x.get("GT"), "claim": x.get("claim", x.get("text")),
              "reference": x.get("reference", x.get("base"))} for x in cases]
    cases = list({x["id"]: x for x in reversed(cases) if x["id"] in annotations and x["reference"] and x["GT"]}.values())
    selected = []
    for x in cases:
        if x["sid"] not in train:
            continue
        a = annotations[x["id"]]
        if a["initial_agreement"] != "3" or a["second_round_anomaly"] != "False" or a["time_metadata_conflict"] != "False":
            continue
        if any(a[k] != x["GT"] for k in ("verdict1", "verdict2", "verdict3")):
            continue
        selected.append(x)
    print("counts", dict(Counter(x["GT"] for x in selected)))
    for label in ("Not Supported", "Not Addressed", "Supported"):
        print("\n", label)
        for x in sorted((y for y in selected if y["GT"] == label), key=lambda y: (len(y["reference"]), y["id"])):
            print(x["id"][:8], x["sid"], len(x["reference"]), x["claim"])


if __name__ == "__main__":
    main()
