"""Freeze 072 teaching pool, patient split and pilot requests before API use."""
from __future__ import annotations

import copy
import csv
import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
SOURCE_FILES = [
    "outputs/053_thinking_prior_validation/evaluation_cases.jsonl",
    "outputs/052_first_tier_validation/evaluation_cases.jsonl",
    "outputs/051_thinking_mode_validation/screen_cases.jsonl",
    "outputs/044_incremental_evidence_recovery/planning_001/train_cases.jsonl",
]
POOL_PREFIXES = [
    "ede1dbb2", "0d286baf", "6446f0a7", "b90878f5",  # exact 071 F4
    "af198ed8", "3415aeb0", "e307868e", "b89074e9",  # S
    "b5c37265", "c92377ee",                    # NS
    "c3d3fd0f", "d4858ebb",                    # NA
]
LABELS = ("Supported", "Not Supported", "Not Addressed")
STATIC_ADDED = ("af198ed8", "b5c37265")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_lines(path, values):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for value in values:
            f.write(canonical(value) + "\n")


def normalize(claim):
    return re.sub(r"[^a-z0-9]+", " ", claim.lower()).strip()


def note_ids(reference):
    return set(re.findall(r"Note ID: (\d+)", reference))


def source_cases():
    found = {}
    for relative in SOURCE_FILES:
        for x in lines(ROOT / relative):
            pid = x.get("id", x.get("proposition_id"))
            if not pid or pid in found:
                continue
            reference = x.get("reference", x.get("base"))
            if reference:
                found[pid] = {
                    "id": pid, "sid": str(x.get("sid", x.get("subject_id"))),
                    "claim": x.get("claim", x.get("text")), "reference": reference,
                    "GT": x.get("GT"), "source_file": relative,
                }
    return found


