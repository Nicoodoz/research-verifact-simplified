"""Record reproducible local evidence searches; matches are not gold evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from analyze import OUT, MODELS, digest_text, integer_id, require, write_json


def facts(reference: str) -> list[dict]:
    starts = list(re.finditer(r"(?m)^\d+\. Date: ", reference))
    return [{"start": m.start(), "end": starts[i+1].start() if i+1 < len(starts) else len(reference),
             "quote": reference[m.start():starts[i+1].start() if i+1 < len(starts) else len(reference)]}
            for i, m in enumerate(starts)]


def compare_references(a: str, b: str) -> dict:
    def normalized(text: str) -> Counter:
        return Counter(re.sub(r"\s+", " ", re.sub(r"^\d+\. ", "", f["quote"])).strip() for f in facts(text))
    aa, bb = normalized(a), normalized(b)
    return dict(exact_equal=a == b, facts_a=sum(aa.values()), facts_b=sum(bb.values()),
                normalized_block_multiset_equal=aa == bb,
                only_a=list((aa-bb).elements()), only_b=list((bb-aa).elements()),
                definition="Remove fact numbering, collapse whitespace, retain date/time/category/description/text; multiset comparison, not clinical equivalence.")


def inspect(run: Path, case_id: str, pattern: str, limit: int) -> None:
    case = json.loads((run / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))
    subject = case["selection"]["subject_id"]
    hadm = case["selection"]["hadm_id"]
    regex = re.compile(pattern, re.I)
    result = dict(case_id=case_id, pattern=pattern, interpretation="Search candidates only; not validated medical evidence", references={}, ehr=[])
    print("\nCASE", case_id, "CLAIM", case["proposition"]["text"])
    for model in MODELS:
        ref = case["models"][model]
        hits = [dict(f, source_sha256=ref["reference_id"]) for f in facts(ref["reference"]) if regex.search(f["quote"])]
        result["references"][model] = hits
        # R1 text displayed by default; full comparator matches retained for inspection.
        if model == "R1-70B":
            print("REFERENCE MATCHES", len(hits))
            for f in hits[:limit]:
                print(f"REF[{f['start']}:{f['end']}]", f["quote"].strip())
    notes = json.loads((run / "ehr_notes.json").read_text(encoding="utf-8"))
    for n in notes:
        if integer_id(n["SUBJECT_ID"]) != subject:
            continue
        # Collapse overlapping windows, retain exact source text and offsets.
        spans = []
        for m in regex.finditer(n["TEXT"]):
            lo, hi = max(0, m.start()-220), min(len(n["TEXT"]), m.end()+260)
            if spans and lo <= spans[-1][1]:
                spans[-1] = (spans[-1][0], max(hi, spans[-1][1]))
            else:
                spans.append((lo, hi))
        for lo, hi in spans:
            result["ehr"].append(dict(row_id=n["ROW_ID"], subject_id=subject, hadm_id=integer_id(n["HADM_ID"]),
                target_admission=integer_id(n["HADM_ID"]) == hadm, chartdate=n["CHARTDATE"], charttime=n["CHARTTIME"],
                storetime=n["STORETIME"], category=n["CATEGORY"], description=n["DESCRIPTION"],
                start=lo, end=hi, quote=n["TEXT"][lo:hi], source_sha256=digest_text(n["TEXT"])))
    print("EHR MATCH WINDOWS", len(result["ehr"]))
    for n in result["ehr"][:limit]:
        print(f"NOTE {n['row_id']} [{n['start']}:{n['end']}] target={n['target_admission']} {n['charttime'] or n['chartdate']} {n['description']}\n{n['quote']}")
    paths = run / "searches"
    paths.mkdir(exist_ok=True)
    write_json(paths / f"{case_id}_{digest_text(pattern)[:12]}.json", result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", default="run_001")
    p.add_argument("--cases", nargs="+", required=True)
    p.add_argument("--pattern", required=True)
    p.add_argument("--limit", type=int, default=12)
    a = p.parse_args()
    require(Path(a.run).name == a.run, "Run must be a directory name")
    for cid in a.cases:
        inspect(OUT / a.run, cid, a.pattern, a.limit)
