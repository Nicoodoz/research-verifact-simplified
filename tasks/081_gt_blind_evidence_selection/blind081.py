"""GT-blind source registry for 081. No GT, prediction, or oracle file access."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/081_gt_blind_evidence_selection"
SOURCES = {
    "031": (
        "outputs/031_training_expansion_confirmation/materials_001/inputs.jsonl",
        "outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",
        "outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
    ),
    "020": (
        "outputs/020_lambda2_patient_validation/new10/preparation_002/inputs.jsonl",
        "outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl",
        "outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
    ),
    "009": (
        "outputs/009_retrieval_baselines/confirmation_001/preparation/inputs.jsonl",
        "outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl",
        "outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl",
    ),
}
BASELINES = (
    "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl",
    "outputs/052_first_tier_validation/sample_blind.jsonl",
    "outputs/053_thinking_prior_validation/sample_blind.jsonl",
)
EXPOSED_BLIND = (
    "outputs/052_first_tier_validation/sample_blind.jsonl",
    "outputs/053_thinking_prior_validation/sample_blind.jsonl",
    "outputs/071_judge_icl_feasibility/evaluation_blind.jsonl",
    "outputs/072_adaptive_judge_examples/target_blind.jsonl",
    "outputs/073_clinical_example_matching/target_blind.jsonl",
    "outputs/074_anchor_dynamic_examples/target_blind.jsonl",
    "outputs/075_annotated_static_examples/target_blind.jsonl",
    "outputs/078_component_ablation/primary_blind.jsonl",
    "outputs/078_component_ablation/bridge_blind.jsonl",
)
SPAN_RE = re.compile(
    r"(?m)^\d+\. Date: [^\n]*?Note ID: (?P<note>\d+), Raw characters: "
    r"\[(?P<start>\d+),(?P<end>\d+)\) \| Text: "
)


def lines(relative):
    return [json.loads(s) for s in (ROOT / relative).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def passage_spans(reference):
    return [(m.group("note"), int(m.group("start")), int(m.group("end"))) for m in SPAN_RE.finditer(reference)]


def load():
    target_patients = {str(x["sid"]) for x in lines("outputs/078_component_ablation/primary_blind.jsonl")}
    assert len(target_patients) == 24
    baseline = {}
    for relative in BASELINES:
        for row in lines(relative):
            pid = str(row.get("proposition_id") or row.get("id"))
            ref = row.get("reference")
            if pid and ref and pid not in baseline:
                baseline[pid] = {"reference": ref, "source": relative,
                                 "selected_ids": row.get("selected_ids"),
                                 "claim": row.get("text") or row.get("claim")}
    exposed = set()
    exposure_by_file = {}
    for relative in EXPOSED_BLIND:
        ids = {str(x.get("proposition_id") or x.get("id")) for x in lines(relative)}
        exposed |= ids
        exposure_by_file[relative] = ids
    eligible = {}
    corpora = {}
    for source, (input_path, candidate_path, corpus_path) in SOURCES.items():
        inputs = {str(x.get("proposition_id") or x.get("id")): x for x in lines(input_path)}
        candidates = {str(x.get("proposition_id") or x.get("id")): x for x in lines(candidate_path)}
        corpus = {str(x["passage_id"]): x for x in lines(corpus_path)}
        corpora[source] = corpus
        span_to_id = {}
        for p in corpus.values():
            key = (str(p["note_id"]), int(p["start"]), int(p["end_exclusive"]))
            assert key not in span_to_id or span_to_id[key] == p["passage_id"]
            span_to_id[key] = p["passage_id"]
        for pid, cand in candidates.items():
            if pid in eligible or pid not in inputs or pid not in baseline:
                continue
            item = inputs[pid]
            sid = str(item.get("subject_id") or item.get("sid"))
            if sid not in target_patients:
                continue
            c48 = (cand.get("candidate_ids") or {}).get("C48") or cand.get("C48")
            if not isinstance(c48, list) or not c48 or len(c48) > 48 or len(set(c48)) != len(c48):
                continue
            if any(q not in corpus or str(corpus[q]["subject_id"]) != sid for q in c48):
                continue
            ref = baseline[pid]["reference"]
            spans = passage_spans(ref)
            mapped = [span_to_id.get(q) for q in spans]
            if not spans or any(q is None for q in mapped):
                continue
            if any(q not in c48 for q in mapped):
                continue
            if len(mapped) > 16 or len(set(mapped)) != len(mapped):
                continue
            if sum(len(f"{n}. Date: {corpus[q]['date']}, Time: {corpus[q]['time']}, Note Category: {corpus[q]['category']}, Note ID: {corpus[q]['note_id']}, Raw characters: [{corpus[q]['start']},{corpus[q]['end_exclusive']}) | Text: {corpus[q]['text']}")+1 for n,q in enumerate(mapped,1)) > 8000:
                continue
            notes = Counter(str(corpus[q]["note_id"]) for q in mapped)
            if max(notes.values()) > 2:
                continue
            if len({(corpus[q]["date"],corpus[q]["category"],corpus[q]["text"]) for q in mapped}) != len(mapped):
                continue
            claim = item.get("text") or item.get("claim")
            if not isinstance(claim, str) or claim != baseline[pid]["claim"]:
                continue
            eligible[pid] = {"id": pid, "sid": sid, "author": item.get("author_type") or item.get("author"),
                             "claim": claim, "admission": item["admission"], "source": source,
                             "C48": c48, "baseline_reference": ref, "baseline_ids": mapped,
                             "baseline_source": baseline[pid]["source"]}
    return eligible, corpora, exposed, exposure_by_file, target_patients


def inspect():
    eligible, corpora, exposed, by_file, target_patients = load()
    per_patient = Counter(x["sid"] for x in eligible.values())
    new = Counter(x["sid"] for x in eligible.values() if x["id"] not in exposed)
    print(json.dumps({"strict_eligible": len(eligible), "patients": len(per_patient),
                      "per_patient": sorted((sid, per_patient[sid], new[sid]) for sid in target_patients),
                      "new_total": sum(new.values()),
                      "source_counts": dict(Counter(x["source"] for x in eligible.values())),
                      "exposure_source_counts": {k: len(v) for k, v in by_file.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    inspect()
