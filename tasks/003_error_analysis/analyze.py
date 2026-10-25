"""Small error exploration; no inference or automatic clinical attribution."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.audit.common import (LABELS, digest_file, digest_text, integer_id,
                                            new_run, read_csv, write_csv, write_json)
from verifact_research.evaluation.core import evaluate

RAW = ROOT / "data/00_raw/verifact-bhc/1.1.0"
OUT = ROOT / "outputs/003_error_analysis"
FORMAL = ROOT / "outputs/002_reproduce_paper_results/run_003"
SPLIT_SEED = "003_error_analysis/patient-split/v1:"
CASE_SEED = "003_error_analysis/case-selection/v1:"
MODELS = {"R1-70B": "v1.1.0-rater-121",
          "Qwen-3-30B-A3B-Thinking": "v1.1.0-rater-056"}
csv.field_size_limit(50_000_000)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def split_patients(subjects: list[str], exposed: list[str]) -> dict:
    require(len(subjects) == 100 and len(set(subjects)) == 100, "Expected 100 distinct patients")
    require(len(set(exposed)) == len(exposed) and set(exposed) <= set(subjects), "Invalid exposure IDs")
    require(len(exposed) <= 20, "Prior exposure exceeds exploration budget")
    rank = lambda x: (digest_text(SPLIT_SEED + x), x)
    remaining = sorted(set(subjects) - set(exposed), key=rank)
    groups = {"exploration": sorted(exposed + remaining[:20-len(exposed)], key=int),
              "development": sorted(remaining[20-len(exposed):60-len(exposed)], key=int),
              "reserved_test": sorted(remaining[60-len(exposed):], key=int)}
    require([len(x) for x in groups.values()] == [20, 40, 40], "Bad group sizes")
    return groups


def freeze(exposed: list[str]) -> None:
    OUT.mkdir(exist_ok=True, parents=True)
    path = OUT / "patient_groups.json"
    source = RAW / "reference_ehr/subject_ids.txt"
    subjects = [integer_id(x.strip()) for x in source.read_text().split(",")]
    groups = split_patients(subjects, exposed)
    write_json(path, dict(groups=groups, previously_viewed=sorted(exposed, key=int),
        seed=SPLIT_SEED, method="force previously viewed into exploration; SHA256(seed + canonical ID)",
        frozen_utc=datetime.now(timezone.utc).isoformat(), source_sha256=digest_file(source),
        exposure_note="Known prior detailed case guide and earlier displayed BHC; 001/002 whole-release aggregates already seen. Future isolation only; no outcome-based split selection."))
    print(json.dumps({"partition": str(path.relative_to(ROOT)), "counts": {k: len(v) for k, v in groups.items()}, "sha256": digest_file(path)}))


def load_split() -> dict:
    split = json.loads((OUT / "patient_groups.json").read_text(encoding="utf-8"))
    source = RAW / "reference_ehr/subject_ids.txt"
    require(digest_file(source) == split["source_sha256"], "Patient source changed")
    subjects = [integer_id(x.strip()) for x in source.read_text().split(",")]
    require(split["seed"] == SPLIT_SEED and split["groups"] == split_patients(subjects, split["previously_viewed"]), "Partition changed")
    return split


def subset_csv(path: Path, key: str, allowed: set[str], numeric: bool = False) -> list[dict]:
    """Sequential local scan; only permitted rows retained, no held-out texts exported."""
    opener = gzip.open if path.suffix == ".gz" else open
    selected = []
    with opener(path, "rt", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            value = integer_id(row[key]) if numeric else row[key]
            if value in allowed:
                require(None not in row and all(v is not None for v in row.values()), "Ragged CSV")
                selected.append(row)
    return selected


def select_cases(rows: list[dict], author: str) -> list[dict]:
    """Prespecified error-cell sample and three label-matched correct controls."""
    pool = [r for r in rows if r["author_type"] == author]
    chosen, used = [], Counter()
    cells = {(a, b): sorted([r for r in pool if (r["human_gt"], r["baseline_verdict"]) == (a, b)],
                            key=lambda r: digest_text(CASE_SEED + r["proposition_id"]))
             for a in LABELS for b in LABELS}

    def take(cell: tuple, reason: str) -> bool:
        existing = {r["proposition_id"] for r in chosen}
        candidates = [r for r in cells[cell] if r["proposition_id"] not in existing]
        if not candidates:
            return False
        capped = [r for r in candidates if used[r["subject_id"]] < 2]
        selected = dict((capped or candidates)[0])
        selected.update(selection_reason=reason, patient_cap_relaxed=not bool(capped))
        used[selected["subject_id"]] += 1
        chosen.append(selected)
        return True

    off = [(a, b) for a in LABELS for b in LABELS if a != b]
    for cell in off:
        take(cell, "initial: one per available error cell")
    while len(chosen) < 9:
        before = len(chosen)
        for cell in sorted(off, key=lambda x: (-len(cells[x]), x)):
            if len(chosen) >= 9:
                break
            take(cell, "initial: fill error budget in descending cell-size rounds")
        if len(chosen) == before:
            break
    for a in LABELS:
        take((a, a), "initial: one correct control per available GT class")
    for i, row in enumerate(chosen, 1):
        row["case_id"] = ("L" if author == "llm" else "H") + f"{i:02d}"
    return chosen


def extract() -> None:
    split = load_split()
    exploration = set(split["groups"]["exploration"])
    formal_manifest = json.loads((FORMAL / "manifest.json").read_text(encoding="utf-8"))
    # Historical result provides frozen metadata and flags; verify its bytes first.
    output_hashes = formal_manifest["output_sha256"]
    master = FORMAL / "cohort_master.csv"
    require(digest_file(master) == output_hashes["cohort_master.csv"], "002 formal cohort changed")
    cohort = subset_csv(master, "subject_id", exploration)
    atomic = [r for r in cohort if r["proposition_type"] == "claim"]
    excluded = [r for r in atomic if r["invalid"] == "True"]
    valid = [r for r in atomic if r["invalid"] == "False"]
    require(len(valid) + len(excluded) == len(atomic), "Unexpected validity value")
    run = new_run(OUT, None, ROOT / "data/00_raw")
    inputs = ["propositions/propositions.csv.gz", "propositions/human_verdicts.csv.gz",
              "propositions/proposition_validity.csv.gz", "reference_ehr/ehr_noteevents.csv.gz",
              "reference_ehr/admissions.csv.gz", "verifact/verdicts.parquet",
              "verifact/reference_payloads.parquet", "verifact/rater_configurations.csv",
              "verifact/experiment_matrix.csv"]
    before = {p: digest_file(RAW / p) for p in inputs}
    require(all(before[p] == formal_manifest["input_sha256"][p] for p in inputs), "Raw inputs differ from 002")
    con = duckdb.connect()
    con.register("selected_ids", pd.DataFrame({"proposition_id": [r["proposition_id"] for r in valid]}))
    frame = con.execute("SELECT v.* FROM read_parquet(?) v JOIN selected_ids USING(proposition_id) WHERE v.rater_alias IN (?, ?)",
                        [str(RAW / "verifact/verdicts.parquet"), *MODELS.values()]).fetchdf()
    pred = frame.where(pd.notna(frame), None).to_dict("records")
    pred_index = {(r["model"], r["proposition_id"]): r for r in pred}
    require(len(pred_index) == len(pred) == 2 * len(valid), "Incomplete or duplicate model predictions")
    configurations = {r["model"]: r for r in read_csv(RAW / "verifact/rater_configurations.csv")[1] if r["rater_alias"] in MODELS.values()}
    for model, config in configurations.items():
        require(config["rater_alias"] == MODELS[model] and config["fact_type"] == "sentence" and config["top_n"] == "100"
                and config["retrieval_method"] == "rerank" and config["reference_format"] == "absolute_time"
                and config["reference_only_admission"] == config["deduplicate_text"] == "True", "Baseline configuration changed")
    require(set(configurations) == set(MODELS), "Missing configuration")
    metrics, candidates = {}, []
    for author in ("llm", "human"):
        rows = [r for r in valid if r["author_type"] == author]
        write_csv(run / f"cohort_{author}_claim_valid.csv", rows)
        metrics[author] = {}
        for model in MODELS:
            pp = [{"proposition_id": r["proposition_id"], "verdict": pred_index[model, r["proposition_id"]]["verdict"]} for r in rows]
            metrics[author][model] = evaluate(rows, pp, profile="none")
            write_csv(run / f"predictions_{model}_{author}.csv", pp)
        for r in rows:
            a, b = [pred_index[model, r["proposition_id"]] for model in MODELS]
            candidates.append(dict(r, baseline_verdict=a["verdict"], comparator_verdict=b["verdict"],
                                   baseline_reference_id=a["reference_id"], comparator_reference_id=b["reference_id"],
                                   exact_same_reference=a["reference_id"] == b["reference_id"]))
    write_csv(run / "excluded_invalid.csv", excluded, list(cohort[0]))
    write_csv(run / "candidate_index.csv", candidates)
    selected = select_cases(candidates, "llm") + select_cases(candidates, "human")
    write_csv(run / "selected_cases.csv", selected)
    selected_ids = {r["proposition_id"] for r in selected}
    props = {r["proposition_id"]: r for r in subset_csv(RAW / "propositions/propositions.csv.gz", "proposition_id", selected_ids)}
    human = {r["proposition_id"]: r for r in subset_csv(RAW / "propositions/human_verdicts.csv.gz", "proposition_id", selected_ids)}
    validity = {r["proposition_id"]: r for r in subset_csv(RAW / "propositions/proposition_validity.csv.gz", "proposition_id", selected_ids)}
    refs = {pred_index[m, pid]["reference_id"] for pid in selected_ids for m in MODELS}
    con.register("reference_ids", pd.DataFrame({"reference_id": sorted(refs)}))
    payloads = dict(con.execute("SELECT r.reference_id, r.reference FROM read_parquet(?) r JOIN reference_ids USING(reference_id)",
                               [str(RAW / "verifact/reference_payloads.parquet")]).fetchall())
    require(set(payloads) == refs and all(digest_text(text) == rid for rid, text in payloads.items()), "Reference identity mismatch")
    (run / "cases").mkdir()
    for selected_row in selected:
        pid = selected_row["proposition_id"]
        require(integer_id(props[pid]["subject_id"]) in exploration and human[pid]["human_gt"] == selected_row["human_gt"], "Case identity mismatch")
        require(props[pid]["text"] == human[pid]["text"] == validity[pid]["text"] and validity[pid]["invalid"] == "False", "Case definition mismatch")
        models = {m: dict(pred_index[m, pid], reference=payloads[pred_index[m, pid]["reference_id"]], configuration=configurations[m]) for m in MODELS}
        write_json(run / "cases" / f"{selected_row['case_id']}.json", dict(selection=selected_row, proposition=props[pid], human=human[pid], validity=validity[pid], models=models))
    case_subjects = {r["subject_id"] for r in selected}
    notes = subset_csv(RAW / "reference_ehr/ehr_noteevents.csv.gz", "SUBJECT_ID", case_subjects, numeric=True)
    admissions = subset_csv(RAW / "reference_ehr/admissions.csv.gz", "SUBJECT_ID", case_subjects, numeric=True)
    write_json(run / "ehr_notes.json", notes)
    write_json(run / "admissions.json", admissions)
    write_json(run / "patient_groups_snapshot.json", split)
    write_json(run / "metrics.json", metrics)
    summary = dict(exploration_patients=len(exploration), inspected_case_patients=len(case_subjects),
        valid_atomic_claims=len(valid), excluded_invalid_atomic_claims=len(excluded), cases=len(selected),
        case_counts=dict(Counter((r["author_type"] + "/" + ("correct" if r["human_gt"] == r["baseline_verdict"] else "error")) for r in selected)),
        case_patient_cap_relaxations=sum(r["patient_cap_relaxed"] for r in selected),
        initial_error_cells={a: {f"{g} -> {p}": sum(r["author_type"] == a and r["human_gt"] == g and r["baseline_verdict"] == p for r in candidates) for g in LABELS for p in LABELS} for a in ("llm", "human")},
        boundary_counts={a: {flag: sum(r["author_type"] == a and r[flag] == "True" for r in valid) for flag in ("time_metadata_conflict", "second_round_anomaly")} for a in ("llm", "human")})
    write_json(run / "summary.json", summary)
    require(before == {p: digest_file(RAW / p) for p in inputs}, "Raw input changed during extraction")
    write_json(run / "manifest.json", dict(created_utc=datetime.now(timezone.utc).isoformat(),
        source_001="outputs/001_dataset_audit/run_006", source_002=str(FORMAL.relative_to(ROOT)),
        raw_input_sha256=before, raw_unchanged=True, partition_sha256=digest_file(OUT / "patient_groups.json"),
        cohort_master_sha256=digest_file(master), script_sha256=digest_file(Path(__file__)),
        baseline_configs=configurations, all_case_subjects_in_exploration=case_subjects <= exploration,
        output_sha256={str(p.relative_to(run)).replace('\\', '/'): digest_file(p) for p in sorted(run.rglob("*")) if p.is_file()}))
    print(json.dumps({"run": str(run.relative_to(ROOT)), **summary}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subs.add_parser("freeze", help="First-time partition only; refuses to overwrite")
    freeze_parser.add_argument("--previously-viewed", nargs="+", required=True)
    subs.add_parser("extract", help="Re-extract fixed exploratory sample into a new local run")
    args = parser.parse_args()
    freeze(args.previously_viewed) if args.command == "freeze" else extract()
