"""Freeze isolated examples, exact 053 T-S inputs and three-arm jobs; no API."""
from __future__ import annotations

import copy
import csv
import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
SRC = ROOT / "outputs/053_thinking_prior_validation"
CM = ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
IDS = ["ede1dbb2", "0d286baf", "6446f0a7", "b90878f5"]
TRUE = ["Supported", "Not Supported", "Supported", "Not Addressed"]
SHUFFLED = ["Not Supported", "Supported", "Not Addressed", "Supported"]
LABELS = set(TRUE)


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def filehash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def jsonl(path, values):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for value in values:
            f.write(canonical(value) + "\n")


def block(reference, number):
    parts = re.split(r"(?=^\d+\. Date:)", reference, flags=re.M)
    found = [s.strip() for s in parts if re.match(rf"^{number}\. Date:", s.strip())]
    assert len(found) == 1
    return found[0]


def note_ids(s):
    return set(re.findall(r"Note ID: (\d+)", s))


def normalized(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not any(OUT.iterdir()), "071 output must be empty before freeze"
    cases = lines(SRC / "evaluation_cases.jsonl")
    byid = {x["id"]: x for x in cases}
    patient_order = sorted({x["sid"] for x in cases}, key=lambda sid: hashlib.sha256(("071/eval/v1:" + sid).encode()).hexdigest())
    evpatients, trainpatients = set(patient_order[:16]), set(patient_order[16:])
    evaluable = [x for x in cases if x["sid"] in evpatients]
    assert len(evaluable) == 96 and len(evpatients) == 16 and len(trainpatients) == 24
    assert Counter(x["GT"] for x in evaluable) == {"Supported": 78, "Not Addressed": 13, "Not Supported": 5}
    cm = {r["proposition_id"]: r for r in csv.DictReader(CM.open(encoding="utf-8-sig", newline=""))}
    chosen = [next(x for x in cases if x["id"].startswith(prefix)) for prefix in IDS]
    assert len({x["sid"] for x in chosen}) == 4
    assert all(x["sid"] in trainpatients for x in chosen)
    assert [x["GT"] for x in chosen] == TRUE
    for x in chosen:
        meta = cm[x["id"]]
        assert meta["initial_agreement"] == "3" and meta["second_round_anomaly"] == "False" and meta["time_metadata_conflict"] == "False"
        assert [meta[k] for k in ("verdict1", "verdict2", "verdict3")] == [x["GT"]] * 3
    evidence = [block(chosen[0]["reference"], 6), chosen[1]["reference"], block(chosen[2]["reference"], 7), chosen[3]["reference"]]
    assert re.search(r"Extubated to np\s*s without incident", evidence[0], flags=re.I)
    assert "Leukocytosis" in evidence[1] and "pulmonary infarcts" not in evidence[1].lower()
    assert "dehydration in the setting of diarrhea and acute infection" in evidence[2]
    assert "compartment syndrome" in evidence[3].lower() and not re.search(r"45\s*mm\s*hg", evidence[3], flags=re.I)
    # A concise positive example is valid because its selected EHR block directly states
    # the complete claim; the two non-S examples retain all 053 final evidence.
    examples = []
    for i, (x, ev) in enumerate(zip(chosen, evidence, strict=True)):
        examples.append({"ordinal": i + 1, "proposition_id": x["id"], "sid": x["sid"], "claim": x["claim"],
                         "reference": ev, "physician_label": x["GT"], "full_final_reference_sha256": hashlib.sha256(x["reference"].encode()).hexdigest(),
                         "selected_reference_sha256": hashlib.sha256(ev.encode()).hexdigest(),
                         "selection": "full_final_reference" if i in (1, 3) else "complete_direct_ehr_block",
                         "annotation": {k: cm[x["id"]][k] for k in ("initial_agreement", "verdict1", "verdict2", "verdict3", "second_round_anomaly", "time_metadata_conflict")}})
    trainnotes = set().union(*(note_ids(x["reference"]) for x in chosen))
    evnotes = set().union(*(note_ids(x["reference"]) for x in evaluable))
    assert not trainnotes & evnotes
    for example in examples:
        assert all(normalized(example["claim"]) != normalized(x["claim"]) for x in evaluable)
        assert max(difflib.SequenceMatcher(None, normalized(example["claim"]), normalized(x["claim"])).ratio() for x in evaluable) < 0.8
    jsonl(OUT / "examples.jsonl", examples)
    jsonl(OUT / "evaluation_blind.jsonl", [{"id": x["id"], "sid": x["sid"], "author": x["author"], "claim": x["claim"], "reference": x["reference"]} for x in evaluable])
    jsonl(OUT / "evaluation_gt.jsonl", [{"id": x["id"], "sid": x["sid"], "GT": x["GT"]} for x in evaluable])
    jobs053 = {(x["id"], x["condition"]): x for x in lines(SRC / "main_jobs.jsonl")}
    prefix = "\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n"

    def suffix(labels):
        return prefix + "\n".join(canonical({"proposition": x["claim"], "reference": x["reference"], "physician_label": lab}) for x, lab in zip(examples, labels, strict=True)) + "\n"

    suffix_e, suffix_c = suffix(TRUE), suffix(SHUFFLED)
    assert len(suffix_e) == len(suffix_c)
    alljobs = []
    for x in evaluable:
        original = jobs053[(x["id"], "T-S")]["body"]
        assert json.loads(original["messages"][-1]["content"]) == {"proposition": x["claim"], "reference": x["reference"]}
        assert original["model"] == "deepseek-v4-flash-0731" and original["enable_thinking"] is True
        for arm in ("B", "E", "C"):
            body = copy.deepcopy(original)
            if arm != "B":
                body["messages"][0]["content"] += suffix_e if arm == "E" else suffix_c
            rid = "071_" + arm + "_" + hashlib.sha256(x["id"].encode()).hexdigest()[:24]
            alljobs.append({"request_id": rid, "id": x["id"], "sid": x["sid"], "arm": arm,
                            "body": body, "body_sha256": digest(body), "stage": "main"})
    assert len(alljobs) == 288
    assert all(set(json.loads(j["body"]["messages"][-1]["content"])) == {"proposition", "reference"} for j in alljobs)
    alljobs.sort(key=lambda j: hashlib.sha256(("071/job/v1:" + j["id"] + j["arm"]).encode()).hexdigest())
    jsonl(OUT / "main_jobs.jsonl", alljobs)
    preflight = copy.deepcopy(jobs053[(evaluable[0]["id"], "T-S")]["body"])
    preflight["messages"][-1]["content"] = json.dumps({"proposition": "The patient received aspirin.",
        "reference": "Hospital Admission Start: [CLINICAL_LITERAL_REMOVED] 00:00:00\nElectronic Health Record Context\n1. Date: [CLINICAL_LITERAL_REMOVED], Time: 01:00:00, Note Category: Nursing, Note ID: 1 | Text: Aspirin administered to the patient."},
        ensure_ascii=False, separators=(",", ":"))
    write(OUT / "preflight_body.json", preflight)
    freeze = {"status": "FROZEN_BEFORE_071_API", "patient_order": patient_order,
              "evaluation_patients": patient_order[:16], "training_patients": patient_order[16:],
              "evaluation_n": len(evaluable), "evaluation_gt_counts": dict(Counter(x["GT"] for x in evaluable)),
              "examples": [{k: v for k, v in x.items() if k not in ("reference", "claim")} for x in examples],
              "example_true_labels": TRUE, "control_shuffled_labels": SHUFFLED,
              "near_duplicate_max": max(difflib.SequenceMatcher(None, normalized(a["claim"]), normalized(x["claim"])).ratio() for a in examples for x in evaluable),
              "overlap_note_ids": 0, "suffix_chars": len(suffix_e),
              "preflight_body_sha256": digest(preflight),
              "main_jobs": len(alljobs), "cap_cny": 20.0,
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): filehash(p) for p in
                                (SRC / "evaluation_cases.jsonl", SRC / "main_jobs.jsonl", SRC / "predictions.csv", SRC / "freeze.json", CM, ROOT / "tasks/071_judge_icl_feasibility/protocol.md")}}
    write(OUT / "freeze.json", freeze)
    print(json.dumps({"evaluation_n": len(evaluable), "GT": freeze["evaluation_gt_counts"], "examples": [(x["proposition_id"][:8], x["physician_label"], len(x["reference"])) for x in examples], "suffix_chars": len(suffix_e), "near_duplicate_max": freeze["near_duplicate_max"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
