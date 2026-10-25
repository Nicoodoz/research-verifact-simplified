"""No-API 082 audit replay into a fresh output directory; never rewrites formal results."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import inventory082 as i
import prepare082 as p
import run082 as r
import model082 as m
import analyze082 as a

ROOT, OUT = i.ROOT, i.OUT


def check(ok, name, passed):
    if not ok:
        raise AssertionError(name)
    passed.append(name)


def main(target):
    destination = Path(target).resolve()
    allowed = (ROOT / "outputs/replays").resolve()
    formal = OUT.resolve()
    check(destination != formal and
          (destination.is_relative_to(allowed) or
           (destination.parent == formal and destination.name.startswith("verification_"))),
          "fresh_replay_location", [])
    check(not destination.exists(), "new_directory_only", [])
    passed = []
    blind = r.read(OUT / "blind_freeze.json")
    check(blind["status"] == "FROZEN_BEFORE_082_API_AND_EVALUATION_GT", "blind_freeze_status", passed)
    for rel, expected in blind["source_sha256"].items():
        check(p.sha(ROOT / rel) == expected, "source:" + rel, passed)
    for name, expected in blind["artifacts_sha256"].items():
        check(p.sha(OUT / name) == expected, "blind_artifact:" + name, passed)
    plan = r.read(OUT / "cost_plan.json")
    check(plan["cap_original_cny"] == 50 and plan["discount_not_used_for_budget"], "original_price_cap", passed)
    sample = i.lines("outputs/082_anchor_configuration_adaptation/train_screen_blind.jsonl")
    evaluation = i.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    repeated = i.lines("outputs/082_anchor_configuration_adaptation/repeat_blind.jsonl")
    check(len(sample) == 420 and len(evaluation) == 180 and len(repeated) == 24,
          "frozen_sample_sizes", passed)
    check(len({x["id"] for x in sample + evaluation}) == 600 and
          not {x["id"] for x in evaluation} & set(i.load()["old_eval"]),
          "unique_old_new_evaluation", passed)
    train_pat, eval_pat, demo = set(blind["train_patients"]), set(blind["eval_patients"]), set(blind["demo_patients"])
    check(len(train_pat) == 14 and len(eval_pat) == 22 and not (train_pat & eval_pat or demo & (train_pat | eval_pat)),
          "patient_isolation", passed)
    check({x["sid"] for x in sample} == train_pat and {x["sid"] for x in evaluation} <= eval_pat,
          "sample_patient_isolation", passed)
    exposed = set(i.load()["exposed"])
    check(not ({x["id"] for x in evaluation} & exposed), "new_evaluation_mechanism_ID_exclusion", passed)
    attempts, new = r.state()
    all_answered = {}
    for stage, count in (("screen_B", 420), ("train_F4", len(r.jobs("train_F4"))),
                         ("eval", 360), ("repeat", 48)):
        jobs = r.jobs(stage)
        _, answers = r.answers(stage)
        check(len(jobs) == len(answers) == count, "complete_stage:" + stage, passed)
        for job in jobs:
            check(job["body_sha256"] == p.digest(job["body"]), "body_hash:" + job["request_id"], passed)
            check(job["body"]["model"] == r.MODEL and job["body"]["enable_thinking"] is True and
                  job["body"]["reasoning_effort"] == "high" and
                  set(json.loads(job["body"]["messages"][1]["content"])) == {"proposition", "reference"},
                  "fixed_judge_and_no_target_GT:" + job["request_id"], passed)
            all_answered[job["request_id"]] = answers[job["request_id"]]
    check(sum(x["original_price_cny"] for x in attempts) <= 50 and len(new) == len({x["job"]["request_id"] for x in new.values()}),
          "charge_and_no_success_resend", passed)
    for x in attempts:
        req = r.read(ROOT / x["request_source"])
        check(req["used_or_reserved_before_cny"] + req["reservation_cny"] <= 50 + 1e-9,
              "pre_send_cap:" + x["attempt_id"], passed)
    gt_access = i.lines("outputs/082_anchor_configuration_adaptation/train_labels_accessed.jsonl")
    check(len(gt_access) == len({x["id"] for x in gt_access}) == 420 and
          {x["sid"] for x in gt_access} == train_pat, "training_label_scope", passed)
    views = r.read(OUT / "training_effective.json")
    check(views["R_n"] == views["E_n"] and views["new_views_plus_old_view_unique"] == 534,
          "equal_size_and_label_count", passed)
    pairs = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/training_pairs.jsonl")}
    check(set(views["R_ids"]) <= set(pairs) and set(views["E_ids"]) <= set(pairs),
          "paired_anchor_scope", passed)
    folds = r.read(OUT / "fold_prior_baselines.json")["folds"]
    for sid, fold in folds.items():
        check(sid not in {pairs[x]["sid"] for x in fold["training_ids"] if x in pairs} and
              fold["heldout_patient"] == sid, "fold_prior_patient_exclusion:" + sid, passed)
    for fold in i.lines("outputs/082_anchor_configuration_adaptation/fold_models.jsonl"):
        sid = fold["heldout_patient"]
        check(sid not in {pairs[x]["sid"] for x in fold["model"]["training_ids"]},
              "LOPO_patient_exclusion:" + sid + fold["family"], passed)
    models = r.read(OUT / "models_frozen.json")
    applied = r.read(OUT / "evaluation_apply_freeze.json")
    check(models["evaluation_GT_used"] is False and applied["models_frozen_sha256"] == p.sha(OUT / "models_frozen.json"),
          "models_precede_evaluation_GT_by_binding", passed)
    check(models["model_code_sha256"] == p.sha(ROOT / "tasks/082_anchor_configuration_adaptation/model082.py") and
          models["fit_code_sha256"] == p.sha(ROOT / "tasks/082_anchor_configuration_adaptation/fit082.py"),
          "frozen_primary_code_fingerprint", passed)
    check(applied["unweighted_models_frozen_sha256"] == p.sha(OUT / "unweighted_models_frozen_v2.json"),
          "frozen_weight_sensitivity_binding", passed)
    for family, model in models["full_R_models"].items():
        check(model["parameter_count"] == m.num_parameters(family) and
              all(math.isfinite(z) for z in model["theta"]) and
              all(math.exp(z) > 0 for z in model["theta"][:3]),
              "identifiable_positive_scales:" + family, passed)
        check(set(model["training_ids"]) == set(views["R_ids"]), "fair_same_R_training:" + family, passed)
    records = i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    check(len(records) == 532 and len({x["id"] for x in records}) == 532 and
          {x["sid"] for x in records} == eval_pat, "complete_patient_out_evaluation", passed)
    results = r.read(OUT / "evaluation_results.json")
    for name, subset in (("old352", [x for x in records if x["cohort"] == "old352"]),
                         ("new180", [x for x in records if x["cohort"] == "new180"]),
                         ("combined532", records)):
        check(len(subset) == results["cohorts"][name]["n"], "cohort_n:" + name, passed)
        lookup = {(x["config"], x["method"]): x for x in results["metrics"][name]}
        for config in ("B", "F4"):
            for method in ("PriorG", "independent_R", "shared_R", "adapted_R", "selected_R"):
                saved = lookup[config, method]
                recomputed = a.metric(subset, config, method, False)
                check(saved["correct"] == recomputed["correct"] and
                      abs(saved["MCC"] - recomputed["MCC"]) < 1e-12 and
                      saved["false_S"] == recomputed["false_S"],
                      "metric_replay:" + name + config + method, passed)
    repeat = i.lines("outputs/082_anchor_configuration_adaptation/repeat_predictions.jsonl")
    original = {x["id"]: x for x in records}
    check(len(repeat) == 24 and len({x["sid"] for x in repeat}) == 22,
          "repeat_patient_coverage", passed)
    for x in repeat:
        for arm in ("B", "F4"):
            check(x["arms"][arm]["body_sha256"] == original[x["id"]]["arms"][arm]["body_sha256"],
                  "repeat_exact_body:" + x["id"] + arm, passed)
    cost = r.read(OUT / "cost_ledger.json")
    check(abs(cost["original_price_total_cny"] - sum(x["original_price_cny"] for x in attempts)) < 1e-9 and
          cost["original_price_total_cny"] <= 50,
          "full_original_price_ledger", passed)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"status": "PASS", "checks": len(passed),
              "scope": "executor self-check, not an independent audit; no API calls",
              "sample_sha256": p.sha(OUT / "blind_freeze.json"),
              "models_sha256": p.sha(OUT / "models_frozen.json"),
              "evaluation_sha256": p.sha(OUT / "evaluation_results.json"),
              "original_price_cny": cost["original_price_total_cny"]}
    with (destination / "verification.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify082.py <new outputs/replays/082_* directory>")
    main(sys.argv[1])
