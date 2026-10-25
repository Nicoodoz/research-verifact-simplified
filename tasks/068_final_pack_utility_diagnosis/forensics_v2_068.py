"""Read-only independent shape audit for 067's v2 branch."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P067 = ROOT / "outputs/067_conservative_evidence_packing"
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def norm(text):
    return re.sub(r"\s+", " ", str(text).replace("\\n", " ")).strip().lower()


def blocks(ref):
    return [norm(part.split("| Text:", 1)[1]) for part in re.split(r"(?:^|\n|\\n)\d+\. Date:", ref)[1:] if "| Text:" in part]


def main():
    cases = {x["id"]: x for x in jsonl(P067 / "cases_blind_v2.jsonl")}
    mapping = {x["id"]: x for x in jsonl(P067 / "pack_mapping_v2.jsonl")}
    audits = {x["id"]: x for x in jsonl(P067 / "stage1v2_jobs.jsonl")}
    judge = {x["id"]: x for x in jsonl(P067 / "stage2v2_jobs.jsonl")}
    results = {x["id"]: x for x in csv.DictReader((P067 / "results_v2.csv").open(encoding="utf-8-sig", newline=""))}
    assert len(cases) == len(mapping) == len(results) == 236
    assert len(audits) == 225 and len(judge) == 27
    rows = []
    for pid, case in cases.items():
        mp, res = mapping[pid], results[pid]
        old, new = blocks(case["baseline_reference"]), blocks(mp["final_reference"])
        assert 10 <= len(old) <= 16
        if case["mapped"]:
            assert len(case["baseline_pids"]) == len(old)
            assert json.loads(audits[pid]["body"]["messages"][1]["content"])["current_pack_ids"] == case["baseline_short_ids"]
        if mp["changed"]:
            assert pid in judge
            assert len(new) == len(old) + len(mp["added_pids"]) - len(mp["dropped_pids"])
            payload = json.loads(judge[pid]["body"]["messages"][1]["content"])
            assert payload == {"proposition": case["claim"], "reference": mp["final_reference"]}
        else:
            assert mp["final_reference"] == case["baseline_reference"]
        old_set, new_set = set(old), set(new)
        group = "rescue" if res["rescue"] == "True" else "harm" if res["harm"] == "True" else "unchanged"
        rows.append({
            "id": pid, "sid": str(res.get("sid") or case["sid"]), "author": res.get("author") or case["author"],
            "GT": res["GT"], "group": group, "mapped": case["mapped"], "changed": bool(mp["changed"]),
            "baseline_blocks_n": len(old), "final_blocks_n": len(new),
            "baseline_pids_n": len(case["baseline_pids"]),
            "explicit_additions_n": len(mp["added_pids"]), "explicit_drops_n": len(mp["dropped_pids"]),
            "original_blocks_exactly_retained_n": sum(block in new_set for block in old),
            "final_blocks_in_original_n": sum(block in old_set for block in new),
            "linebreak_literals_n": mp["final_reference"].count("\\n"),
            "baseline_raw": res["baseline_raw"], "final_raw": res["final_raw"],
            "baseline_pg": res["baseline"], "final_pg": res["final"],
            "roles": mp["addition_roles"],
        })
    changed = [row for row in rows if row["changed"]]
    summary = {
        "n": len(rows), "mapped": sum(row["mapped"] for row in rows), "changed": len(changed),
        "mapped_baseline_pids_nonempty": all(row["baseline_pids_n"] > 0 for row in rows if row["mapped"]),
        "audit_current_pack_ids_match": True,
        "final_judge_request_matches_mapping": True,
        "baseline_blocks_total_mapped": sum(row["baseline_blocks_n"] for row in rows if row["mapped"]),
        "explicit_additions": sum(row["explicit_additions_n"] for row in changed),
        "explicit_drops": sum(row["explicit_drops_n"] for row in changed),
        "changed_mean_baseline_blocks": sum(row["baseline_blocks_n"] for row in changed) / len(changed),
        "changed_mean_final_blocks": sum(row["final_blocks_n"] for row in changed) / len(changed),
        "changed_with_literal_linebreak": sum(row["linebreak_literals_n"] > 0 for row in changed),
        "groups_changed": dict(Counter(row["group"] for row in changed)),
        "added_roles": dict(Counter(role for pid, mp in mapping.items() if mp["changed"] for role in mp["addition_roles"])),
    }
    with (OUT / "forensic_v2_cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (OUT / "forensics_v2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
