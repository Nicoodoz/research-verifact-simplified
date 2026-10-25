"""GT-blind model and output-format preflight while the fixed queue runs."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
from common053 import parse_response, VALID


def main():
    statuses, models, arms = Counter(), Counter(), Counter()
    for path in (ROOT / "outputs/084_f4_coverage_validation/attempts").glob("*/receipt.json"):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        tr = receipt["transport"]
        req = json.loads((path.parent / "request.json").read_text(encoding="utf-8"))
        arms[req["job"]["arm"]] += 1
        if tr.get("http_status") == 200:
            x = parse_response(tr, True, True)
            statuses[x["status"]] += 1
            models[x.get("model_returned")] += 1
        else:
            statuses[f"HTTP{tr.get('http_status')}"] += 1
    print(json.dumps({"attempts": sum(arms.values()), "arms": arms, "parse_status": statuses,
                      "models": models, "expected_core_valid_statuses": VALID}, ensure_ascii=False))


if __name__ == "__main__":
    main()
