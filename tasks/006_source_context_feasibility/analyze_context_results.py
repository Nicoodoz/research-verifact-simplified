"""Offline descriptive diagnostics and traceable full-output review packets for 006."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import context_feasibility as cf


def reference_blocks(text):
    matches = list(re.finditer(r"(?m)^(\d+)\. Date: ", text))
    return [(int(m.group(1)), text[m.end()-len("Date: "):matches[i+1].start() if i+1 < len(matches) else len(text)].rstrip())
        for i, m in enumerate(matches)]


def outcome(row, baseline, candidate):
    before, after, truth = row[baseline], row[candidate], row["human_gt"]
    if not before or not after:
        return "missing_pair"
    if before != truth == after:
        return "improved_original_GT"
    if before == truth != after:
        return "degraded_original_GT"
    if before != after:
        return "changed_both_wrong"
    return "unchanged_correct" if before == truth else "unchanged_wrong"


def build(prep, run, output):
    rows = cf.pilot.read_csv(run / "analysis/transitions.csv")[1]
    inputs = {r["proposition_id"]: r for r in cf.pilot.jsonl(prep / "inputs.jsonl")}
    responses = {(r["proposition_id"], r["arm"]): r for r in cf.pilot.jsonl(run / "analysis/normalized_responses.jsonl")}
    for i, row in enumerate(rows):
        row.update(case_id=f"N{i+1:02d}", primary_outcome=outcome(row, "structured", "source_context"),
            control_outcome=outcome(row, "repeat_claim", "source_context"))
        # Review all disagreements (including repeat-only effects) and all failures.
        row["review_selection"] = "all_arm_disagreements_or_failures" if len({row[a] for a in cf.ARMS}) > 1 or not all(row[a] for a in cf.ARMS) else ""
    # Fixed hash controls from each author x stable-correct/wrong cell, at most 2 per cell.
    for author in ("llm", "human"):
        for correct in (True, False):
            candidates = [r for r in rows if r["author_type"] == author and not r["review_selection"]
                and (r["structured"] == r["human_gt"]) == correct]
            for row in sorted(candidates, key=lambda r: cf.pilot.digest_text("006/review-control/v1:" + r["proposition_id"]))[:2]:
                row["review_selection"] = "fixed_hash_stable_" + ("correct" if correct else "wrong")
    output.mkdir(parents=True, exist_ok=False)
    (output / "packets").mkdir()
    unions = defaultdict(dict)
    for row in rows:
        pid, cid = row["proposition_id"], row["case_id"]
        item = inputs[pid]
        answers = {a: responses.get((pid, a)) for a in cf.ARMS}
        cf.pilot.write_json(output / "packets" / (cid + ".json"), dict(case=row, input=item, responses=answers))
        if row["review_selection"]:
            for number, block in reference_blocks(item["reference"]):
                h = cf.pilot.digest_text(block)
                saved = unions[row["subject_id"]].setdefault(h, dict(block_id=h, text=block, uses=[]))
                saved["uses"].append(dict(case_id=cid, number=number))
    (output / "reference_unions").mkdir()
    for sid, union in unions.items():
        cf.pilot.write_json(output / "reference_unions" / (sid + ".json"), list(union.values()))
    cf.pilot.write_csv(output / "case_index.csv", rows)
    stats = dict(primary_comparison_incomplete=True, counts_are_descriptive_not_available_case_metrics=True,
        cohorts={}, review_selected=[r["case_id"] for r in rows if r["review_selection"]],
        selection_rule="All arm label disagreements/missing cases plus two fixed-hash stable-correct and stable-wrong cases per author; chosen before full-output reading; no outcome filtering",
        reference_unique_blocks={sid: len(u) for sid, u in unions.items()})
    for author in ("llm", "human"):
        part = [r for r in rows if r["author_type"] == author]
        stats["cohorts"][author] = dict(expected_n=len(part), primary_outcomes=dict(Counter(r["primary_outcome"] for r in part)),
            control_outcomes=dict(Counter(r["control_outcome"] for r in part)),
            verdict_counts_including_missing={a: dict(Counter(r[a] or "MISSING" for r in part)) for a in cf.ARMS})
    stats["arms"] = {}
    for arm in cf.ARMS:
        part = [r for r in responses.values() if r["arm"] == arm]
        stats["arms"][arm] = dict(received=len(part), valid=sum(r["status"] == "success" for r in part),
            adherence_flags=dict(Counter(e for r in part for e in r["adherence_errors"])),
            input_tokens=sum(r.get("usage", {}).get("input_tokens", 0) for r in part),
            output_tokens=sum(r.get("usage", {}).get("output_tokens", 0) for r in part),
            cache_hit_tokens=sum(r.get("usage", {}).get("cache_hit_tokens") or 0 for r in part),
            estimated_received_cost_cny=sum(r.get("cost", {}).get("cny", 0) for r in part),
            output_characters=sum(len(r.get("output_text") or "") for r in part))
    cf.pilot.write_json(output / "descriptive_statistics.json", stats)
    cf.pilot.write_json(output / "extraction_manifest.json", dict(code_sha256=cf.pilot.digest_file(Path(__file__)),
        preparation_manifest_sha256=cf.pilot.digest_file(prep / "manifest.json"),
        analysis_manifest_sha256=cf.pilot.digest_file(run / "analysis/manifest.json"),
        outputs_sha256={p.relative_to(output).as_posix(): cf.pilot.digest_file(p) for p in output.rglob("*") if p.is_file()}))
    print(cf.pilot.canonical(stats))


def read(output, cases, patient, start, count):
    if patient:
        blocks = json.loads((output / "reference_unions" / (patient + ".json")).read_text(encoding="utf-8"))
        for i, block in enumerate(blocks[start:start+count], start):
            print(f"[{patient} union {i}] " + json.dumps(block["uses"]))
            print(block["text"])
        print(f"END indices {start}..{min(start+count,len(blocks))-1}; total {len(blocks)}")
    else:
        for cid in cases:
            packet = json.loads((output / "packets" / (cid + ".json")).read_text(encoding="utf-8"))
            print("\n" + cid + " " + json.dumps(packet["case"], ensure_ascii=False))
            print("CLAIM: " + packet["input"]["text"])
            print("UNVERIFIED SOURCE: " + packet["input"]["source_context"]["text"])
            for arm, response in packet["responses"].items():
                print(arm + ": " + (response.get("output_text", "NO OUTPUT") if response else "NO RESPONSE"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "read"])
    parser.add_argument("--preparation", type=Path, default=cf.OUT / "preparation_001")
    parser.add_argument("--run", type=Path, default=cf.OUT / "run_001")
    parser.add_argument("--output", type=Path, default=cf.OUT / "run_001/review_001")
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--patient")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()
    if args.mode == "build":
        build(args.preparation, args.run, args.output)
    else:
        read(args.output, args.cases, args.patient, args.start, args.count)
