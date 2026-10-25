"""Offline executor checks for 070. No network or model calls."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/070_fixed_evidence_reasoning_diagnosis"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


checks = []


def check(name, okay, detail=None):
    checks.append({"name": name, "ok": bool(okay), "detail": detail})


source = read(OUT / "source_alignment_summary.json")
for relative, expected in source["source_sha256"].items():
    path = ROOT / relative
    check("source_hash:" + relative, path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == expected)
align = lines(OUT / "source_alignment.jsonl")
rows = lines(OUT / "all_cases.jsonl")
book = lines(OUT / "casebook_full.jsonl")
changed = lines(OUT / "changed_cases.jsonl")
repeats = read(OUT / "exact_repeats.json")
ev = read(OUT / "evaluation.json")
check("source_coverage", len(align) == 240 and sum(x["q_same_payload"] is True for x in align) == 237)
check("source_exact", all(x["ns_same_payload"] and x["ts_same_payload"] and x["q_same_payload"] is not False for x in align))
check("same_id_complete", len(rows) == 240 and len({x["id"] for x in rows}) == 240 and ev["common_n"] == 237 and ev["patients"] == 40)
check("oracle_14", len(book) == 14 and {x["id"] for x in book} == {x["id"] for x in rows if x["reasoning_oracle_fix"]})
check("oracle_gt", Counter(x["GT"] for x in book) == {"Supported": 6, "Not Supported": 6, "Not Addressed": 2})
check("oracle_patients", len({x["sid"] for x in book}) == 12)
for row in book:
    check("reference_hash:" + row["id"], hashlib.sha256(row["reference"].encode()).hexdigest() == row["reference_sha256"])
    check("three_receipts:" + row["id"], set(row["outputs"]) == {"NS_U0", "TS_raw", "Qwen_U0"} and all((ROOT / x["receipt_path"]).exists() and (ROOT / x["request_path"]).exists() for x in row["outputs"].values()))
    check("native_qwen_agreement:" + row["id"], row["labels"]["Qwen_U0"] == row["outputs"]["Qwen_U0"]["output"]["verdict"])
check("repeat_inventory", len(repeats) == 42 and Counter(x["independent_receipts"] for x in repeats) == {1: 38, 2: 3, 7: 1})
fixids = {x["id"] for x in book}
check("success_not_repeated", all(x["independent_receipts"] == 1 for x in repeats if x["candidate"] in next(z["correct_candidates"] for z in book if z["id"] == x["id"])))
check("changed_ids", len(changed) == 62 and len({x["id"] for x in changed}) == 62)
check("baseline_240", ev["full_240_baseline_correct"] == 201 and ev["baseline_errors"] == 39)
for method, expected in {"NS_U0": (9, 28), "TS_raw": (1, 19), "Qwen_U0": (11, 23)}.items():
    got = ev["comparisons"][method]
    check("paired:" + method, (got["rescue"], got["harm"]) == expected and got["net"] == expected[0] - expected[1])
check("ledger_14", sum(line.startswith("| `") for line in (OUT / "case_ledger.md").read_text(encoding="utf-8").splitlines()) == 14)
check("report_present", (OUT / "report.md").exists())
check("no_reserved_sources", all("reserved" not in key.lower() for key in source["source_sha256"]))
result = {"status": "PASS" if all(x["ok"] for x in checks) else "FAIL", "checks": len(checks),
          "failed": [x for x in checks if not x["ok"]], "new_paid_api_calls": 0, "estimated_new_api_cost_cny": 0,
          "scope": "executor self-check, not independent audit"}
(OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "PASS":
    raise SystemExit(1)
