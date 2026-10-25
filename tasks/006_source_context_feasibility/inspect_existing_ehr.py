"""Inspect only the two already-reviewed 005 patients for event-specific evidence."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/006_source_context_feasibility/offline_review_001"
OUT.mkdir(parents=True,exist_ok=False)
source=ROOT/"data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz"
patterns={"98790":r"tolerat|post.op|washout|10-19|10/19", "45979":r"100\s*mg|100mg|rate.?control|good result|metoprolol|lopressor"}
rows=[]
with gzip.open(source,"rt",encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f):
        sid=row["SUBJECT_ID"].removesuffix(".0")
        if sid not in patterns:
            continue
        hits=[dict(start=max(0,m.start()-160),end=min(len(row["TEXT"]),m.end()+240)) for m in re.finditer(patterns[sid],row["TEXT"],re.I)]
        record=dict(subject_id=sid,row_id=row["ROW_ID"],hadm_id=row["HADM_ID"],chartdate=row["CHARTDATE"],
            charttime=row["CHARTTIME"],category=row["CATEGORY"],description=row["DESCRIPTION"],text=row["TEXT"],windows=hits)
        rows.append(record)
with (OUT/"selected_patient_notes.json").open("x",encoding="utf-8",newline="\n") as f:
    json.dump(dict(source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        patients=list(patterns),selection="All notes of 005 C17/C18 patients; no new-development or reserved-test notes",notes=rows),f,ensure_ascii=False,indent=2)
    f.write("\n")
for sid in patterns:
    own=[r for r in rows if r["subject_id"]==sid]
    print("PATIENT",sid,"notes",len(own))
    for r in own:
        print(r["row_id"],r["chartdate"],r["charttime"],r["category"],r["description"],"hits",len(r["windows"]))
