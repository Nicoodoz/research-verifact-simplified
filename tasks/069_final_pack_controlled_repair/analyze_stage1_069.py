"""Analyze frozen 069 mechanism calls and historical B0/O0 without selection."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
import run066  # noqa: E402
import run069  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def parsed(job, transport):
    if not transport or transport.get("http_status") != 200:
        return {"status": "unavailable"}
    x = c.parse({**job, "kind": "judge"}, transport)
    if x.get("status") in ("valid", "valid_with_format_anomaly") and x.get("scores") and x.get("verdict") in c.LABELS:
        return {"status": "valid", "raw": x["verdict"], "pg": c.priorg(x["scores"]), "scores": x["scores"]}
    return {"status": "invalid", "parse_status": x.get("status"), "errors": x.get("errors", [])}


def main():
    controls = {x["id"]: x for x in jsonl(OUT / "stage1_controls.jsonl")}
    newjobs = jsonl(OUT / "stage1_jobs.jsonl")
    new_by_key = {(x["id"], x["arm"]): x for x in newjobs}
    histjobs = {x["id"]: x for x in jsonl(ROOT / "outputs/066_oracle_headroom/stage3_jobs.jsonl")}
    pred053 = {x["id"]: x for x in csv.DictReader((ROOT / "outputs/053_thinking_prior_validation/predictions.csv").open(encoding="utf-8-sig", newline=""))}
    _, oldterm = run066.state()
    _, newterm = run069.state()
    rows = []
    for pid, shape in controls.items():
        gt = shape["GT"]
        original = pred053[pid]
        assert original["TS_PriorG"] != gt
        oraclejob = histjobs[pid]
        oracle = parsed(oraclejob, oldterm[oraclejob["request_id"]]["transport"])
        assert oracle["status"] == "valid" and oracle["pg"] == gt
        conditions = {"baseline_historical": {"status": "valid", "raw": original["TS_raw"], "pg": original["TS_PriorG"]}, "oracle_historical": oracle}
        for arm in ("baseline_repeat", "oracle_repeat", "add_only", "delete_only", "combined_header"):
            job = new_by_key.get((pid, arm))
            if job is None:
                conditions[arm] = {"status": "not_constructable_or_identical"}
            else:
                conditions[arm] = parsed(job, newterm[job["request_id"]]["transport"] if job["request_id"] in newterm else None)
        rows.append({"id": pid, "sid": shape["sid"], "GT": gt, "conditions": conditions,
                     "add_only_chars": shape["add_only_chars"], "baseline_chars": shape["baseline_chars"],
                     "new_oracle_n": len(shape["missing_ids"]), "intersection_n": len(set(shape["baseline_ids"]) & set(shape["oracle_ids"]))})
    with (OUT / "stage1_results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    counts = {}
    for arm in ("baseline_repeat", "oracle_repeat", "add_only", "delete_only", "combined_header"):
        available = [row for row in rows if row["conditions"][arm]["status"] == "valid"]
        counts[arm] = {"valid": len(available), "pg_correct": sum(row["conditions"][arm]["pg"] == row["GT"] for row in available), "raw_correct": sum(row["conditions"][arm]["raw"] == row["GT"] for row in available), "patients_pg_correct": len({row["sid"] for row in available if row["conditions"][arm]["pg"] == row["GT"]})}
    state, _ = run069.state()
    summary = {"cases": len(rows), "patients": len({row["sid"] for row in rows}), "arm_counts": counts,
               "baseline_repeat_self_flip_pg": sum(row["conditions"]["baseline_repeat"].get("pg") != row["conditions"]["baseline_historical"]["pg"] for row in rows),
               "oracle_repeat_self_flip_pg": sum(row["conditions"]["oracle_repeat"].get("pg") != row["conditions"]["oracle_historical"]["pg"] for row in rows),
               "api_attempts": len(state), "http200": sum(row["http_status"] == 200 for row in state), "occupied_cny": sum(row["cost"] for row in state), "cap_cny": 8.0,
               "positive_arm_case_count": sum(row["conditions"][arm].get("pg") == row["GT"] for row in rows for arm in ("add_only", "delete_only", "combined_header"))}
    (OUT / "stage1_analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
