"""No-API read-only 083 replay checks into a fresh directory."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

import inventory083 as base
import prepare083 as prep
import parse083 as parsed
import features083 as feat
import fit083 as fitting
import run083 as runner
import evaluate083 as ev
from verifact_research.evaluation import evaluate

ROOT, OUT = base.ROOT, base.OUT


def main(target):
    target = Path(target).resolve()
    assert target.is_relative_to((ROOT / "outputs/replays").resolve()) and not target.exists()
    passed = []

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        passed.append(name)

    plan = base.read(OUT / "preflight_and_cost_plan.json")
    check(plan["cap_original_cny"] == 20 and plan["new_main_judge_calls"] == 0, "budget_and_no_judge")
    for name, key in (("extraction_jobs.jsonl", "jobs_sha256"),
                      ("cleaned_inputs.jsonl", "cleaned_inputs_sha256"),
                      ("source_manifest.jsonl", "native_manifest_sha256")):
        check(base.digest((OUT / name).read_bytes()) == plan[key], "plan_hash:" + name)
    quality = base.read(OUT / "native_quality.json")
    check(quality["training_n"] == 459 and quality["evaluation_n"] == 532 and quality["repeat_n"] == 24,
          "fixed_cohort_sizes")
    train_pat = set(quality["training_patients"])
    eval_pat = set(quality["evaluation_patients"])
    demos = set(quality["example_patients"])
    check(len(train_pat) == 14 and len(eval_pat) == 22 and not train_pat & eval_pat and
          not demos & (train_pat | eval_pat), "patient_and_example_isolation")
    source = base.lines("outputs/083_native_rationale_information/source_manifest.jsonl")
    texts = base.lines("outputs/083_native_rationale_information/native_texts.jsonl")
    check(len(source) == len(texts) == 2030, "native_answers_2x1015")
    keys = set()
    for row in source:
        key = (row["phase"], row["arm"], row["id"])
        check(key not in keys, "unique_native:" + str(key))
        keys.add(key)
        receipt = ROOT / row["receipt_source"]
        request = ROOT / row["request_source"]
        check(base.digest(receipt.read_bytes()) == row["receipt_sha256"] and
              base.digest(request.read_bytes()) == row["request_sha256"],
              "native_source_hash:" + row["id"] + row["arm"] + row["phase"])
        r = base.read(receipt)
        check(r["request_sha256"] == row["request_sha256"] and
              r["transport"]["http_status"] == 200, "native_receipt_binding:" + row["id"] + row["arm"])
        body = base.read(request)["job"]["body"]
        check(base.digest(prep.canonical(body).encode()) == row["body_sha256"],
              "native_body_hash:" + row["id"] + row["arm"])
        sent = json.loads(body["messages"][1]["content"])
        check(set(sent) == {"proposition", "reference"} and
              base.digest(sent["proposition"].encode()) == row["claim_sha256"] and
              base.digest(sent["reference"].encode()) == row["reference_sha256"],
              "native_claim_reference:" + row["id"] + row["arm"])
    original = {(x["phase"], x["arm"], x["id"]): x for x in texts}
    cleaned = base.lines("outputs/083_native_rationale_information/cleaned_inputs.jsonl")
    by_clean = {(x["phase"], x["arm"], x["id"]): x for x in cleaned}
    check(len(cleaned) == 2030, "cleaned_count")
    for row in cleaned:
        key = (row["phase"], row["arm"], row["id"])
        check(row["content_sha256"] == original[key]["content_sha256"] and
              row["cleaned_sha256"] == base.digest(row["cleaned_text"].encode()),
              "cleaning_binding:" + row["id"] + row["arm"])
        expected, _ = prep.clean(original[key])
        check(row["cleaned_text"] == expected, "cleaning_replay:" + row["id"] + row["arm"])
    jobs = runner.jobs()
    attempts, answers = runner.state()
    check(len(jobs) == len(answers) == len(attempts) == 1015, "complete_extraction_and_no_success_repeat")
    for job in jobs:
        body = job["body"]
        check(body["model"] == prep.MODEL and body["enable_thinking"] is False and
              set(json.loads(body["messages"][1]["content"])) == {"rationale_text"} and
              job["request_id"] in answers, "extractor_blind_input:" + job["request_id"])
    total = sum(x["original_price_cny"] for x in attempts)
    check(total <= 20 and all(x["http_status"] == 200 for x in attempts), "cost_and_all_HTTP200")
    for attempt in attempts:
        request = base.read(ROOT / attempt["request_source"])
        check(request["used_or_reserved_before_cny"] + request["reservation_cny"] <= 20 + 1e-10,
              "presend_hard_cap:" + attempt["request_id"])
    extracted = base.lines("outputs/083_native_rationale_information/structured_arguments.jsonl")
    check(len(extracted) == 1015, "full_extracted_records")
    for row in extracted:
        key = (row["phase"], "F4", row["id"])
        assert key in by_clean
        text = by_clean[key]["cleaned_text"]
        for arg in row["accepted"]:
            check(arg["quote"] in text and arg["stance"] in parsed.STANCE and
                  arg["basis"] in parsed.BASIS and arg["dimension"] in parsed.DIMENSION,
                  "grounded_argument:" + row["id"])
        coarse, fine = parsed.features(row["accepted"], row["claimed_count"], original[key],
                                       by_clean[key], row["malformed"])
        check(coarse == row["coarse"] and fine == row["fine"], "feature_replay:" + row["id"])
    model = base.read(OUT / "models_frozen.json")
    freeze = base.read(OUT / "evaluation_apply_freeze.json")
    check(model["model_joblib_sha256"] == base.digest((OUT / "models_frozen.joblib").read_bytes()) and
          freeze["models_sha256"] == base.digest((OUT / "models_frozen.json").read_bytes()),
          "model_freeze_binding")
    check(model["feature_code_sha256"] == base.digest((ROOT / "tasks/083_native_rationale_information/features083.py").read_bytes()) and
          model["fit_code_sha256"] == base.digest((ROOT / "tasks/083_native_rationale_information/fit083.py").read_bytes()),
          "model_code_hashes")
    check(model["training_n"] == 459 and len(model["training_patients"]) == 14 and
          model["source_n"] == 1218 and model["evaluation_GT_read"] is False,
          "source_and_train_supervision")
    source_prior = [x for x in base.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")
                    if x["sid"] in train_pat]
    check(len(source_prior) == 1218 and not {x["sid"] for x in source_prior} & eval_pat,
          "source_prior_excludes_evaluation")
    perm = base.read(OUT / "permutation_frozen.json")
    feature_rows = [x for x in feat.build_rows() if x["phase"] in ("old352", "new180")]
    redo, sizes = fitting.permutation(feature_rows)
    check(redo == perm["mapping"] and sizes == perm["group_sizes"] and
          perm["changed"] == 531, "GT_blind_permutation_replay")
    check(freeze["permutation_sha256"] == base.digest((OUT / "permutation_frozen.json").read_bytes()) and
          freeze["structured_arguments_sha256"] == base.digest((OUT / "structured_arguments.jsonl").read_bytes()),
          "evaluation_apply_hashes")
    records = base.lines("outputs/083_native_rationale_information/evaluation_predictions.jsonl")
    check(len(records) == len({x["id"] for x in records}) == 532 and
          [x["id"] for x in records] == freeze["evaluation_ids"], "complete_fixed_evaluation")
    results = base.read(OUT / "evaluation_results.json")
    for name, subset in (("old352", [x for x in records if x["cohort"] == "old352"]),
                         ("new180", [x for x in records if x["cohort"] == "new180"]),
                         ("combined532", records)):
        saved = {x["method"]: x for x in results["cohorts"][name]["metrics"]}
        for method in ("F4_FrozenPriorG", "N", "C", "T", "G", "R", "R_permuted"):
            recalculated = evaluate(ev.cohort(subset), ev.pred(subset, method), profile="none")
            actual_correct = sum(x["predictions"][method] == x["GT"] for x in subset)
            actual_false_s = sum(x["GT"] != "Supported" and x["predictions"][method] == "Supported" for x in subset)
            check(saved[method]["correct"] == actual_correct and
                  abs(saved[method]["MCC"] - recalculated["mcc"]) < 1e-12 and
                  saved[method]["false_S"] == actual_false_s,
                  "metric_replay:" + name + method)
    repeated = base.lines("outputs/083_native_rationale_information/repeat_predictions.jsonl")
    first = {x["id"]: x for x in records}
    check(len(repeated) == 24 and len({x["sid"] for x in repeated}) == 22, "repeat_patient_coverage")
    for row in repeated:
        check(row["body_sha256"] == first[row["id"]]["body_sha256"] and
              row["GT"] == first[row["id"]]["GT"], "repeat_exact_Judge_body:" + row["id"])
    cost = base.read(OUT / "cost_ledger.json")
    check(abs(cost["new_original_price_cny"] - total) < 1e-9 and
          cost["new_attempts"] == len(attempts) and not cost["unknown_or_missing_receipts"],
          "full_charge_reconciliation")
    target.mkdir(parents=True)
    report = {"status": "PASS", "checks": len(passed),
              "scope": "executor self-check, not independent audit; no API or model refit",
              "native_sha256": base.digest((OUT / "source_manifest.jsonl").read_bytes()),
              "models_sha256": base.digest((OUT / "models_frozen.json").read_bytes()),
              "evaluation_sha256": base.digest((OUT / "evaluation_results.json").read_bytes()),
              "new_original_price_cny": total}
    with (target / "verification.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify083.py <fresh outputs/replays directory>")
    main(sys.argv[1])
