"""Check full 032 C48 text against all 082 historical B/F4 request bodies."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "tasks/082_anchor_configuration_adaptation"))
import prepare082 as p


def lines(path):
    return [json.loads(s) for s in Path(path).open(encoding="utf-8-sig") if s.strip()]


def main():
    broad = {x["proposition_id"]: x for x in lines(ROOT / "outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")}
    old = lines(ROOT / "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    bt = lines(ROOT / "outputs/079_f4_priorg_adaptation/calibration_cases.jsonl")[0]["B"]["body"]
    ft = lines(ROOT / "outputs/079_f4_priorg_adaptation/main_jobs.jsonl")[0]["body"]
    result = Counter()
    mismatches = []
    for x in old:
        pid = x["id"]
        item = broad[pid]
        for arm, template in (("B", bt), ("F4", ft)):
            expected = p.digest(p.score_body(template, item["text"], item["reference"]))
            actual = x["arms"][arm]["body_sha256"]
            if expected == actual:
                result[(x["cohort"], arm, "exact")] += 1
            else:
                result[(x["cohort"], arm, "different_body")] += 1
                mismatches.append({"id": pid, "sid": x["sid"], "cohort": x["cohort"], "arm": arm,
                                   "expected_body_sha256": expected, "historical_body_sha256": actual})
    artifact = {"counts": {"/".join(k):v for k,v in result.items()}, "mismatches": mismatches}
    (OUT / "historical_reference_consistency.json").write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"counts": artifact["counts"], "mismatch_n": len(mismatches)}))


if __name__ == "__main__":
    main()
