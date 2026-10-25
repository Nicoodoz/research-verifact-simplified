"""Freeze 084-based, GT-blind provider-neutral inputs for deferred R1 inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks/085_r1_70b_model_swap"
OUT = ROOT / "outputs/085_r1_70b_model_swap"
SAMPLE = ROOT / "outputs/084_f4_coverage_validation/sample_blind.jsonl"
JOBS = ROOT / "outputs/084_f4_coverage_validation/main_jobs.jsonl"
FREEZE = ROOT / "outputs/084_f4_coverage_validation/freeze.json"
EXAMPLES = ROOT / "outputs/071_judge_icl_feasibility/examples.jsonl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_lines(path: Path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def put(path: Path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        f.write("\n")


def put_lines(path: Path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for row in rows:
            json.dump(row, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-source", type=Path, required=True)
    args = parser.parse_args()
    assert not OUT.exists(), "085A output exists; preparation cannot overwrite a freeze"
    frozen = read_json(FREEZE)
    assert frozen["status"] == "FROZEN_BEFORE_FIRST_084_API_AND_GT"
    assert sha(SAMPLE) == frozen["sample_sha256"] and sha(JOBS) == frozen["jobs_sha256"]
    sample = read_lines(SAMPLE)
    jobs = read_lines(JOBS)
    examples = read_lines(EXAMPLES)
    assert len(sample) == 180 and len(jobs) == 360 and len(examples) == 4
    byid = {row["id"]: row for row in sample}
    assert len(byid) == 180 and len({row["sid"] for row in sample}) == 21
    by_case_arm = {(j["id"], j["arm"]): j for j in jobs}
    assert len(by_case_arm) == 360
    bbody = next(j["body"] for j in jobs if j["arm"] == "B")
    fbody = next(j["body"] for j in jobs if j["arm"] == "F4")
    base = bbody["messages"][0]["content"]
    full_f4 = fbody["messages"][0]["content"]
    assert full_f4.startswith(base)
    assert bbody["response_format"] == fbody["response_format"]
    block = full_f4[len(base):]
    demos = [json.loads(line) for line in block.splitlines() if line.startswith("{")]
    assert len(demos) == 4
    for i, (demo, source) in enumerate(zip(demos, examples), 1):
        assert source["ordinal"] == i
        assert demo == {"proposition": source["claim"], "reference": source["reference"],
                        "physician_label": source["physician_label"]}
    expected = bbody["response_format"]["json_schema"]["schema"]
    assert set(expected["properties"]) == {"verdict", "label_scores", "reason", "checks"}
    assert set(expected["required"]) == set(expected["properties"])
    assert expected["properties"]["verdict"]["enum"] == ["Supported", "Not Supported", "Not Addressed"]
    for j in jobs:
        row = byid[j["id"]]
        assert j["sid"] == row["sid"] and j["arm"] in ("B", "F4")
        body = j["body"]
        assert body["messages"][0]["content"] == (base if j["arm"] == "B" else full_f4)
        assert json.loads(body["messages"][1]["content"]) == {"proposition": row["claim"], "reference": row["reference"]}
        assert body["response_format"]["json_schema"]["schema"] == expected
    request_raw = args.request_source.read_bytes()
    request_text = request_raw.decode("utf-8-sig").replace("\r\n", "\n")
    TASK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=False)
    (TASK / "USER_REQUEST.md").write_text(request_text.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    semantics = {"status": "PROVIDER_NEUTRAL_FROZEN_NO_SAGEMAKER_PAYLOAD",
                 "B_system_content": base, "F4_system_content": full_f4,
                 "F4_appendix_exact": block, "F4_demonstrations_in_order": demos,
                 "expected_output_schema": expected,
                 "user_content_format": "JSON with exactly proposition and reference; UTF-8, no clinical label",
                 "B_system_sha256": text_sha(base), "F4_system_sha256": text_sha(full_f4),
                 "source_084_job_sha256": sha(JOBS), "source_071_examples_sha256": sha(EXAMPLES),
                 "warning": "semantic source only; no provider payload, no enable_thinking/reasoning_effort/Alibaba response_format on SageMaker"}
    put(OUT / "prompt_semantics.json", semantics)
    manifest = []
    neutral = []
    for case in sample:
        pid = case["id"]
        manifest.append({"id": pid, "sid": case["sid"], "author": case["author"],
                         "claim_sha256": text_sha(case["claim"]),
                         "reference_sha256": text_sha(case["reference"]),
                         "source_sample_sha256": sha(SAMPLE)})
        for arm in ("B", "F4"):
            job = by_case_arm[pid, arm]
            neutral.append({"id": pid, "sid": case["sid"], "author": case["author"],
                            "arm": arm, "claim": case["claim"], "reference": case["reference"],
                            "instruction_semantic_content": base if arm == "B" else full_f4,
                            "demonstrations_in_order": [] if arm == "B" else demos,
                            "expected_output_schema": expected,
                            "source_084_request_id": job["request_id"],
                            "source_084_body_sha256": job["body_sha256"],
                            "source_084_jobs_file_sha256": sha(JOBS),
                            "source_084_sample_file_sha256": sha(SAMPLE)})
    assert len(neutral) == 360 and not any("GT" in x or "human_gt" in x for x in neutral)
    put_lines(OUT / "frozen_cohort_manifest.jsonl", manifest)
    put_lines(OUT / "neutral_jobs.jsonl", neutral)
    sources = (SAMPLE, JOBS, FREEZE, EXAMPLES,
               ROOT / "outputs/071_judge_icl_feasibility/freeze.json",
               ROOT / "outputs/084_f4_coverage_validation/new_predictions.jsonl",
               ROOT / "outputs/084_f4_coverage_validation/evaluation_results.json",
               TASK / "protocol_predeploy.md", TASK / "USER_REQUEST.md")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    put(OUT / "source_manifest.json", {"head_at_preparation": head,
        "attachment_raw_sha256": hashlib.sha256(request_raw).hexdigest(),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        "artifacts_sha256": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
        "claims": 180, "patients": 21, "arms": dict(Counter(j["arm"] for j in neutral)),
        "evaluation_GT_read": False, "new_inference_calls": 0})
    print(json.dumps({"claims":len(sample),"neutral_jobs":len(neutral),"demos":len(demos),
                      "head":head,"GT_read":False},ensure_ascii=False))


if __name__ == "__main__":
    main()
