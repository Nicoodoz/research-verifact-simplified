"""Zero-API source alignment and full-cohort paired analysis for 070."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/070_fixed_evidence_reasoning_diagnosis"
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.evaluation import evaluate, paired_compare  # noqa: E402

LABELS = ("Supported", "Not Supported", "Not Addressed")


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def payload(body):
    return json.loads(body["messages"][-1]["content"])


def argmax(scores):
    return max(LABELS, key=lambda lab: float(scores[lab]))


def rows_to_pred(rows, key):
    return [{"proposition_id": row["id"], "verdict": row[key]} for row in rows]


def false_s(rows, key):
    return sum(row["GT"] != "Supported" and row[key] == "Supported" for row in rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p053 = ROOT / "outputs/053_thinking_prior_validation"
    p055 = ROOT / "outputs/055_zero_label_policy_adaptation"
    p066 = ROOT / "outputs/066_oracle_headroom"
    cases = {x["id"]: x for x in jsonl(p053 / "evaluation_cases.jsonl")}
    errors066 = {x["id"]: x for x in jsonl(p066 / "error_cases.jsonl")}
    preds = list(csv.DictReader((p053 / "predictions.csv").open(encoding="utf-8-sig", newline="")))
    qfeatures = {x["id"]: x for x in jsonl(p055 / "features_qwen_053.jsonl")}
    assert len(cases) == len(preds) == 240 and len(qfeatures) == 237
    ns = {x["id"]: x for x in jsonl(p053 / "main_jobs.jsonl") if x["condition"] == "N-S"}
    ts = {x["id"]: x for x in jsonl(p053 / "main_jobs.jsonl") if x["condition"] == "T-S"}
    assert len(ns) == len(ts) == 240
    q_new = {x["id"]: x for x in jsonl(p055 / "qwen_full_jobs.jsonl") if x["id"] in qfeatures}
    q_reuse = {x["id"]: x for x in jsonl(p055 / "qwen_full_reuse.jsonl") if x["id"] in qfeatures}
    old_q = {x["request_id"]: x for x in jsonl(p053 / "qwen_jobs.jsonl")}
    assert len(q_new) == 209 and len(q_reuse) == 28
    alignment = []
    for pid, case in cases.items():
        expected = {"proposition": case["claim"], "reference": case["reference"]}
        same_ns = payload(ns[pid]["body"]) == expected
        same_ts = payload(ts[pid]["body"]) == expected
        qsource = "missing"
        qjob = None
        if pid in q_new:
            qjob = q_new[pid]
            qsource = "055_new"
        elif pid in q_reuse:
            rid = q_reuse[pid]["existing_request_id"]
            qjob = old_q[rid]
            qsource = "053_reused"
            assert q_reuse[pid]["body_sha256"] == hashlib.sha256(json.dumps(qjob["body"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        same_q = payload(qjob["body"]) == expected if qjob else None
        alignment.append({
            "id": pid, "sid": str(case["sid"]), "reference_sha256": hashlib.sha256(case["reference"].encode("utf-8")).hexdigest(),
            "reference_chars": len(case["reference"]), "claim_sha256": hashlib.sha256(case["claim"].encode("utf-8")).hexdigest(),
            "ns_same_payload": same_ns, "ts_same_payload": same_ts, "q_same_payload": same_q,
            "q_source": qsource, "q_request_id": qjob["request_id"] if qjob else None,
            "ns_request_id": ns[pid]["request_id"], "ts_request_id": ts[pid]["request_id"],
            "ns_model": ns[pid]["body"]["model"], "ts_model": ts[pid]["body"]["model"],
            "q_model": qjob["body"]["model"] if qjob else None,
            "ns_thinking": ns[pid]["body"].get("enable_thinking"),
            "ts_thinking": ts[pid]["body"].get("enable_thinking"),
            "q_thinking": qjob["body"].get("enable_thinking") if qjob else None,
        })
    assert all(x["ns_same_payload"] and x["ts_same_payload"] for x in alignment)
    assert all(x["q_same_payload"] is True for x in alignment if x["q_source"] != "missing")
    with (OUT / "source_alignment.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in alignment:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    source_summary = {
        "all_053_claims": len(cases), "common_valid": len(qfeatures),
        "q_new": len(q_new), "q_reused": len(q_reuse),
        "same_ns": sum(x["ns_same_payload"] for x in alignment),
        "same_ts": sum(x["ts_same_payload"] for x in alignment),
        "same_q": sum(x["q_same_payload"] is True for x in alignment),
        "q_missing_ids": sorted(x["id"] for x in alignment if x["q_source"] == "missing"),
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in (p053 / "evaluation_cases.jsonl", p053 / "predictions.csv", p053 / "main_jobs.jsonl", p053 / "qwen_jobs.jsonl", p055 / "features_qwen_053.jsonl", p055 / "qwen_full_jobs.jsonl", p055 / "qwen_full_reuse.jsonl", p066 / "error_cases.jsonl", p066 / "analysis.json", ROOT / "tasks/070_fixed_evidence_reasoning_diagnosis/protocol.md")},
    }
    (OUT / "source_alignment_summary.json").write_text(json.dumps(source_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    detail = []
    for row in preds:
        pid = row["id"]
        q = qfeatures.get(pid)
        x = dict(id=pid, sid=row["sid"], author=row["author"], GT=row["GT"],
                 PriorG=row["TS_PriorG"], NS_U0=row["NS_U0"], TS_raw=row["TS_raw"],
                 TS_status=row["TS_status"], Qwen_U0=argmax(q["qwen_scores"]) if q else None,
                 Qwen_raw=q["qwen_verdict"] if q else None,
                 TS_scores=q["ts_scores"] if q else None,
                 NS_scores=q["ns_scores"] if q else None,
                 Qwen_scores=q["qwen_scores"] if q else None,
                 reference_sha256=next(z["reference_sha256"] for z in alignment if z["id"] == pid),
                 reference_chars=next(z["reference_chars"] for z in alignment if z["id"] == pid))
        x["baseline_error"] = x["PriorG"] != x["GT"]
        x["correct_candidates"] = [m for m in ("NS_U0", "TS_raw", "Qwen_U0") if x[m] == x["GT"]]
        x["reasoning_oracle_fix"] = bool(x["baseline_error"] and x["correct_candidates"])
        x["TS_raw_correct_PriorG_wrong"] = bool(x["TS_raw"] == x["GT"] and x["PriorG"] != x["GT"])
        detail.append(x)
    assert sum(x["baseline_error"] for x in detail) == 39
    assert {x["id"] for x in detail if x["baseline_error"]} == set(errors066)
    assert all(x["GT"] == errors066[x["id"]]["GT"] and x["PriorG"] == errors066[x["id"]]["baseline_pred"] and cases[x["id"]]["reference"] == errors066[x["id"]]["baseline_reference"] for x in detail if x["baseline_error"])
    assert sum(x["reasoning_oracle_fix"] for x in detail) == 14
    with (OUT / "all_cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for x in detail:
            handle.write(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n")
    common = [x for x in detail if x["Qwen_U0"] in LABELS and x["TS_raw"] in LABELS and x["TS_status"] in ("valid", "valid_with_format_anomaly")]
    assert len(common) == 237
    cohort = [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in common]
    methods = ("PriorG", "NS_U0", "TS_raw", "Qwen_U0")
    evaluated = {m: evaluate(cohort, rows_to_pred(common, m), profile="research_patient", missing="error", iterations=1000) for m in methods}
    comparisons = {}
    for m in methods[1:]:
        rescue = [x for x in common if x["PriorG"] != x["GT"] and x[m] == x["GT"]]
        harm = [x for x in common if x["PriorG"] == x["GT"] and x[m] != x["GT"]]
        comparisons[m] = {
            "paired": paired_compare(cohort, rows_to_pred(common, "PriorG"), rows_to_pred(common, m), iterations=1000),
            "rescue": len(rescue), "harm": len(harm), "net": len(rescue) - len(harm),
            "rescue_by_GT": dict(Counter(x["GT"] for x in rescue)),
            "harm_by_GT": dict(Counter(x["GT"] for x in harm)),
            "rescue_patients": len({x["sid"] for x in rescue}), "harm_patients": len({x["sid"] for x in harm}),
            "falseS_delta": false_s(common, m) - false_s(common, "PriorG"),
            "author": {author: {"rescue": sum(x["author"] == author for x in rescue), "harm": sum(x["author"] == author for x in harm)} for author in ("human", "llm")},
            "transition_counts": dict(Counter(f'{x["PriorG"]} -> {x[m]}' for x in common if x["PriorG"] != x[m])),
        }
    summary = {
        "common_n": len(common), "patients": len({x["sid"] for x in common}),
        "GT_counts": dict(Counter(x["GT"] for x in common)),
        "baseline_correct": sum(x["PriorG"] == x["GT"] for x in common),
        "baseline_errors": sum(x["PriorG"] != x["GT"] for x in common),
        "full_240_baseline_correct": sum(x["PriorG"] == x["GT"] for x in detail),
        "invalid_3": [x["id"] for x in detail if x["id"] not in {z["id"] for z in common}],
        "metrics": {m: {"PA": evaluated[m]["percent_agreement"], "AC1": evaluated[m]["gwet_ac1"], "MCC": evaluated[m]["mcc"], "falseS": false_s(common, m), "confusion_matrix": evaluated[m]["confusion_matrix"], "per_class": evaluated[m]["per_class"], "coverage": evaluated[m]["coverage"]} for m in methods},
        "comparisons": comparisons,
        "reasoning_oracle_fix_14": sum(x["reasoning_oracle_fix"] for x in detail),
        "fix_by_GT": dict(Counter(x["GT"] for x in detail if x["reasoning_oracle_fix"])),
        "fix_by_author": dict(Counter(x["author"] for x in detail if x["reasoning_oracle_fix"])),
        "fix_contributors": dict(Counter(m for x in detail if x["reasoning_oracle_fix"] for m in x["correct_candidates"])),
        "fix_exclusive": dict(Counter(x["correct_candidates"][0] for x in detail if x["reasoning_oracle_fix"] and len(x["correct_candidates"]) == 1)),
        "fix_multiple": sum(x["reasoning_oracle_fix"] and len(x["correct_candidates"]) > 1 for x in detail),
        "TS_raw_correct_PriorG_wrong": sum(x["TS_raw_correct_PriorG_wrong"] for x in detail),
    }
    (OUT / "evaluation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: summary[key] for key in ("common_n", "patients", "baseline_correct", "baseline_errors", "reasoning_oracle_fix_14", "fix_by_GT", "fix_contributors", "fix_exclusive", "fix_multiple", "TS_raw_correct_PriorG_wrong")}, ensure_ascii=False, indent=2))
    for m in methods:
        print(m, {key: summary["metrics"][m][key] for key in ("PA", "MCC", "falseS")})
    for m in methods[1:]:
        print(m, {key: summary["comparisons"][m][key] for key in ("rescue", "harm", "net", "falseS_delta")})


if __name__ == "__main__":
    main()
