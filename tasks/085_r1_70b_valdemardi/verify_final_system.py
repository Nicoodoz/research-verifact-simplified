"""Independent point-metric checks for the full-180 secondary system view."""
import json
from pathlib import Path

from sklearn.metrics import accuracy_score, matthews_corrcoef

import preflight as p


def main():
    result = p.read(p.PUBLIC / "final_system_comparison.json")
    rows = p.rows(p.PRIVATE / "final_system_case_ledger.jsonl")
    checks = {}

    def require(name, okay):
        checks[name] = bool(okay)
        if not okay:
            raise AssertionError(name)

    require("180 unique ID", len(rows) == 180 and len({x["id"] for x in rows}) == 180)
    require("21 patients", len({x["sid"] for x in rows}) == 21)
    require("original 084 baselines", result["summary"]["V4-B-PriorG"]["correct"] == 155 and result["summary"]["V4-F4-PriorG"]["correct"] == 161)
    for arm, summary in result["summary"].items():
        gt = [x["GT"] for x in rows]
        labels = [x["labels"][arm] for x in rows]
        require(arm + " correct", summary["correct"] == sum(a == b for a, b in zip(gt, labels)))
        require(arm + " PA", abs(summary["PA"] - accuracy_score(gt, labels)) < 1e-12)
        require(arm + " MCC", abs(summary["MCC"] - matthews_corrcoef(gt, labels)) < 1e-12)
        require(arm + " false-S", summary["false_S"] == sum(a != "Supported" and b == "Supported" for a, b in zip(gt, labels)))
    for name, comparison in result["comparisons"].items():
        require(name + " rescue/harm", comparison["net_correct"] == len(comparison["rescued_ids"]) - len(comparison["harmed_ids"]))
        require(name + " patient partition", comparison["patient_wins"] + comparison["patient_losses"] + comparison["patient_ties"] == 21)
    require("R1-B U2 equals G on fixed data", all(x["labels"]["R1-B-U2"] == x["labels"]["R1-B-PriorG"] for x in rows))
    require("R1-F4 U2 equals G on fixed data", all(x["labels"]["R1-F4-U2"] == x["labels"]["R1-F4-PriorG"] for x in rows))
    require("source V4 hash", result["source_084_predictions_sha256"] == p.sha(p.ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl"))
    require("source R1 hash", result["source_r1_predictions_sha256"] == p.sha(p.PRIVATE / "r1_predictions.jsonl"))
    output = {"status": "PASS", "n_checks": len(checks), "checks": checks,
              "evaluation_sha256": p.sha(p.PUBLIC / "final_system_comparison.json"),
              "independent_point_metrics": True, "independent_bootstrap_audit": False}
    path = p.PUBLIC / "final_system_selfcheck.json"
    if path.exists():
        raise FileExistsError("final-system selfcheck already saved")
    p.put_json(path, output)
    print(json.dumps({"status": "PASS", "n_checks": len(checks)}))


if __name__ == "__main__":
    main()
