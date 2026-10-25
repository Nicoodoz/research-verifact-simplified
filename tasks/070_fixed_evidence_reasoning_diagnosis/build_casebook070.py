"""Offline full-reference/output casebook and exact-request repeat inventory."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/070_fixed_evidence_reasoning_diagnosis"


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def native_parsed(transport):
    if transport.get("http_status") != 200:
        return None
    native = json.loads(transport["body_text"])
    message = native["choices"][0]["message"]
    try:
        obj = json.loads(message.get("content") or "")
    except (json.JSONDecodeError, TypeError):
        obj = None
    return {"model": native.get("model"), "output": obj, "content": message.get("content"),
            "reasoning_present": bool(message.get("reasoning_content")),
            "reasoning_chars": len(message.get("reasoning_content") or "")}


def receipt_index(base):
    ans = {}
    for path in base.glob("*/request.json"):
        receipt = path.parent / "receipt.json"
        if not receipt.exists():
            continue
        request = json.loads(path.read_text(encoding="utf-8-sig"))
        record = json.loads(receipt.read_text(encoding="utf-8-sig"))
        assert record["request_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        rid = request["job"]["request_id"]
        assert rid not in ans
        ans[rid] = {"request_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "receipt_path": str(receipt.relative_to(ROOT)).replace("\\", "/"),
                    "body_hash": digest(request["job"]["body"]), "job": request["job"],
                    "native": native_parsed(record["transport"])}
    return ans


def main():
    p053 = ROOT / "outputs/053_thinking_prior_validation"
    p055 = ROOT / "outputs/055_zero_label_policy_adaptation"
    p069 = ROOT / "outputs/069_final_pack_controlled_repair"
    all_rows = lines(OUT / "all_cases.jsonl")
    fixes = [x for x in all_rows if x["reasoning_oracle_fix"]]
    cases = {x["id"]: x for x in lines(p053 / "evaluation_cases.jsonl")}
    main_jobs = {(x["id"], x["condition"]): x for x in lines(p053 / "main_jobs.jsonl")}
    qnew = {x["id"]: x for x in lines(p055 / "qwen_full_jobs.jsonl")}
    reuse = {x["id"]: x for x in lines(p055 / "qwen_full_reuse.jsonl")}
    oldq = {x["request_id"]: x for x in lines(p053 / "qwen_jobs.jsonl")}
    receipts = {}
    for base in (p053 / "attempts", p055 / "qwen_full_attempts", p069 / "attempts"):
        receipts.update(receipt_index(base))
    book = []
    for row in fixes:
        pid = row["id"]
        qjob = qnew.get(pid) or oldq[reuse[pid]["existing_request_id"]]
        jobs = {"NS_U0": main_jobs[(pid, "N-S")], "TS_raw": main_jobs[(pid, "T-S")], "Qwen_U0": qjob}
        outputs = {}
        for name, job in jobs.items():
            ri = receipts[job["request_id"]]
            assert ri["body_hash"] == digest(job["body"])
            assert ri["native"] and ri["native"]["output"]
            output = ri["native"]["output"]
            assert output.get("verdict") in ("Supported", "Not Supported", "Not Addressed")
            outputs[name] = {"request_id": job["request_id"], "body_hash": ri["body_hash"],
                             "request_path": ri["request_path"], "receipt_path": ri["receipt_path"],
                             "model": ri["native"]["model"], "output": output,
                             "reasoning_present": ri["native"]["reasoning_present"],
                             "reasoning_chars": ri["native"]["reasoning_chars"]}
        case = cases[pid]
        assert all(json.loads(j["body"]["messages"][-1]["content"]) ==
                   {"proposition": case["claim"], "reference": case["reference"]} for j in jobs.values())
        book.append({"id": pid, "sid": row["sid"], "author": row["author"], "GT": row["GT"],
                     "claim": case["claim"], "reference": case["reference"],
                     "reference_sha256": row["reference_sha256"],
                     "labels": {k: row[k] for k in ("PriorG", "NS_U0", "TS_raw", "Qwen_U0", "Qwen_raw")},
                     "scores": {k: row[k] for k in ("TS_scores", "NS_scores", "Qwen_scores")},
                     "correct_candidates": row["correct_candidates"], "outputs": outputs})
    with (OUT / "casebook_full.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in book:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    assert len(book) == 14
    # Scan only historical requests, never make new calls. Exact body includes system prompt,
    # user payload, model and generation settings; a copied receipt is not an independent repeat.
    target = defaultdict(list)
    for row in book:
        for name, output in row["outputs"].items():
            target[output["body_hash"]].append((row["id"], name))
    inventory = defaultdict(list)
    prior_bases = [ROOT / f"outputs/{name}/attempts" for name in (
        "050_repeated_score_aggregation", "051_thinking_mode_validation",
        "052_first_tier_validation", "053_thinking_prior_validation",
        "068_final_pack_utility_diagnosis", "069_final_pack_controlled_repair")]
    prior_bases.append(p055 / "qwen_full_attempts")
    for base in prior_bases:
        for rid, rec in receipt_index(base).items():
            if rec["body_hash"] in target:
                for pid, name in target[rec["body_hash"]]:
                    inventory[(pid, name)].append({"request_id": rid, "request_path": rec["request_path"],
                                                    "receipt_path": rec["receipt_path"],
                                                    "verdict": rec["native"]["output"].get("verdict") if rec["native"] and rec["native"]["output"] else None})
    repeat_rows = []
    for row in book:
        for name in ("NS_U0", "TS_raw", "Qwen_U0"):
            entries = inventory[(row["id"], name)]
            assert len(entries) >= 1
            repeat_rows.append({"id": row["id"], "candidate": name, "exact_body_hash": row["outputs"][name]["body_hash"],
                                "independent_receipts": len(entries), "entries": entries})
    (OUT / "exact_repeats.json").write_text(json.dumps(repeat_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    changes = []
    for row in all_rows:
        if row["Qwen_U0"] is None or row["TS_status"] not in ("valid", "valid_with_format_anomaly"):
            continue
        pid = row["id"]
        outcomes = {}
        for name in ("NS_U0", "TS_raw", "Qwen_U0"):
            if row["PriorG"] == row["GT"] and row[name] != row["GT"]:
                outcomes[name] = "harm"
            elif row["PriorG"] != row["GT"] and row[name] == row["GT"]:
                outcomes[name] = "rescue"
            else:
                outcomes[name] = "same_correctness"
        if all(v == "same_correctness" for v in outcomes.values()):
            continue
        qjob = qnew.get(pid) or oldq[reuse[pid]["existing_request_id"]]
        jobs = {"NS_U0": main_jobs[(pid, "N-S")], "TS_raw": main_jobs[(pid, "T-S")], "Qwen_U0": qjob}
        notes = {}
        for name, job in jobs.items():
            rec = receipts[job["request_id"]]
            notes[name] = {"reason": rec["native"]["output"].get("reason") if rec["native"] and rec["native"]["output"] else None,
                           "receipt_path": rec["receipt_path"]}
        changes.append({"id": pid, "sid": row["sid"], "author": row["author"], "GT": row["GT"],
                        "claim": cases[pid]["claim"], "reference_sha256": row["reference_sha256"],
                        "PriorG": row["PriorG"], "labels": {k: row[k] for k in outcomes},
                        "outcomes": outcomes, "output_notes": notes})
    with (OUT / "changed_cases.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in changes:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"cases": len(book), "exact_receipt_count_distribution":
                      {str(n): sum(x["independent_receipts"] == n for x in repeat_rows) for n in sorted({x["independent_receipts"] for x in repeat_rows})},
                      "repeat_cases": [x for x in repeat_rows if x["independent_receipts"] > 1]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