def select_dynamic(target, pool, matrix, vectorizer, source_matrix):
    scores = (vectorizer.transform([target["claim"]]) @ matrix.T).toarray()[0]
    base_order = {x["proposition_id"]: i for i, x in enumerate(pool)}
    preferred = {
        "Supported": [pool[0]["proposition_id"], pool[2]["proposition_id"]],
        "Not Supported": [pool[1]["proposition_id"]],
        "Not Addressed": [pool[3]["proposition_id"]],
    }
    positions = [("Supported", 0), ("Not Supported", 0), ("Supported", 1), ("Not Addressed", 0)]
    selected, used_sids = [], set()
    for label, ordinal in positions:
        matches = []
        for i, x in enumerate(pool):
            if x["physician_label"] != label or x["sid"] in used_sids:
                continue
            similarity = difflib.SequenceMatcher(None, normalize(x["claim"]), normalize(target["claim"])).ratio()
            if similarity >= 0.85:
                continue
            score = float(scores[i])
            fallback = preferred[label]
            prior = fallback.index(x["proposition_id"]) if x["proposition_id"] in fallback else 100 + base_order[x["proposition_id"]]
            matches.append((score, prior, x))
        assert matches, (target["id"], label)
        if max(m[0] for m in matches) < 0.02:
            matches.sort(key=lambda v: (v[1], -v[0], v[2]["proposition_id"]))
        else:
            matches.sort(key=lambda v: (-v[0], v[1], v[2]["proposition_id"]))
        score, _, chosen = matches[0]
        selected.append({"proposition_id": chosen["proposition_id"], "sid": chosen["sid"],
                         "label": label, "claim_tfidf_cosine": round(score, 8),
                         "near_duplicate_ratio": round(difflib.SequenceMatcher(None, normalize(chosen["claim"]), normalize(target["claim"])).ratio(), 8),
                         "fallback_low_similarity": score < 0.02})
        used_sids.add(chosen["sid"])
    return selected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not any(OUT.iterdir()), "072 output must be empty before first freeze"
    f071 = read(ROOT / "outputs/071_judge_icl_feasibility/freeze.json")
    target_patients = set(f071["evaluation_patients"])
    train_patients = set(f071["training_patients"])
    assert len(target_patients) == 16 and len(train_patients) == 24 and not target_patients & train_patients
    blind = lines(ROOT / "outputs/071_judge_icl_feasibility/evaluation_blind.jsonl")
    gold = lines(ROOT / "outputs/071_judge_icl_feasibility/evaluation_gt.jsonl")
    assert len(blind) == len(gold) == 96 and {x["id"] for x in blind} == {x["id"] for x in gold}
    assert {x["sid"] for x in blind} == target_patients
    patient_order = sorted(target_patients, key=lambda sid: hashlib.sha256(("072/pilot/v1:" + sid).encode()).hexdigest())
    pilot_patients, confirm_patients = set(patient_order[:6]), set(patient_order[6:])
    pilot = [x for x in blind if x["sid"] in pilot_patients]
    confirm = [x for x in blind if x["sid"] in confirm_patients]
    assert len(pilot) == 36 and len(confirm) == 60

    old_examples = lines(ROOT / "outputs/071_judge_icl_feasibility/examples.jsonl")
    all_cases = source_cases()
    annotations = {x["proposition_id"]: x for x in csv.DictReader(
        (ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv").open(encoding="utf-8-sig", newline=""))}
    pool = []
    for ordinal, prefix in enumerate(POOL_PREFIXES, start=1):
        if ordinal <= 4:
            x = dict(old_examples[ordinal - 1])
            x["source_file"] = "outputs/071_judge_icl_feasibility/examples.jsonl"
        else:
            matches = [x for pid, x in all_cases.items() if pid.startswith(prefix)]
            assert len(matches) == 1, prefix
            source = matches[0]
            meta = annotations[source["id"]]
            assert source["sid"] in train_patients
            assert source["GT"] in LABELS
            assert meta["initial_agreement"] == "3" and meta["second_round_anomaly"] == "False" and meta["time_metadata_conflict"] == "False"
            assert [meta[k] for k in ("verdict1", "verdict2", "verdict3")] == [source["GT"]] * 3
            x = {"ordinal": ordinal, "proposition_id": source["id"], "sid": source["sid"],
                 "claim": source["claim"], "reference": source["reference"],
                 "physician_label": source["GT"], "selection": "full_final_reference",
                 "source_file": source["source_file"],
                 "full_final_reference_sha256": hashlib.sha256(source["reference"].encode()).hexdigest(),
                 "selected_reference_sha256": hashlib.sha256(source["reference"].encode()).hexdigest(),
                 "annotation": {k: meta[k] for k in ("initial_agreement", "verdict1", "verdict2", "verdict3", "second_round_anomaly", "time_metadata_conflict")}}
        assert x["sid"] in train_patients
        assert x["physician_label"] in LABELS
        pool.append(x)
    assert Counter(x["physician_label"] for x in pool) == {"Supported": 6, "Not Supported": 3, "Not Addressed": 3}
    target_notes = set().union(*(note_ids(x["reference"]) for x in blind))
    example_notes = set().union(*(note_ids(x["reference"]) for x in pool))
    assert not target_notes & example_notes
    near = max(difflib.SequenceMatcher(None, normalize(x["claim"]), normalize(y["claim"])).ratio() for x in pool for y in blind)
    assert near < 0.85, near

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]+\b")
    matrix = vectorizer.fit_transform([x["claim"] for x in pool])
    dynamic = {x["id"]: select_dynamic(x, pool, matrix, vectorizer, None) for x in blind}
    pool_by_id = {x["proposition_id"]: x for x in pool}
    jobs071 = {(j["id"], j["arm"]): j for j in lines(ROOT / "outputs/071_judge_icl_feasibility/main_jobs.jsonl")}
    original_baseline = {j["id"]: j for j in lines(ROOT / "outputs/053_thinking_prior_validation/main_jobs.jsonl") if j["condition"] == "T-S"}
    assert len(original_baseline) == 240
    pilot_jobs = []
    selections = []
    suffix_prefix = "\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n"
    for x in pilot:
        old_b = jobs071[(x["id"], "B")]["body"]
        old_f = jobs071[(x["id"], "E")]["body"]
        assert old_b == original_baseline[x["id"]]["body"]
        assert json.loads(old_b["messages"][-1]["content"]) == {"proposition": x["claim"], "reference": x["reference"]}
        new_static = copy.deepcopy(old_f)
        new_static["messages"][0]["content"] += "\nTwo additional examples from other patients:\n" + "\n".join(
            canonical({"proposition": pool_by_id[next(p for p in pool_by_id if p.startswith(prefix))]["claim"],
                       "reference": pool_by_id[next(p for p in pool_by_id if p.startswith(prefix))]["reference"],
                       "physician_label": pool_by_id[next(p for p in pool_by_id if p.startswith(prefix))]["physician_label"]})
            for prefix in STATIC_ADDED) + "\n"
        dyn = dynamic[x["id"]]
        new_dynamic = copy.deepcopy(old_b)
        new_dynamic["messages"][0]["content"] += suffix_prefix + "\n".join(canonical({
            "proposition": pool_by_id[item["proposition_id"]]["claim"],
            "reference": pool_by_id[item["proposition_id"]]["reference"],
            "physician_label": item["label"]}) for item in dyn) + "\n"
        selections.append({"id": x["id"], "sid": x["sid"], "selected": dyn})
        for arm, body in (("B", old_b), ("F4", old_f), ("S6", new_static), ("D4", new_dynamic)):
            assert body["model"] == "deepseek-v4-flash-0731" and body["enable_thinking"] is True and body["reasoning_effort"] == "high"
            assert body["messages"][-1]["content"] == old_b["messages"][-1]["content"]
            rid = "072_pilot_" + arm + "_" + hashlib.sha256(x["id"].encode()).hexdigest()[:24]
            pilot_jobs.append({"request_id": rid, "stage": "pilot", "id": x["id"], "sid": x["sid"], "arm": arm,
                               "body": body, "body_sha256": digest(body)})
    pilot_jobs.sort(key=lambda j: hashlib.sha256(("072/pilotjob/v1:" + j["id"] + j["arm"]).encode()).hexdigest())
    write_lines(OUT / "example_pool.jsonl", pool)
    write_lines(OUT / "target_blind.jsonl", blind)
    write_lines(OUT / "target_gt.jsonl", gold)
    write_lines(OUT / "dynamic_selections.jsonl", selections)
    write_lines(OUT / "pilot_jobs.jsonl", pilot_jobs)
    freeze = {"status": "FROZEN_BEFORE_072_API", "cap_cny": 30.0, "model": "deepseek-v4-flash-0731",
              "pilot_patients": patient_order[:6], "confirmation_patients": patient_order[6:],
              "pilot_n": 36, "confirmation_n": 60, "teaching_patients": sorted(train_patients),
              "example_ids": [x["proposition_id"] for x in pool],
              "example_label_counts": dict(Counter(x["physician_label"] for x in pool)),
              "static_added_ids": [next(pid for pid in pool_by_id if pid.startswith(prefix)) for prefix in STATIC_ADDED],
              "dynamic_method": {"vectorizer": "sklearn_TfidfVectorizer_unigram_bigram_english_stopwords_training_claims_only",
                                 "slots": ["Supported", "Not Supported", "Supported", "Not Addressed"],
                                 "min_similarity_for_dynamic": 0.02, "near_duplicate_exclude_ge": 0.85,
                                 "distinct_example_patients": True},
              "near_duplicate_max": near, "overlap_note_ids": 0,
              "pilot_jobs_n": len(pilot_jobs),
              "source_sha256": {p: sha(ROOT / p) for p in [
                  "tasks/072_adaptive_judge_examples/protocol.md",
                  "outputs/071_judge_icl_feasibility/freeze.json",
                  "outputs/071_judge_icl_feasibility/examples.jsonl",
                  "outputs/071_judge_icl_feasibility/evaluation_blind.jsonl",
                  "outputs/071_judge_icl_feasibility/evaluation_gt.jsonl",
                  "outputs/071_judge_icl_feasibility/main_jobs.jsonl",
                  "outputs/053_thinking_prior_validation/freeze.json",
                  "outputs/053_thinking_prior_validation/main_jobs.jsonl",
                  "outputs/002_reproduce_paper_results/run_003/cohort_master.csv", *SOURCE_FILES]},
              "artifact_sha256": {p: sha(OUT / p) for p in ("example_pool.jsonl", "target_blind.jsonl", "target_gt.jsonl", "dynamic_selections.jsonl", "pilot_jobs.jsonl")}}
    write(OUT / "freeze.json", freeze)
    print(json.dumps({"pilot_patients": len(pilot_patients), "pilot_n": len(pilot),
                      "confirmation_patients": len(confirm_patients), "confirmation_n": len(confirm),
                      "examples": len(pool), "pilot_jobs": len(pilot_jobs),
                      "near_duplicate_max": near,
                      "dynamic_fallback_slots": sum(item["fallback_low_similarity"] for row in selections for item in row["selected"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
