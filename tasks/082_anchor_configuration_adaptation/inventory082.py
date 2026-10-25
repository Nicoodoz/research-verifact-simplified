"""GT-free eligible inventory for 082; no evaluation predictions or labels are read."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/082_anchor_configuration_adaptation"
MATERIAL = "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl"
SPLIT = "outputs/079_f4_priorg_adaptation/freeze.json"
OLD_EVAL = "outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl"
OLD_TRAIN = "outputs/079_f4_priorg_adaptation/calibration_cases.jsonl"
EXPOSURE = (
    "outputs/066_oracle_headroom/error_cases.jsonl",
    "outputs/067_conservative_evidence_packing/cases_blind.jsonl",
    "outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl",
    "outputs/068_final_pack_utility_diagnosis/diagnostic_cases.jsonl",
    "outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl",
    "outputs/069_final_pack_controlled_repair/stage1_final_cases.jsonl",
    "outputs/070_fixed_evidence_reasoning_diagnosis/case_ledger.jsonl",
    "outputs/081_gt_blind_evidence_selection/sample_blind.jsonl",
)


def lines(path):
    return [json.loads(s) for s in (ROOT / path).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def load():
    split = json.loads((ROOT / SPLIT).read_text(encoding="utf-8-sig"))
    train, evaluate = set(split["train_patients"]), set(split["eval_patients"])
    demo = {x["sid"] for x in json.loads((ROOT / "outputs/071_judge_icl_feasibility/freeze.json").read_text(encoding="utf-8-sig"))["examples"]}
    assert train.isdisjoint(evaluate) and (train | evaluate).isdisjoint(demo)
    materials = {x["proposition_id"]: x for x in lines(MATERIAL)}
    old_eval = {x["id"] for x in lines(OLD_EVAL)}
    old_train = {x["id"] for x in lines(OLD_TRAIN)}
    exposed = defaultdict(list)
    for path in EXPOSURE:
        if not (ROOT / path).exists():
            continue
        for x in lines(path):
            pid = x.get("proposition_id") or x.get("id")
            if pid:
                exposed[str(pid)].append(path)
    train_pool = [x for x in materials.values() if x["subject_id"] in train and x["proposition_id"] not in old_train]
    eval_pool = [x for x in materials.values() if x["subject_id"] in evaluate and x["proposition_id"] not in old_eval and x["proposition_id"] not in exposed]
    return dict(train_patients=train, eval_patients=evaluate, demo_patients=demo, materials=materials,
                old_train=old_train, old_eval=old_eval, exposed=exposed, train_pool=train_pool, eval_pool=eval_pool)


def main():
    q = load()
    print(json.dumps({"materials": len(q["materials"]), "old_train": len(q["old_train"]),
                      "old_eval": len(q["old_eval"]), "train_pool": len(q["train_pool"]),
                      "eval_pool": len(q["eval_pool"]),
                      "train_counts": dict(Counter(x["subject_id"] for x in q["train_pool"])),
                      "eval_counts": dict(Counter(x["subject_id"] for x in q["eval_pool"])),
                      "demo_patients": sorted(q["demo_patients"]),
                      "mechanism_excluded_in_eval": len({pid for pid in q["exposed"] if pid in q["materials"]})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
