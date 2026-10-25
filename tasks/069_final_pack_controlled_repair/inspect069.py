"""Read-only feasibility audit for 066 C48 oracle factorial controls."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
from build_stage3_066 import CORPUS_PATH  # noqa: E402
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c67  # noqa: E402


def read_jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def match(blocks, ids, corpus):
    mapped, used = [], set()
    for block in blocks:
        found = None
        for pid in ids:
            if pid in used or pid not in corpus:
                continue
            text = c67.norm(corpus[pid].get("text", ""))
            if block == text or block in text or text in block:
                found = pid
                break
        if found is None:
            return None
        mapped.append(found)
        used.add(found)
    return mapped


def main():
    evidence = list(csv.DictReader((ROOT / "outputs/066_oracle_headroom/evidence_cases.csv").open(encoding="utf-8-sig", newline="")))
    target = {row["id"] for row in evidence if row["evidence_fix"] == "True" and row["kept_all_in_c48"] == "True"}
    assert len(target) == 10
    cases = {x["id"]: x for x in read_jsonl(ROOT / "outputs/066_oracle_headroom/error_cases.jsonl")}
    oracle = {x["id"]: x for x in read_jsonl(ROOT / "outputs/066_oracle_headroom/final_mapping.jsonl")}
    corpora = {name: {x["passage_id"]: x for x in read_jsonl(path)} for name, path in CORPUS_PATH.items()}
    rows = []
    for pid in sorted(target):
        case, mapped = cases[pid], oracle[pid]
        corpus = corpora[case["corpus_source"]]
        blocks = c67.reference_blocks(case["baseline_reference"])
        original_ids = match(blocks, case["c48_pids"], corpus)
        selected = mapped["kept_pids"]
        same = (original_ids is not None and c.build_reference(original_ids, corpus, max_chars=100000, max_items=100)[0] == case["baseline_reference"])
        overlap = len(set(original_ids or []) & set(selected))
        union_ids = list(dict.fromkeys((original_ids or []) + selected))
        union_reference, union_kept, _ = c.build_reference(union_ids, corpus, max_chars=100000, max_items=100)
        oracle_reference, oracle_kept, _ = c.build_reference(selected, corpus, max_chars=100000, max_items=100)
        rows.append({
            "id": pid, "GT": case["GT"], "sid": case["sid"], "source": case["corpus_source"],
            "baseline_blocks": len(blocks), "baseline_mapped": original_ids is not None,
            "baseline_ids": original_ids, "baseline_rebuilt_exact": same,
            "oracle_kept_n": len(selected), "oracle_in_c48": all(x in case["c48_pids"] for x in selected),
            "oracle_rebuilt_exact": oracle_reference == mapped["reference"],
            "intersection_n": overlap, "new_oracle_n": len(set(selected) - set(original_ids or [])),
            "baseline_chars": len(case["baseline_reference"]), "union_chars": len(union_reference),
            "oracle_chars": len(mapped["reference"]),
            "union_n": len(union_kept),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "preflight_cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "target_n": len(rows), "mapped_baseline": sum(row["baseline_mapped"] for row in rows),
        "rebuilt_baseline_exact": sum(row["baseline_rebuilt_exact"] for row in rows),
        "rebuilt_oracle_exact": sum(row["oracle_rebuilt_exact"] for row in rows),
        "all_oracle_in_c48": all(row["oracle_in_c48"] for row in rows),
        "no_intersection": sum(row["intersection_n"] == 0 for row in rows),
        "mean_baseline_chars": sum(row["baseline_chars"] for row in rows) / len(rows),
        "mean_union_chars": sum(row["union_chars"] for row in rows) / len(rows),
        "case_shapes": [{key: row[key] for key in ("id", "GT", "baseline_blocks", "oracle_kept_n", "intersection_n", "new_oracle_n", "baseline_mapped", "baseline_rebuilt_exact", "oracle_rebuilt_exact", "baseline_chars", "union_chars")} for row in rows],
    }
    (OUT / "preflight.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
