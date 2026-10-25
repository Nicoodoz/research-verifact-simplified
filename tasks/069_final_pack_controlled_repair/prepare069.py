"""Freeze mechanism controls and the contingent GT-blind development cohort."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
from build_stage3_066 import CORPUS_PATH  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def id_hash(pid):
    return hashlib.sha256(str(pid).encode("utf-8")).hexdigest()


def split_blocks(reference):
    starts = list(re.finditer(r"(?m)^\d+\. Date:", reference))
    if not starts:
        raise ValueError("no baseline passage blocks")
    header = reference[:starts[0].start()]
    blocks = [reference[match.start():(starts[i + 1].start() if i + 1 < len(starts) else len(reference))].rstrip("\n") for i, match in enumerate(starts)]
    return header, blocks


def renumber(block, index):
    return re.sub(r"^\d+\. Date:", f"{index}. Date:", block, count=1)


def add_job(jobs, pid, arm, body):
    assert body["model"] == c.MODELS["deepseek"]
    assert body["enable_thinking"] is True and body["reasoning_effort"] == "high" and body["max_tokens"] == 8192
    payload = json.loads(body["messages"][1]["content"])
    assert set(payload) == {"proposition", "reference"}
    job = {"request_id": f"069_{arm}_" + id_hash(pid)[:24], "id": pid, "arm": arm, "model_key": "deepseek", "body": body}
    job["body_sha256"] = c.digest(body)
    job["reservation_cny"] = c.bound(job)
    jobs.append(job)


def main():
    if (OUT / "freeze.json").exists():
        raise RuntimeError("069 already frozen")
    OUT.mkdir(parents=True, exist_ok=True)
    preflight = {row["id"]: row for row in jsonl(OUT / "preflight_cases.jsonl")}
    assert len(preflight) == 10 and all(row["baseline_mapped"] and row["oracle_in_c48"] and row["oracle_rebuilt_exact"] for row in preflight.values())
    cases = {row["id"]: row for row in jsonl(ROOT / "outputs/066_oracle_headroom/error_cases.jsonl")}
    mapping = {row["id"]: row for row in jsonl(ROOT / "outputs/066_oracle_headroom/final_mapping.jsonl")}
    baseline_jobs = {row["id"]: row for row in jsonl(ROOT / "outputs/053_thinking_prior_validation/main_jobs.jsonl") if row["condition"] == "T-S"}
    oracle_jobs = {row["id"]: row for row in jsonl(ROOT / "outputs/066_oracle_headroom/stage3_jobs.jsonl")}
    corpora = {key: {row["passage_id"]: row for row in jsonl(path)} for key, path in CORPUS_PATH.items()}
    jobs, controls = [], []
    for pid in sorted(preflight):
        shape, case, oracle = preflight[pid], cases[pid], mapping[pid]
        b_ids, o_ids = shape["baseline_ids"], oracle["kept_pids"]
        assert b_ids and o_ids and set(o_ids) <= set(case["c48_pids"])
        header, blocks = split_blocks(case["baseline_reference"])
        assert len(blocks) == len(b_ids) == shape["baseline_blocks"]
        old_payload = json.loads(baseline_jobs[pid]["body"]["messages"][1]["content"])
        oracle_payload = json.loads(oracle_jobs[pid]["body"]["messages"][1]["content"])
        assert old_payload == {"proposition": case["claim"], "reference": case["baseline_reference"]}
        assert oracle_payload == {"proposition": case["claim"], "reference": oracle["reference"]}
        corpus = corpora[case["corpus_source"]]
        missing_ids = [x for x in o_ids if x not in b_ids]
        retained_blocks = [block for block, source_id in zip(blocks, b_ids) if source_id in set(o_ids)]
        add_reference = case["baseline_reference"]
        if missing_ids:
            separator = "" if add_reference.endswith("\n") else "\n"
            addition = "\n".join(c.final_line(len(blocks) + index, corpus[source_id]) for index, source_id in enumerate(missing_ids, 1))
            add_reference = add_reference + separator + addition
        delete_reference = None
        if retained_blocks:
            delete_reference = header + "\n".join(renumber(block, index) for index, block in enumerate(retained_blocks, 1))
        combo_reference = header + oracle["reference"]
        assert add_reference.startswith(case["baseline_reference"])
        assert combo_reference[len(header):] == oracle["reference"]
        if delete_reference:
            assert len(retained_blocks) == len(set(b_ids) & set(o_ids))
        add_job(jobs, pid, "baseline_repeat", baseline_jobs[pid]["body"])
        add_job(jobs, pid, "oracle_repeat", oracle_jobs[pid]["body"])
        if missing_ids:
            add_job(jobs, pid, "add_only", c.score_body(case["claim"], add_reference))
        if delete_reference:
            add_job(jobs, pid, "delete_only", c.score_body(case["claim"], delete_reference))
        add_job(jobs, pid, "combined_header", c.score_body(case["claim"], combo_reference))
        controls.append({
            "id": pid, "sid": str(case["sid"]), "GT": case["GT"], "baseline_ids": b_ids,
            "oracle_ids": o_ids, "missing_ids": missing_ids,
            "header_chars": len(header), "baseline_chars": len(case["baseline_reference"]),
            "add_only_chars": len(add_reference), "delete_only_chars": len(delete_reference) if delete_reference else None,
            "combined_header_chars": len(combo_reference), "oracle_chars": len(oracle["reference"]),
            "add_only_identical_to_baseline": not missing_ids, "delete_only_constructable": bool(delete_reference),
            "baseline_blocks": len(blocks), "oracle_blocks": len(o_ids),
        })
    assert len(jobs) == 48
    assert len({job["request_id"] for job in jobs}) == len(jobs)
    with (OUT / "stage1_controls.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in controls:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with (OUT / "stage1_jobs.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(json.dumps(job, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    # Contingent stage-2 cohort is frozen before any new 069 answers.
    mechanism_patients = {str(row["sid"]) for row in controls}
    historic = list(csv.DictReader((ROOT / "outputs/067_conservative_evidence_packing/results_v2.csv").open(encoding="utf-8-sig", newline="")))
    blind052 = {row["id"]: row for row in jsonl(ROOT / "outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl")}
    eligible = [row for row in historic if row["sid"] not in mechanism_patients and row["id"] not in preflight and blind052[row["id"]]["mapped"]]
    wrong = sorted((row for row in eligible if row["baseline"] != row["GT"]), key=lambda row: id_hash(row["id"]))[:8]
    correct = sorted((row for row in eligible if row["baseline"] == row["GT"]), key=lambda row: id_hash(row["id"]))[:12]
    assert len(wrong) == 8 and len(correct) == 12
    selected = sorted(wrong + correct, key=lambda row: id_hash(row["id"]))
    with (OUT / "stage2_cohort_blind.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in selected:
            x = blind052[row["id"]]
            handle.write(json.dumps({"id": row["id"], "sid": row["sid"], "author": row["author"], "claim": x["claim"], "baseline_reference": x["baseline_reference"], "c48_pids": x["c48_pids"], "source": x["source"]}, ensure_ascii=False, sort_keys=True) + "\n")
    with (OUT / "stage2_cohort_evaluation.csv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "sid", "author", "GT", "baseline_pg", "baseline_raw", "stratum"])
        writer.writeheader()
        for row in selected:
            writer.writerow({"id": row["id"], "sid": row["sid"], "author": row["author"], "GT": row["GT"], "baseline_pg": row["baseline"], "baseline_raw": row["baseline_raw"], "stratum": "wrong" if row["baseline"] != row["GT"] else "correct"})
    stage1_bound = sum(c.bound(job) for job in jobs)
    assert stage1_bound < 8, f"core mechanism controls exceed cap: {stage1_bound}"
    paths = [HERE / "protocol.md", HERE / "prepare069.py", OUT / "preflight.json", OUT / "stage1_jobs.jsonl", OUT / "stage1_controls.jsonl", OUT / "stage2_cohort_blind.jsonl", OUT / "stage2_cohort_evaluation.csv", ROOT / "outputs/066_oracle_headroom/error_cases.jsonl", ROOT / "outputs/066_oracle_headroom/final_mapping.jsonl", ROOT / "outputs/066_oracle_headroom/stage3_jobs.jsonl"]
    freeze = {
        "task": "069_final_pack_controlled_repair", "stage": "stage1_mechanism_core",
        "cases": len(controls), "patients": len(mechanism_patients), "jobs": len(jobs),
        "arms": {arm: sum(job["arm"] == arm for job in jobs) for arm in ("baseline_repeat", "oracle_repeat", "add_only", "delete_only", "combined_header")},
        "conservative_stage1_core_reservation_cny": stage1_bound,
        "hard_cap_cny_all_stages": 8.0, "model": c.MODELS["deepseek"],
        "price_peak_cny_per_million_input_output": list(c.PRICES["deepseek"]),
        "price_source": "https://help.aliyun.com/zh/model-studio/model-pricing",
        "stage2_contingent_cases": len(selected), "stage2_contingent_patients": len({row["sid"] for row in selected}),
        "stage2_wrong_stratum": len(wrong), "stage2_correct_stratum": len(correct),
        "GT_in_Judge_body": False, "GT_aware_stage1_only": True, "reserved_used": False,
        "source_sha256": {str(path.relative_to(ROOT)): sha_file(path) for path in paths},
    }
    (OUT / "freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: freeze[key] for key in ("cases", "patients", "jobs", "arms", "conservative_stage1_core_reservation_cny", "hard_cap_cny_all_stages", "stage2_contingent_cases", "stage2_contingent_patients")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
