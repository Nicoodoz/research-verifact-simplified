"""Independent integrity/point-metric checks after 360 R1 replies and evaluation."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef

import formal_runner as runner
import preflight as p


def main():
    checks = {}

    def require(name, value):
        checks[name] = bool(value)
        if not value:
            raise AssertionError(name)

    p.check_frozen_sources()
    profile = p.read(p.PUBLIC / "profile.json")
    jobs, indexed = runner.frozen_jobs()
    require("frozen 360", len(jobs) == 360 and len(indexed) == 360)
    require("B F4 180 each", sum(j["arm"] == "B" for j in jobs) == 180 and sum(j["arm"] == "F4" for j in jobs) == 180)
    auth = p.read(p.PUBLIC / "formal_authorization.json")
    require("formal user authorization recorded", auth["user_authorized_formal"] and auth["initial_HTTP200_slots"] == 3)
    require("profile unchanged", auth["frozen_profile_sha256"] == p.sha(p.PUBLIC / "profile.json"))
    complete = p.read(p.PUBLIC / "formal_completion.json")
    reconciled = p.read(p.PUBLIC / "formal_reconciliation.json")
    require("360 complete", complete["all_HTTP200"] and complete["frozen_slots"] == 360)
    require("original 3 and new 357", reconciled["A_B_reused_HTTP200"] == 3 and reconciled["new_formal_HTTP200"] == 357 and reconciled["total_HTTP200"] == 360)
    retry = 0
    unknown = 0
    per_arm = {"B": 0, "F4": 0}
    for j in jobs:
        found = p.attempts(j["request_id"])
        successes = [(r, folder) for _, r, folder in found if r["http_status"] == 200]
        require(j["request_id"] + " exactly one HTTP200", len(successes) == 1)
        retry += max(0, len(found) - 1)
        unknown += sum(r.get("outcome_unknown", False) for _, r, _ in found)
        receipt, folder = successes[0]
        request = p.read(folder / "request.json")
        require(j["request_id"] + " frozen body SHA", request["job"]["body_sha256"] == indexed[j["request_id"]]["body_sha256"] and p.digest(p.encoded(request["job"]["body"])) == j["body_sha256"])
        require(j["request_id"] + " native hash", receipt["response_sha256"] == p.sha(folder / "response.raw") and receipt["request_sha256"] == p.sha(folder / "request.json"))
        observed = p.inspect(folder, indexed[j["request_id"]]["local_input_tokens"])
        require(j["request_id"] + " model and input", observed["response_model"] == p.MODEL and observed["local_server_prompt_tokens_match"])
        require(j["request_id"] + " context", observed["full_output_budget_fits_20k"])
        per_arm[j["arm"]] += 1
    require("arm coverage", per_arm == {"B": 180, "F4": 180})
    predictions_path = p.PRIVATE / "r1_predictions.jsonl"
    material = p.read(p.PUBLIC / "r1_materialization.json")
    require("private predictions hash", p.sha(predictions_path) == material["private_predictions_sha256"])
    predictions = p.rows(predictions_path)
    require("materialized positions", len(predictions) == 360 and len({(x["id"], x["arm"]) for x in predictions}) == 360)
    for arm in ("B", "F4"):
        subset = [x for x in predictions if x["arm"] == arm]
        require(arm + " raw coverage", sum(x["valid"] for x in subset) == material["coverage"][arm]["raw_valid"])
        require(arm + " score coverage", sum(x["score_valid"] for x in subset) == material["coverage"][arm]["scores_valid"])
        require(arm + " raw and score separate", all(not x["score_valid"] or x["label_scores"] is not None for x in subset))
    result = p.read(p.PUBLIC / "formal_evaluation.json")
    case_rows = p.rows(p.PRIVATE / "formal_case_ledger.jsonl")
    require("same common count", len(case_rows) == result["common_valid_n"] and len(case_rows) + len(result["excluded_from_common"]) == 180)
    require("21 patient frozen cohort", len({x["sid"] for x in p.rows(p.OLD / "frozen_cohort_manifest.jsonl")}) == 21)
    for arm, summary in result["primary"].items():
        truth = [x["GT"] for x in case_rows]
        pred = [x["labels"][arm] for x in case_rows]
        require(arm + " correct", summary["correct"] == sum(a == b for a, b in zip(truth, pred)))
        require(arm + " PA independent", abs(summary["PA"] - accuracy_score(truth, pred)) < 1e-12)
        require(arm + " MCC independent", abs(summary["MCC"] - matthews_corrcoef(truth, pred)) < 1e-12)
        require(arm + " macro-F1 independent", abs(summary["macro_F1"] - f1_score(truth, pred, labels=list(p.LABELS), average="macro", zero_division=0)) < 1e-12)
        require(arm + " false-S", summary["false_S"] == sum(t != "Supported" and y == "Supported" for t, y in zip(truth, pred)))
    for name, comparison in result["comparisons"].items():
        require(name + " rescue/harm", comparison["net_correct"] == len(comparison["rescued_ids"]) - len(comparison["harmed_ids"]))
        require(name + " patient partition", comparison["patient_wins"] + comparison["patient_losses"] + comparison["patient_ties"] == result["common_valid_patients"])
    require("secondary pair coverage", result["secondary_score_valid_pair_n"] <= result["common_valid_n"])
    require("private raw ignored", subprocess.run(["git", "check-ignore", "-q", str(p.PRIVATE / "r1_predictions.jsonl")], cwd=p.ROOT).returncode == 0)
    require("gitignore unchanged", subprocess.run(["git", "diff", "--quiet", "--", ".gitignore"], cwd=p.ROOT).returncode == 0)
    out = {"status": "PASS", "n_checks": len(checks), "checks": checks,
           "frozen_slots": 360, "new_formal_HTTP200": 357, "retry_attempts": retry,
           "unknown_outcomes": unknown, "common_valid_n": result["common_valid_n"],
           "independent_point_metrics": ["PA", "MCC", "macro-F1", "correct", "false-S"],
           "bootstrap_implementation_reused_from_project": True,
           "independent_audit": False,
           "evaluation_sha256": p.sha(p.PUBLIC / "formal_evaluation.json")}
    path = p.PUBLIC / "formal_selfcheck.json"
    if path.exists():
        raise FileExistsError("formal selfcheck already saved")
    p.put_json(path, out)
    print(json.dumps({"status": "PASS", "n_checks": len(checks), "retry_attempts": retry,
                      "unknown_outcomes": unknown, "common_valid_n": result["common_valid_n"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
