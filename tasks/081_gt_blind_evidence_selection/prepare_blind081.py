"""Freeze Stage 1/2 IDs and U planner requests without opening any labels or predictions."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import blind081 as b
import selector081 as s


def write_once(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(content)


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def rows_text(rows):
    return "".join(dump(x) + "\n" for x in rows)


def h(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    eligible, corpora, exposed, by_file, patients = b.load()
    sample, manifest = [], []
    for sid in sorted(patients):
        pool = [x for x in eligible.values() if x["sid"] == sid]
        pool.sort(key=lambda x: (x["id"] in exposed, h("081/sample/v1:" + x["id"]), x["id"]))
        assert len(pool) >= 8, (sid, len(pool))
        for rank, item in enumerate(pool[:8]):
            pid = item["id"]
            stage = 1 if rank < 4 else 2
            candidates = []
            for j, passage_id in enumerate(item["C48"], 1):
                p = corpora[item["source"]][passage_id]
                candidates.append({"short_id": f"C{j:02d}", "passage_id": passage_id,
                                   "note_id": p["note_id"], "date": p["date"], "time": p["time"],
                                   "category": p["category"], "start": p["start"],
                                   "end_exclusive": p["end_exclusive"], "text": p["text"]})
            sample.append({"id": pid, "sid": sid, "stage": stage, "rank": rank + 1,
                           "author": item["author"], "claim": item["claim"], "source": item["source"],
                           "admission": item["admission"], "baseline_reference": item["baseline_reference"],
                           "baseline_ids": item["baseline_ids"], "baseline_source": item["baseline_source"],
                           "candidates": candidates, "previously_exposed": pid in exposed})
            manifest.append({"id": pid, "sid": sid, "stage": stage, "rank": rank + 1,
                             "source": item["source"], "previously_exposed": pid in exposed,
                             "blind_exposure_files": [path for path, ids in by_file.items() if pid in ids]})
    assert len(sample) == 192 and len({x["id"] for x in sample}) == 192
    jobs = []
    for item in sample:
        if item["stage"] == 1:
            body = s.plan_body(item["claim"])
            jobs.append({"request_id": "081_s1_U_plan_" + item["id"], "id": item["id"],
                         "stage": "U_plan", "body": body, "body_sha256": b.digest(body)})
    src_paths = sorted({p for group in b.SOURCES.values() for p in group} | set(b.BASELINES)
                       | set(b.EXPOSED_BLIND) | {"outputs/078_component_ablation/primary_blind.jsonl"})
    freeze = {"status": "SAMPLE_AND_U_PLAN_FROZEN_BEFORE_GT_AND_API", "stage1_n": 96,
              "stage2_reserved_n": 96, "patient_n": 24,
              "sample_rule": "new first, then sha256(081/sample/v1:id); first 4 stage1, next 4 stage2",
              "source_sha256": {p: b.sha(b.ROOT / p) for p in src_paths},
              "protocol_sha256": b.sha(Path(__file__).with_name("protocol.md")),
              "selector_sha256": b.sha(Path(__file__).with_name("selector081.py")),
              "blind_code_sha256": b.sha(Path(__file__).with_name("blind081.py")),
              "stage1_new_n": sum(not x["previously_exposed"] and x["stage"] == 1 for x in sample),
              "stage2_new_n": sum(not x["previously_exposed"] and x["stage"] == 2 for x in sample),
              "source_counts": dict(Counter(x["source"] for x in sample if x["stage"] == 1)),
              "sample_blind_sha256": h(rows_text(sample)),
              "overlap_manifest_sha256": h(rows_text(manifest)),
              "u_plan_jobs_sha256": h(rows_text(jobs))}
    out = b.OUT
    write_once(out / "sample_blind.jsonl", rows_text(sample))
    write_once(out / "overlap_manifest.jsonl", rows_text(manifest))
    write_once(out / "u_plan_jobs.jsonl", rows_text(jobs))
    write_once(out / "sample_freeze.json", dump(freeze) + "\n")
    print(dump({"stage1": 96, "stage2_reserved": 96, "new_stage1": freeze["stage1_new_n"],
                "source_counts": freeze["source_counts"]}))


if __name__ == "__main__":
    main()
