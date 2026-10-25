"""Read-only audit of 067's actual frozen intervention, with no API calls."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P067 = ROOT / "outputs/067_conservative_evidence_packing"
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
CORPUS = {
    "031": ROOT / "outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
    "020": ROOT / "outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
    "009": ROOT / "outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl",
}


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("\\n", " ")).strip().lower()


def blocks(ref):
    out = []
    for part in re.split(r"(?:^|\n|\\n)\d+\. Date:", ref)[1:]:
        if "| Text:" in part:
            out.append(norm(part.split("| Text:", 1)[1]))
    return out


def main():
    cases = {x["id"]: x for x in jsonl(P067 / "cases_blind.jsonl")}
    mapping = {x["id"]: x for x in jsonl(P067 / "pack_mapping.jsonl")}
    results = {x["id"]: x for x in csv.DictReader((P067 / "results.csv").open(encoding="utf-8-sig", newline=""))}
    audit_jobs = {x["id"]: x for x in jsonl(P067 / "stage1_jobs.jsonl")}
    judge_jobs = {x["id"]: x for x in jsonl(P067 / "stage2_jobs.jsonl")}
    corp = {src: {x["passage_id"]: x for x in jsonl(path)} for src, path in CORPUS.items()}
    assert len(cases) == len(mapping) == len(results) == 236
    assert len(audit_jobs) == 227 and len(judge_jobs) == 226
    assert all(not x["baseline_pids"] and not x.get("baseline_short_ids") for x in cases.values())
    assert all(json.loads(job["body"]["messages"][1]["content"])["current_pack_ids"] == [] for job in audit_jobs.values())
    rows = []
    for pid, x in cases.items():
        mp, res = mapping[pid], results[pid]
        old_blocks, new_blocks = blocks(x["baseline_reference"]), blocks(mp["final_reference"])
        assert 1 <= len(old_blocks) <= 20
        if mp["changed"]:
            assert len(new_blocks) == len(mp["added_pids"])
            assert mp["dropped_pids"] == []
            payload = json.loads(judge_jobs[pid]["body"]["messages"][1]["content"])
            assert payload == {"proposition": x["claim"], "reference": mp["final_reference"]}
        else:
            assert mp["final_reference"] == x["baseline_reference"]
        original_norm = norm(x["baseline_reference"])
        passage_status = []
        for passage_id in mp["added_pids"]:
            passage = norm(corp[x["source"]][passage_id]["text"])
            exact = bool(passage and passage in original_norm)
            # Long verbatim fragments allow for partial formatting/truncation differences.
            fragment = bool(len(passage) >= 100 and passage[:100] in original_norm)
            passage_status.append({"pid": passage_id, "full_text_in_old": exact, "first_100_chars_in_old": fragment})
        old_norm_blocks = set(old_blocks)
        new_norm_blocks = set(new_blocks)
        old_present = sum(item in new_norm_blocks for item in old_blocks)
        new_present = sum(item in old_norm_blocks for item in new_blocks)
        old_ok = res["baseline_pg"] == res["GT"]
        new_ok = res["new_pg"] == res["GT"]
        group = "rescue" if not old_ok and new_ok else "harm" if old_ok and not new_ok else "unchanged"
        rows.append({
            "id": pid, "sid": res["sid"], "author": res["author"], "GT": res["GT"], "group": group,
            "changed": bool(mp["changed"]), "source": x["source"],
            "baseline_pids_n": len(x["baseline_pids"]),
            "baseline_blocks_n": len(old_blocks), "final_blocks_n": len(new_blocks),
            "original_blocks_exactly_in_final_n": old_present,
            "final_blocks_exactly_in_original_n": new_present,
            "added_passages_n": len(passage_status),
            "added_passages_full_text_in_original_n": sum(z["full_text_in_old"] for z in passage_status),
            "added_passages_first_100_in_original_n": sum(z["first_100_chars_in_old"] for z in passage_status),
            "baseline_raw": res["baseline_raw"], "new_raw": res["new_raw"],
            "baseline_pg": res["baseline_pg"], "new_pg": res["new_pg"],
            "addition_roles": mp["addition_roles"],
        })
    changed = [row for row in rows if row["changed"]]
    summary = {
        "n": len(rows), "changed": len(changed),
        "all_baseline_pids_empty": all(row["baseline_pids_n"] == 0 for row in rows),
        "all_audit_current_pack_ids_empty": True,
        "baseline_block_histogram": dict(Counter(row["baseline_blocks_n"] for row in changed)),
        "final_block_histogram": dict(Counter(row["final_blocks_n"] for row in changed)),
        "mean_baseline_blocks": sum(row["baseline_blocks_n"] for row in changed) / len(changed),
        "mean_final_blocks": sum(row["final_blocks_n"] for row in changed) / len(changed),
        "changed_with_any_original_block_retained": sum(row["original_blocks_exactly_in_final_n"] > 0 for row in changed),
        "changed_with_all_original_blocks_retained": sum(row["original_blocks_exactly_in_final_n"] == row["baseline_blocks_n"] for row in changed),
        "added_passages": sum(row["added_passages_n"] for row in changed),
        "added_passages_full_text_already_in_original": sum(row["added_passages_full_text_in_original_n"] for row in changed),
        "added_passages_first_100_already_in_original": sum(row["added_passages_first_100_in_original_n"] for row in changed),
        "group_histogram": dict(Counter(row["group"] for row in changed)),
        "judges_body_matches_frozen_mapping": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "forensic_cases.jsonl").open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (OUT / "forensics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
