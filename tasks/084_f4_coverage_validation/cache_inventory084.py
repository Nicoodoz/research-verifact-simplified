"""Read-only exact-body receipt coverage beyond the 031 material subset."""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "tasks/082_anchor_configuration_adaptation"))
import prepare082 as p


def lines(rel):
    return [json.loads(s) for s in (ROOT / rel).open(encoding="utf-8-sig") if s.strip()]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main():
    broad = {x["proposition_id"]: x for x in lines("outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")}
    old = {x["id"]: x for x in lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")}
    b = lines("outputs/079_f4_priorg_adaptation/calibration_cases.jsonl")[0]["B"]["body"]
    f = lines("outputs/079_f4_priorg_adaptation/main_jobs.jsonl")[0]["body"]
    cache = defaultdict(dict)
    for x in old.values():
        for arm in ("B", "F4"):
            info = x["arms"][arm]
            cache[x["id"]][arm] = {"source": "082_old532", "body_sha256": info["body_sha256"],
                                   "receipt_source": info["receipt_source"]}
    candidate = Counter()
    for x in lines("outputs/076_existing_results_synthesis/unified_predictions.jsonl"):
        arm = x["arm"]
        pid = x["id"]
        if arm not in ("B", "F4") or pid not in broad:
            continue
        source = broad[pid]
        template = b if arm == "B" else f
        expected = p.digest(p.score_body(template, source["text"], source["reference"]))
        candidate["considered"] += 1
        if x["body_sha256"] != expected:
            candidate["nonexact"] += 1
            continue
        if not x.get("receipt_source") or not (ROOT / x["receipt_source"]).exists():
            candidate["missing_receipt"] += 1
            continue
        candidate["exact"] += 1
        if pid not in old and arm not in cache[pid]:
            cache[pid][arm] = {"source": "076_prior_BF4", "body_sha256": expected,
                               "receipt_source": x["receipt_source"]}
    sample = {x["id"] for x in lines("outputs/084_f4_coverage_validation/sample_blind.jsonl")}
    assert all(not cache[pid] for pid in sample)
    inventory = json.loads((OUT / "coverage_inventory.json").read_text(encoding="utf-8"))
    patientrows = []
    for row in inventory["patients"]:
        sid = row["sid"]
        ids = [pid for pid,x in broad.items() if x["subject_id"] == sid]
        available = [pid for pid in ids if pid in cache]
        patientrows.append({"sid": sid, "legal_C48": len(ids), "exact_B_any": sum("B" in cache[pid] for pid in ids),
                            "exact_F4_any": sum("F4" in cache[pid] for pid in ids),
                            "exact_BF4_pair": sum({"B","F4"} <= set(cache[pid]) for pid in ids),
                            "old532": row["old532"], "new_paired_eligible": row["new_paired_eligible"]})
    with (OUT / "cache_receipt_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=patientrows[0].keys())
        w.writeheader(); w.writerows(patientrows)
    (OUT / "cache_receipt_inventory.json").write_text(json.dumps({"source_sha256": {
        rel: sha(rel) for rel in ("outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl",
                            "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl",
                            "outputs/076_existing_results_synthesis/unified_predictions.jsonl",
                            "outputs/079_f4_priorg_adaptation/calibration_cases.jsonl",
                            "outputs/079_f4_priorg_adaptation/main_jobs.jsonl")},
        "candidate_receipts": dict(candidate), "patients": patientrows,
        "new084_sample_historical_exact_B_or_F4": 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"candidate": dict(candidate), "exact_BF4_all_eval": sum(x["exact_BF4_pair"] for x in patientrows),
                      "new084_exact_cache": 0}))


if __name__ == "__main__":
    main()
