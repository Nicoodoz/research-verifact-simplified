"""Offline post-hoc analysis of the saved 004 structured/event comparison."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/005_pilot_effect_analysis"
SOURCE = ROOT / "outputs/004_event_alignment_pilot/run_003"
sys.path.insert(0, str(ROOT / "tasks/004_event_alignment_pilot"))
import analyze_live
import pilot

SEED = "005_pilot_effect_analysis/case-selection/v1:"
ARMS = ("structured", "event_alignment")


def outcome(gt, structured, event):
    if structured != gt == event:
        return "improved"
    if structured == gt != event:
        return "degraded"
    if structured != event:
        return "wrong_changed"
    return "both_correct" if structured == gt else "both_wrong"


def select_cases(rows):
    selected, patient_counts = [], Counter()
    def add(row, purpose):
        copy = dict(row, selection_purpose=purpose, case_id=f"C{len(selected)+1:02d}")
        selected.append(copy)
        patient_counts[row["subject_id"]] += 1
    for author in ("llm", "human"):
        for kind in ("improved", "degraded"):
            candidates = [r for r in rows if r["author_type"] == author and r["outcome"] == kind]
            used_cells, patients = set(), Counter()
            for _ in range(min(4, len(candidates))):
                row = min(candidates, key=lambda r: ((r["human_gt"], r["structured"], r["event_alignment"]) in used_cells,
                    patients[r["subject_id"]], r["selection_hash"]))
                add(row, author + "/" + kind + "/transition_then_patient_coverage")
                used_cells.add((row["human_gt"], row["structured"], row["event_alignment"]))
                patients[row["subject_id"]] += 1
                candidates.remove(row)
    for row in sorted((r for r in rows if r["outcome"] == "wrong_changed"), key=lambda r: r["selection_hash"]):
        add(row, "all_wrong_changed")
    for author in ("llm", "human"):
        for kind, positive in (("both_correct", True), ("both_correct", False), ("both_wrong", True)):
            candidates = [r for r in rows if r["author_type"] == author and r["outcome"] == kind
                and (r["human_gt"] == "Supported") == positive]
            row = min(candidates, key=lambda r: (patient_counts[r["subject_id"]], r["selection_hash"]))
            add(row, f"control/{author}/{kind}/" + ("S" if positive else "non_S"))
    pilot.require(len({r["proposition_id"] for r in selected}) == len(selected), "Duplicate selected case")
    return selected


def reference_blocks(text):
    matches = list(re.finditer(r"(?m)^(\d+)\. Date: ", text))
    return [(int(m.group(1)), text[m.end()-len("Date: "):matches[i+1].start() if i+1 < len(matches) else len(text)].rstrip())
        for i, m in enumerate(matches)]


def extract():
    config, cohort, terminal, _, checks, receipt_hashes = analyze_live.collect(SOURCE)
    inputs = {r["proposition_id"]: r for r in pilot.jsonl(SOURCE / "inputs.jsonl")}
    responses = {(r["proposition_id"], r["arm"]): r for r in terminal if r["arm"] in ARMS}
    split = json.loads((ROOT / "outputs/003_error_analysis/patient_groups.json").read_text(encoding="utf-8"))
    pilot.require({r["subject_id"] for r in cohort} <= set(split["groups"]["development"]), "Outside development group")
    rows = []
    for r in cohort:
        pid = r["proposition_id"]
        answers = {a: responses[(pid, a)] for a in ARMS}
        pilot.require(all(v["status"] == "success" for v in answers.values()), "Incomplete primary comparison")
        rows.append(dict(r, **{a: answers[a]["verdict"] for a in ARMS},
            outcome=outcome(r["human_gt"], *(answers[a]["verdict"] for a in ARMS)),
            selection_hash=pilot.digest_text(SEED + pid), reference_id=inputs[pid]["reference_id"],
            **{a+"_strict_format": not bool(answers[a]["adherence_errors"]) for a in ARMS}))
    selected = select_cases(rows)
    run = pilot.new_run(OUT, None, ROOT / "data/00_raw")
    pilot.write_csv(run / "all_transitions.csv", rows)
    pilot.write_csv(run / "selected_cases.csv", selected)
    original = json.loads((SOURCE / "analysis/metrics.json").read_text(encoding="utf-8"))
    scores = {}
    for author in ("llm", "human"):
        c = [r for r in cohort if r["author_type"] == author]
        pp = {a: [dict(proposition_id=r["proposition_id"], verdict=responses[(r["proposition_id"], a)]["verdict"]) for r in c] for a in ARMS}
        scores[author] = dict(metrics={a: pilot.evaluate(c, pp[a], iterations=1000) for a in ARMS},
            contrast=pilot.paired_compare(c, pp[ARMS[0]], pp[ARMS[1]], iterations=1000))
        own = [r for r in rows if r["author_type"] == author]
        cells = Counter((r["human_gt"], r[ARMS[0]], r[ARMS[1]]) for r in own)
        scores[author]["contrast"].update(error_to_correct=sum(r["outcome"] == "improved" for r in own),
            correct_to_error=sum(r["outcome"] == "degraded" for r in own),
            transitions=[dict(gt=k[0], baseline=k[1], candidate=k[2], count=v) for k,v in sorted(cells.items())])
        for a in ARMS:
            pilot.require(scores[author]["metrics"][a] == original[author]["primary"]["metrics"][a], "004 metric mismatch")
        pilot.require(scores[author]["contrast"] == original[author]["primary"]["contrasts"]["event_alignment_minus_structured"], "004 contrast mismatch")
    pilot.write_json(run / "metrics.json", scores)
    for name, fields in (("transition_counts", ["author_type", "outcome", "human_gt", *ARMS]),
            ("patient_counts", ["subject_id", "author_type", "outcome"]),
            ("annotation_counts", ["author_type", "initial_agreement", "outcome"]),
            ("adherence_counts", ["author_type", "structured_strict_format", "event_alignment_strict_format", "outcome"])):
        counts = Counter(tuple(r[f] for f in fields) for r in rows)
        pilot.write_csv(run / (name + ".csv"), [dict(zip(fields, key), n=value) for key, value in sorted(counts.items())])
    duplicates = defaultdict(list)
    for r in rows:
        item = inputs[r["proposition_id"]]
        duplicates[(r["subject_id"], item["text"], item["reference_id"])].append(r)
    pilot.write_json(run / "exact_input_duplicates.json", [dict(subject_id=k[0], text=k[1], reference_id=k[2], rows=v)
        for k, v in duplicates.items() if len(v) > 1])
    packets = run / "packets"
    packets.mkdir()
    select_by_id = {r["proposition_id"]: r for r in selected}
    overview = []
    union = defaultdict(dict)
    for row in rows:
        pid = row["proposition_id"]
        if row["outcome"] in {"both_correct", "both_wrong"} and pid not in select_by_id:
            continue
        item = inputs[pid]
        selection = select_by_id.get(pid)
        name = selection["case_id"] if selection else "X_" + pid[:8]
        packet = dict(case_id=name, selected_for_deep_review=bool(selection), cohort=row, input=item,
            outputs={a: responses[(pid, a)] for a in ARMS})
        pilot.write_json(packets / (name + ".json"), packet)
        overview += [f"## {name} | {row['author_type']} {row['subject_id']} | {row['outcome']} | GT {row['human_gt']}",
            item["text"], *[a + ": " + responses[(pid, a)]["output_text"] for a in ARMS], ""]
        if selection:
            for number, block in reference_blocks(item["reference"]):
                key = pilot.digest_text(block)
                union[row["subject_id"]].setdefault(key, dict(text=block, occurrences=[]))["occurrences"].append(dict(case=name, number=number))
    (run / "outputs_overview.md").write_text("\n".join(overview), encoding="utf-8", newline="\n")
    (run / "reference_unions").mkdir()
    for sid, blocks in union.items():
        ordered = sorted(blocks.items(), key=lambda x: x[1]["text"])
        pilot.write_json(run / "reference_unions" / (sid + ".json"), [dict(block_id=h, **b) for h, b in ordered])
        lines = [f"# Patient {sid}: complete reference blocks for selected cases, exact-text deduplicated"]
        for h, b in ordered:
            lines += ["\n" + h[:10] + " | " + ", ".join(f"{o['case']}:{o['number']}" for o in b["occurrences"]), b["text"]]
        (run / "reference_unions" / (sid + ".md")).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    summary = dict(claims=len(rows), selected_cases=len(selected), changed=sum(r["structured"] != r["event_alignment"] for r in rows),
        outcome_counts={a: dict(Counter(r["outcome"] for r in rows if r["author_type"] == a)) for a in ("llm", "human")},
        selected_patients=sorted({r["subject_id"] for r in selected}), union_block_counts={s:len(b) for s,b in union.items()},
        source_004_primary_metrics_exactly_reproduced=True, api_calls=0, reserved_test_used=False)
    pilot.write_json(run / "summary.json", summary)
    source_paths = [SOURCE / "manifest.json", SOURCE / "analysis/manifest.json", SOURCE / "inputs.jsonl",
        SOURCE / "cohort_llm.csv", SOURCE / "cohort_human.csv", SOURCE / "analysis/metrics.json",
        ROOT / "outputs/003_error_analysis/patient_groups.json", TASK / "README.md"]
    pilot.write_json(run / "manifest.json", dict(stage="extraction_complete_pending_interpretation", selection_seed=SEED,
        sources_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in source_paths},
        receipts_verified_against_original_manifest=len(receipt_hashes), source_checks=checks,
        code_sha256=pilot.digest_file(Path(__file__)), outputs_sha256={p.relative_to(run).as_posix():pilot.digest_file(p) for p in run.rglob("*") if p.is_file()}))
    print(pilot.canonical(dict(run=str(run), **summary)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["extract"])
    parser.parse_args()
    extract()
