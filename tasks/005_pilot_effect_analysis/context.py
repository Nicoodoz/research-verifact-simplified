"""Targeted source-context inspection; BHC context is not patient evidence."""
import csv
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.audit.common import digest_file, integer_id, write_json

RUN = ROOT / "outputs/005_pilot_effect_analysis/run_002"
CASES = ["C01", "C02", "C05", "C07", "C08", "C14", "C15", "C17", "C18", "C19", "C20", "C22", "C25"]
request = dict(stage="post_reference_review_targeted_context", cases=CASES,
    reason="Inspect near-paraphrase opposite GT, broad scope, plural/ongoing management, deidentification, unresolved event referents and dose/date context; C20 is a stable explicit control.",
    context_is_evidence=False, no_labels_changed=True)
write_json(RUN / "context_request.json", request)
packets = [json.loads((RUN / "packets" / (c + ".json")).read_text(encoding="utf-8")) for c in CASES]
wanted = {p["input"]["proposition_id"]:p for p in packets}
release = ROOT / "data/00_raw/verifact-bhc/1.1.0"
source = release / "propositions/propositions.csv.gz"
expected = next(line.split()[0] for line in (release / "SHA256SUMS.txt").read_text().splitlines()
    if line.split()[-1].lstrip("*") == "propositions/propositions.csv.gz")
assert digest_file(source) == expected
contexts = []
with gzip.open(source, "rt", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        p = wanted.get(row["proposition_id"])
        if p is None:
            continue
        assert row["text"] == p["input"]["text"] and integer_id(row["subject_id"]) == p["input"]["subject_id"]
        contexts.append(dict(case_id=p["case_id"], proposition_id=row["proposition_id"],
            parent_text_chunk=row["parent_text_chunk"], brief_hospital_course=row["brief_hospital_course"]))
assert len(contexts) == len(wanted)
write_json(RUN / "source_context.json", dict(source=source.relative_to(ROOT).as_posix(), source_sha256=expected,
    role="unverified source document context; never used as EHR evidence", cases=contexts))
for row in sorted(contexts, key=lambda r:r["case_id"]):
    print(row["case_id"], row["parent_text_chunk"], "\n")
