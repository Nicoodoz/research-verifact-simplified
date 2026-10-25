"""Read-only post-A/B integrity and boundary audit."""
import json
from pathlib import Path
import subprocess

import preflight as p


def main():
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    p.check_frozen_sources()
    profile = p.read(p.PUBLIC / "profile.json")
    check("360 frozen requests", len(profile["jobs"]) == 360)
    check("B F4 counts", {arm: sum(j["arm"] == arm for j in profile["jobs"]) for arm in ("B", "F4")} == {"B": 180, "F4": 180})
    check("all local input plus 8192 fit", all(j["local_input_tokens"] + 8192 <= 20000 for j in profile["jobs"]))
    check("only two token difference", {j["old_official_token_delta"] for j in profile["jobs"]} == {-2})
    check("original locks preserved", profile["old_identity_lock_sha256"] == p.sha(p.ROOT / "tasks/085_r1_70b_autodl/identity_lock.json"))
    identity = p.read(p.PUBLIC / "service_identity.json")
    check("live model id and context", identity["model"] == p.MODEL and identity["max_model_len"] == 20000)
    check("live raw models hash", p.sha(p.ROOT / identity["private_response_path"]) == identity["models_response_sha256"])
    selected = p.selected_jobs()
    items = [("A", p.read(p.PRIVATE / "fictional_job.json"), p.read(p.PUBLIC / "stage_a.json"))]
    for role, job in selected:
        items.append((role, job, p.read(p.PUBLIC / "stage_b" / f"{role}.json")))
    check("four authorized inference slots", len(items) == 4)
    for role, job, result in items:
        found = p.attempts(job["request_id"])
        check(role + " one HTTP200", sum(r["http_status"] == 200 for _, r, _ in found) == 1)
        check(role + " no retry", len(found) == 1)
        _, receipt, folder = found[0]
        check(role + " request hash", p.sha(folder / "request.json") == result["request_sha256"])
        check(role + " response hash", p.sha(folder / "response.raw") == result["response_sha256"])
        check(role + " 200", receipt["http_status"] == 200)
        check(role + " model", result["response_model"] == p.MODEL)
        check(role + " content paths", result["reasoning_content_present"] and result["content_present"])
        check(role + " prompt token match", result["prompt_tokens"] == result["local_prompt_tokens"])
        check(role + " context fit", result["full_output_budget_fits_20k"])
        check(role + " raw parse", result["raw_verdict_valid"] and not result["truncated"])
        check(role + " scores independently valid", result["label_scores_valid"])
        check(role + " no GT read", not result["GT_read"])
    check("frozen selected three", [(role, job["id"], job["arm"]) for role, job in selected] ==
          [(c["role"], c["id"], c["arm"]) for c in p.read(p.OLD / "preflight_selection.json")["cases"]])
    forecast = p.read(p.PUBLIC / "forecast.json")
    check("formal stopped", forecast["status"] == "AWAIT_USER_FORMAL_AUTHORIZATION" and forecast["remaining_R1_B"] == 179 and forecast["remaining_R1_F4"] == 178)
    check("no evaluation", not (p.PUBLIC / "evaluation.json").exists())
    check("clinical jobs privately ignored", subprocess.run(["git", "check-ignore", "-q", str(p.PRIVATE / "jobs.jsonl")], cwd=p.ROOT).returncode == 0)
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in p.PUBLIC.rglob("*.json"))
    check("no clinical payload in public artifacts", '"reference"' not in public_text and '"claim"' not in public_text and '"messages"' not in public_text)
    out = {"status": "PASS", "checks": checks, "n_checks": len(checks),
           "HTTP200_inference": 4, "A_fictional": 1, "B_frozen": 3, "retries": 0,
           "GT_read": False, "formal_calls": 0, "evaluation": False,
           "private_root": str(p.PRIVATE.relative_to(p.ROOT)),
           "profile_sha256": p.sha(p.PUBLIC / "profile.json"),
           "forecast_sha256": p.sha(p.PUBLIC / "forecast.json")}
    path = p.PUBLIC / "selfcheck.json"
    if not path.exists():
        p.put_json(path, out)
    print(json.dumps({"status": out["status"], "n_checks": out["n_checks"],
                      "HTTP200_inference": 4, "formal_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
