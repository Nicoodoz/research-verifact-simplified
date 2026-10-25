"""Freeze the A/B-observed native response paths without reading any GT."""
import json

import preflight as p


def main():
    items = [("A", p.read(p.PRIVATE / "fictional_job.json"), p.read(p.PUBLIC / "stage_a.json"))]
    for role, job in p.selected_jobs():
        items.append((role, job, p.read(p.PUBLIC / "stage_b" / f"{role}.json")))
    for role, job, observed in items:
        found = p.attempts(job["request_id"])
        success = [(r, f) for _, r, f in found if r["http_status"] == 200]
        if len(success) != 1:
            raise ValueError(role + " lacks unique HTTP200")
        envelope = json.loads((success[0][1] / "response.raw").read_bytes())
        if envelope["model"] != p.MODEL:
            raise ValueError(role + " model changed")
        choice = envelope["choices"][0]
        if not isinstance(choice["message"]["reasoning_content"], str) or not isinstance(choice["message"]["content"], str):
            raise ValueError(role + " native paths differ")
        if not isinstance(choice["finish_reason"], str) or not isinstance(envelope["usage"], dict):
            raise ValueError(role + " finish/usage paths differ")
        if p.sha(success[0][1] / "response.raw") != observed["response_sha256"]:
            raise ValueError(role + " response SHA differs")
    value = {"status": "FROZEN_AFTER_AB_NO_GT", "created_utc": p.stamp(),
             "content_path": ["choices", 0, "message", "content"],
             "reasoning_path": ["choices", 0, "message", "reasoning_content"],
             "finish_path": ["choices", 0, "finish_reason"], "usage_path": ["usage"],
             "truncation_values": ["length", "max_tokens", "max_new_tokens", "truncated"],
             "model": p.MODEL, "GT_read": False,
             "A_response_sha256": items[0][2]["response_sha256"],
             "B_response_sha256": {role: observed["response_sha256"] for role, _, observed in items[1:]},
             "parse_source_sha256": p.sha(p.ROOT / "tasks/085_r1_70b_model_swap/parse_r1.py")}
    path = p.PUBLIC / "parser_profile.json"
    if path.exists():
        old = p.read(path)
        for key in ("status", "content_path", "reasoning_path", "finish_path", "usage_path", "model", "A_response_sha256", "B_response_sha256", "parse_source_sha256"):
            if old[key] != value[key]:
                raise ValueError("frozen parser differs")
    else:
        p.put_json(path, value)
    print(json.dumps({"status": value["status"], "GT_read": False}))


if __name__ == "__main__":
    main()
