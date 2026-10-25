"""GT-blind C48 coverage inventory across the frozen development archive."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
BROAD = "outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl"
OLD = "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl"
MECHANISM = (
    "outputs/066_oracle_headroom/error_cases.jsonl",
    "outputs/067_conservative_evidence_packing/cases_blind.jsonl",
    "outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl",
    "outputs/068_final_pack_utility_diagnosis/diagnostic_cases.jsonl",
    "outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl",
    "outputs/069_final_pack_controlled_repair/stage1_final_cases.jsonl",
    "outputs/070_fixed_evidence_reasoning_diagnosis/all_cases.jsonl",
    "outputs/081_gt_blind_evidence_selection/sample_blind.jsonl",
)
TEACHING = (
    "outputs/071_judge_icl_feasibility/evaluation_blind.jsonl",
    "outputs/072_adaptive_judge_examples/target_blind.jsonl",
    "outputs/073_clinical_example_matching/target_blind.jsonl",
    "outputs/074_anchor_dynamic_examples/target_blind.jsonl",
    "outputs/075_annotated_static_examples/target_blind.jsonl",
)


def lines(rel):
    return [json.loads(s) for s in (ROOT / rel).open(encoding="utf-8-sig") if s.strip()]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def get_id(x):
    return str(x.get("id") or x.get("proposition_id") or "")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    split = json.loads((ROOT / "outputs/079_f4_priorg_adaptation/freeze.json").read_text(encoding="utf-8-sig"))
    evalp, trainp = set(split["eval_patients"]), set(split["train_patients"])
    demo = {x["sid"] for x in json.loads((ROOT / "outputs/071_judge_icl_feasibility/freeze.json").read_text(encoding="utf-8-sig"))["examples"]}
    assert len(evalp) == 22 and not evalp & (trainp | demo)
    allrows = lines(BROAD)
    assert len(allrows) == len({get_id(x) for x in allrows}) == 3675
    broad = {get_id(x): x for x in allrows if x["subject_id"] in evalp}
    old = {get_id(x): x for x in lines(OLD)}
    assert len(old) == 532 and set(old) <= set(broad)
    for pid, x in old.items():
        assert broad[pid]["subject_id"] == x["sid"]
    exposure = defaultdict(list)
    sources = {BROAD: sha(BROAD), OLD: sha(OLD)}
    for rel in MECHANISM + TEACHING:
        if not (ROOT / rel).exists():
            continue
        sources[rel] = sha(rel)
        for x in lines(rel):
            pid = get_id(x)
            if pid:
                exposure[pid].append(rel.split("/")[1][:3])
    full_pool = set()
    for rel in ("outputs/071_judge_icl_feasibility/examples.jsonl",
                "outputs/072_adaptive_judge_examples/example_pool.jsonl",
                "outputs/073_clinical_example_matching/pool_candidates.jsonl"):
        sources[rel] = sha(rel)
        full_pool |= {get_id(x) for x in lines(rel)}
    teaching_answered = set()
    rel = "outputs/076_existing_results_synthesis/unified_predictions.jsonl"
    sources[rel] = sha(rel)
    for x in lines(rel):
        if x.get("arm") in ("B", "F4"):
            teaching_answered.add(get_id(x))
    # Source books each contain exact C48 text. 032 combines them and checks overlapping text.
    source_books = (
        "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl",
        "outputs/026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl",
        "outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl",
    )
    origins = defaultdict(list)
    for rel in source_books:
        sources[rel] = sha(rel)
        for x in lines(rel):
            pid = get_id(x)
            if pid in broad:
                assert x["reference"] == broad[pid]["reference"]
                origins[pid].append(rel.split("/")[1][:3])
    assert len(origins) == len(broad), (len(origins), len(broad))
    eligible = []
    per_patient = []
    for sid in sorted(evalp):
        patient = [x for x in broad.values() if x["subject_id"] == sid]
        oldrows = [x for x in patient if get_id(x) in old]
        unused = [x for x in patient if get_id(x) not in old]
        mechan = [x for x in unused if set(exposure[get_id(x)]) & {"066", "067", "068", "069", "070", "081"}]
        answered = [x for x in unused if get_id(x) in teaching_answered]
        available = [x for x in unused if x not in mechan and get_id(x) not in teaching_answered]
        for x in available:
            pid = get_id(x)
            eligible.append({"id": pid, "sid": sid, "author": x["author_type"],
                             "claim": x["text"], "reference": x["reference"],
                             "reference_sha256": hashlib.sha256(x["reference"].encode()).hexdigest(),
                             "material_sources": sorted(origins[pid]),
                             "mechanism_exposure": sorted(set(exposure[pid]) & {"066", "067", "068", "069", "070", "081"}),
                             "teaching_exposure": sorted(set(exposure[pid]) & {"071", "072", "073", "074", "075"}),
                             "full_candidate_pool_overlap": pid in full_pool})
        per_patient.append({"sid": sid, "legal_C48": len(patient), "old532": len(oldrows),
                            "incremental_unseen_ID": len(unused), "mechanism_excluded": len(mechan),
                            "prior_B_or_F4_answered": len(answered), "new_paired_eligible": len(available),
                            "mechanism_exposure_eligible": sum(bool(set(exposure[get_id(x)]) & {"066", "067", "068", "069", "070", "081"}) for x in available),
                            "031_source": sum("031" in origins[get_id(x)] for x in patient),
                            "020_source": sum("020" in origins[get_id(x)] for x in patient),
                            "026_source": sum("026" in origins[get_id(x)] for x in patient),
                            "full_candidate_pool_overlap_eligible": sum(get_id(x) in full_pool for x in available),
                            "teaching_exposure_eligible": sum(bool(set(exposure[get_id(x)]) & {"071", "072", "073", "074", "075"}) for x in available)})
    assert len(eligible) == len({x["id"] for x in eligible})
    with (OUT / "coverage_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=per_patient[0].keys())
        w.writeheader()
        w.writerows(per_patient)
    (OUT / "coverage_inventory.json").write_text(json.dumps({"source_sha256": sources,
        "patients": per_patient, "total_eligible": len(eligible), "demo_patients": sorted(demo),
        "train_patients": sorted(trainp), "eval_patients": sorted(evalp),
        "selection_uses_GT": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    with (OUT / "eligible_blind.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for x in eligible:
            f.write(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"broad_eval": len(broad), "old": len(old), "eligible": len(eligible),
                      "patients": sum(x["new_paired_eligible"] > 0 for x in per_patient),
                      "counts": [(x["sid"], x["new_paired_eligible"]) for x in per_patient]}))


if __name__ == "__main__":
    main()
