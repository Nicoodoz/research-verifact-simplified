"""Read-only scientific verification for task 034."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.evaluation import evaluate, paired_compare

OUT = ROOT / "outputs" / "034_same_data_comparison"
COMMON = OUT / "predictions_common.csv"
METRICS = OUT / "metrics.json"
PAIRED = OUT / "paired.json"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def make(rows, method):
    cohort = [{"proposition_id": r["proposition_id"], "subject_id": r["subject_id"], "human_gt": r["GT"]} for r in rows]
    pred = [{"proposition_id": r["proposition_id"], "verdict": r[method]} for r in rows]
    return cohort, pred


def main():
    rows = read_csv(COMMON)
    assert len(rows) == 3675
    assert len({r["proposition_id"] for r in rows}) == 3675
    assert len({r["subject_id"] for r in rows}) == 40
    stored = json.loads(METRICS.read_text(encoding="utf-8"))
    methods = ["Original_Verifact_O", "U2", "U2_A_all40_LOPO"]
    for scope, selected in {
        "all": rows,
        "human": [r for r in rows if r["author_type"] == "human"],
        "llm": [r for r in rows if r["author_type"] == "llm"],
    }.items():
        for method in methods:
            cohort, pred = make(selected, method)
            actual = evaluate(cohort, pred, profile="research_patient", iterations=1000)
            assert actual == stored[scope][method], (scope, method)

    saved_pairs = json.loads(PAIRED.read_text(encoding="utf-8"))
    cohort, o = make(rows, "Original_Verifact_O")
    _, u = make(rows, "U2")
    _, a = make(rows, "U2_A_all40_LOPO")
    assert paired_compare(cohort, o, u, iterations=1000) == saved_pairs["all"]["U2_minus_Original_Verifact_O"]
    assert paired_compare(cohort, u, a, iterations=1000) == saved_pairs["all"]["A_all40_minus_U2"]
    assert paired_compare(cohort, o, a, iterations=1000) == saved_pairs["all"]["A_all40_minus_Original_Verifact_O"]

    result = {"status": "pass", "n": len(rows), "patients": 40,
              "checks": ["unique_ids", "all_metrics_exact", "all_primary_pairs_exact"]}
    (OUT / "verification_001.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("034 verification PASS")


if __name__ == "__main__":
    main()
