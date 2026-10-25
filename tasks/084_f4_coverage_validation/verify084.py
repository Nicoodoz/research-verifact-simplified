"""Read-only integrity audit of frozen 084 materials, receipts and metrics."""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "tasks/084_f4_coverage_validation"))
import run084
import analyze084 as analysis


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    checks = 0
    freeze = read(OUT / "freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_FIRST_084_API_AND_GT"
    assert freeze["sample_sha256"] == sha(OUT / "sample_blind.jsonl")
    assert freeze["jobs_sha256"] == sha(OUT / "main_jobs.jsonl")
    for rel, digest in freeze["source_sha256"].items():
        assert sha(ROOT / rel) == digest
    grouped = defaultdict(list)
    for job in analysis.lines(OUT / "main_jobs.jsonl"):
        assert job["body_sha256"] == run084.p.digest(job["body"])
        grouped[job["id"]].append(job)
    groups = list(grouped.values())
    assert len(groups) == 180 and all(len(group) == 2 and {j["arm"] for j in group} == {"B", "F4"} for group in groups)
    inventory = read(OUT / "coverage_inventory.json")
    cache_inventory = read(OUT / "cache_receipt_inventory.json")
    assert cache_inventory["new084_sample_historical_exact_B_or_F4"] == 0
    reference_check = read(OUT / "historical_reference_consistency.json")
    assert not reference_check["mismatches"]
    assert sum(reference_check["counts"].values()) == 1064
    for rel, digest in cache_inventory["source_sha256"].items():
        assert sha(ROOT / rel) == digest
    sample = analysis.lines(OUT / "sample_blind.jsonl")
    assert len(groups) == 180 and len(sample) == 180
    checks += 2
    sample_by_id = {x["id"]: x for x in sample}
    assert len(sample_by_id) == 180
    for group in groups:
        for job in group:
            item = sample_by_id[job["id"]]
            body = job["body"]
            payload = json.loads(body["messages"][1]["content"])
            assert payload == {"proposition": item["claim"], "reference": item["reference"]}
            assert hashlib.sha256(body["messages"][0]["content"].encode()).hexdigest() == freeze["template_"+job["arm"]+"_system_sha256"]
            checks += 2
    old = analysis.historical()
    old_ids = {x["id"] for x in old}
    assert len(old_ids) == 532 and not old_ids & {x["id"] for x in sample}
    checks += 2
    train = set(freeze["source_sha256"])
    assert not any("reserved" in rel or "/036_final_validation/" in rel for rel in train)
    checks += 1
    assert not set(freeze["patients"]) & (set(inventory["train_patients"]) | set(inventory["demo_patients"]))
    assert len(freeze["patients"]) == 21 and "85689" not in freeze["patients"]
    checks += 2
    assert sha(ROOT / "outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl") == inventory["source_sha256"]["outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl"]
    checks += 1
    for row in sample:
        assert not row["mechanism_exposure"] and row["fallback_U2"] in analysis.LABELS
        checks += 1
    attempts, successful, counts = run084.state()
    assert len(successful) == 360 and all(counts[rid] <= 3 for rid in counts)
    checks += 2
    for attempt in attempts:
        request = ROOT / attempt["request_source"]
        receipt = ROOT / attempt["receipt_source"] if attempt["receipt_source"] else None
        req = read(request)
        assert req["job"]["request_id"] == attempt["request_id"]
        if receipt:
            rc = read(receipt)
            assert rc["request_sha256"] == sha(request)
            assert abs(run084.charge(req, rc["transport"]) - attempt["original_price_or_unknown_reserved_cny"]) < 1e-12
            if rc["transport"]["http_status"] == 200:
                native = json.loads(rc["transport"]["body_text"])
                assert native["model"] == run084.MODEL
                assert native["usage"]["prompt_tokens"] >= 0 and native["usage"]["completion_tokens"] >= 0
                checks += 2
        checks += 3
    ledger = read(OUT / "cost_ledger.json")
    assert abs(ledger["original_used_or_unknown_reserved_cny"] - sum(x["original_price_or_unknown_reserved_cny"] for x in attempts)) < 1e-9
    assert ledger["original_used_or_unknown_reserved_cny"] <= 20
    checks += 2
    predictions = analysis.lines(OUT / "new_predictions.jsonl")
    assert len(predictions) == 180 and len({x["id"] for x in predictions}) == 180
    checks += 2
    teaching_patients = set(read(ROOT / "outputs/071_judge_icl_feasibility/freeze.json")["training_patients"])
    assert sum(x["teaching_candidate_patient_overlap"] for x in predictions) == 121
    assert all(x["teaching_candidate_patient_overlap"] == (x["sid"] in teaching_patients) for x in predictions)
    checks += 2
    native_manifest = analysis.lines(OUT / "native_manifest.jsonl")
    assert len(native_manifest) == 360 and len({(x["id"], x["arm"]) for x in native_manifest}) == 360
    checks += 2
    for row in native_manifest:
        receipt_path = ROOT / row["receipt_source"]
        assert sha(receipt_path) == row["receipt_sha256"]
        receipt = read(receipt_path)
        native = json.loads(receipt["transport"]["body_text"])
        message = native["choices"][0]["message"]
        try:
            content = json.loads(message.get("content"))
        except (TypeError, ValueError):
            content = {}
        assert row["usage"] == native.get("usage") and row["reasoning_content"] == message.get("reasoning_content")
        assert row["reason"] == content.get("reason") and row["checks"] == content.get("checks")
        checks += 3
    for x in predictions:
        for arm in ("B", "F4"):
            info = x["arms"][arm]
            label = x["methods"][arm]
            if info["valid"]:
                assert label["raw"] == info["raw"]
                assert label["U0"] == analysis.decision(info["scores"], 0)
                assert label["U2"] == analysis.decision(info["scores"], 2)
                assert label["PriorG"] == analysis.priorg(info["scores"])
            else:
                assert all(label[method] == x["fallback_label"] for method in ("raw", "U0", "U2", "PriorG"))
            assert x["original_verifact"] in analysis.LABELS and x["GT"] in analysis.LABELS
            checks += 6
    results = read(OUT / "evaluation_results.json")
    assert results["freeze_sha256"] == sha(OUT / "freeze.json")
    assert results["teaching_candidate_patient_source_sha256"] == sha(ROOT / "outputs/071_judge_icl_feasibility/freeze.json")
    cohorts = {"new084": predictions, "old352": [x for x in old if x["cohort"] == "old352"],
               "old082new180": [x for x in old if x["cohort"] == "new180"],
               "historical532": old, "combined712": old+predictions}
    for name, rows in cohorts.items():
        assert results["cohorts"][name]["n"] == len(rows)
        assert dict(Counter(x["GT"] for x in rows)) == results["cohorts"][name]["GT"]
        for arm in ("B", "F4"):
            recorded = next(x for x in results["metrics"][name] if x["config"] == arm and x["method"] == "PriorG")
            verify = analysis.metric(rows, arm, "PriorG", False)
            for field in ("correct", "false_S", "PA", "MCC", "AC1", "macro_F1"):
                assert abs(recorded[field]-verify[field]) < 1e-10, (name, arm, field)
                checks += 1
        p = results["paired"][name]["PriorG"]
        assert p["net"] == p["rescue"]-p["harm"]
        assert p["net"] == next(x for x in results["metrics"][name] if x["config"] == "F4" and x["method"] == "PriorG")["correct"] - next(x for x in results["metrics"][name] if x["config"] == "B" and x["method"] == "PriorG")["correct"]
        checks += 4
    oof = read(OUT / "083_oof_diagnosis.json")
    assert len(oof["candidates"]) == 18
    for filename, digest in oof["source_sha256"].items():
        assert sha(ROOT / "outputs/083_native_rationale_information" / filename) == digest
        checks += 1
    repeat = read(OUT / "historical_repeat_sensitivity.json")
    assert repeat["n"] == 24 and repeat["patients"] == 22
    assert sha(ROOT / "outputs/082_anchor_configuration_adaptation/repeat_predictions.jsonl") == repeat["source_sha256"]
    checks += 2
    result = {"status": "PASS", "executor_checks": checks, "independent_audit": "not_performed",
              "new_cases": 180, "new_pairs": 180, "attempts": len(attempts),
              "source_hashes_verified": len(freeze["source_sha256"]) + len(oof["source_sha256"]),
              "original_used_or_unknown_cny": ledger["original_used_or_unknown_reserved_cny"]}
    (OUT / "selfcheck.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
