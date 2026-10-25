"""Patient/example and claim-history exposure audit without reading evaluation labels."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT
FILES = (
    "outputs/071_judge_icl_feasibility/evaluation_blind.jsonl",
    "outputs/072_adaptive_judge_examples/target_blind.jsonl",
    "outputs/073_clinical_example_matching/target_blind.jsonl",
    "outputs/074_anchor_dynamic_examples/target_blind.jsonl",
    "outputs/075_annotated_static_examples/target_blind.jsonl",
    "outputs/078_component_ablation/primary_blind.jsonl",
    "outputs/078_component_ablation/bridge_blind.jsonl",
    "outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl",
    "outputs/080_final_decision_adaptation/evaluation_blind.jsonl",
    "outputs/081_gt_blind_evidence_selection/sample_blind.jsonl",
)


def main():
    freeze = json.loads((OUT / "blind_freeze.json").read_text(encoding="utf-8"))
    new = i.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    ids = {x["id"] for x in new}
    by_file = {}
    for path in FILES:
        if not (ROOT / path).exists():
            continue
        history = {str(x.get("id") or x.get("proposition_id")) for x in i.lines(path)}
        by_file[path] = sorted(ids & history)
    pool = set(json.loads((ROOT / "outputs/071_judge_icl_feasibility/freeze.json").read_text(encoding="utf-8"))["training_patients"])
    train = set(freeze["train_patients"])
    evaluate = set(freeze["eval_patients"])
    demo = set(freeze["demo_patients"])
    assert train.isdisjoint(evaluate) and not demo & (train | evaluate)
    report = {"actual_example_patients": sorted(demo),
              "full_teaching_candidate_pool_patients": sorted(pool),
              "candidate_pool_overlap_train14": sorted(pool & train),
              "candidate_pool_overlap_eval22": sorted(pool & evaluate),
              "candidate_pool_overlap_new_eval7": sorted(pool & {x["sid"] for x in new}),
              "new_eval_overlap_by_file": by_file,
              "new_eval_any_historical_blind": sorted(set().union(*map(set, by_file.values())) if by_file else set()),
              "new_eval_n": len(new),
              "old352_remains_historically_exposed": True,
              "prior_reference_patients": sorted({x["sid"] for x in i.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")}),
              "new_eval_GT_not_read": True}
    p.write("exposure_audit.json", report)
    print(json.dumps({"train_candidate_pool_overlap": len(pool & train),
                      "eval_candidate_pool_overlap": len(pool & evaluate),
                      "new_eval_any_historical_blind": len(report["new_eval_any_historical_blind"]),
                      "new_eval_overlap_by_file": {k: len(v) for k, v in by_file.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
