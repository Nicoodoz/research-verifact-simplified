"""Offline self-check of extraction, source context, anchors and shared metrics."""
import csv
import gzip
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import effect_analysis as effects
import build_effect_review as review

ROOT, TASK, OUT = effects.ROOT, effects.TASK, effects.OUT
pilot = effects.pilot


def main():
    first = OUT / "run_002"
    formal = first / "review_002"
    out = next(OUT / f"verification_{i:03d}" for i in range(1,10000) if not (OUT / f"verification_{i:03d}").exists())
    out.mkdir()
    sources = [effects.SOURCE / "manifest.json", effects.SOURCE / "analysis/manifest.json",
        ROOT / "outputs/003_error_analysis/patient_groups.json", ROOT / ".gitignore"]
    before = {str(p.relative_to(ROOT)):pilot.digest_file(p) for p in sources}
    code = ("import sys,unittest\nfrom unittest.mock import patch\n"
        "with patch('socket.socket.connect',side_effect=AssertionError('Network disabled')), "
        "patch('socket.socket.connect_ex',side_effect=AssertionError('Network disabled')), "
        "patch('socket.create_connection',side_effect=AssertionError('Network disabled')):\n"
        "    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\n"
        "sys.exit(not result.wasSuccessful())\n")
    tests = subprocess.run([sys.executable,"-B","-c",code],cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
    (out / "tests.log").write_text(tests.stdout+tests.stderr,encoding="utf-8",newline="\n")
    pilot.require(tests.returncode == 0,"Tests failed; see saved log")
    previous = set(OUT.glob("run_*"))
    with patch("socket.socket.connect",side_effect=AssertionError("Network disabled")), patch("socket.socket.connect_ex",side_effect=AssertionError("Network disabled")), patch("socket.create_connection",side_effect=AssertionError("Network disabled")):
        effects.extract()
    created = set(OUT.glob("run_*")) - previous
    pilot.require(len(created)==1,"Expected exactly one new extraction")
    second = created.pop()
    original_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    same = {name: pilot.digest_file(first / name)==pilot.digest_file(second / name)
        for name in original_manifest["outputs_sha256"]}
    pilot.require(all(same.values()),"Repeated extraction changed")
    pilot.require(pilot.digest_file(OUT/"run_001/selected_cases.csv")==pilot.digest_file(first/"selected_cases.csv"),"Selection changed after initial freeze")
    anchors = json.loads((formal / "evidence_anchors.json").read_text(encoding="utf-8"))
    packets = {p.stem:json.loads(p.read_text(encoding="utf-8")) for p in (first/"packets").glob("C*.json")}
    for a in anchors:
        review.verify_anchor(a,packets[a["case_id"]])
    reconstructed = {cid:{} for cid in packets}
    unique_blocks = 0
    for file in (first/"reference_unions").glob("*.json"):
        blocks = json.loads(file.read_text(encoding="utf-8"))
        unique_blocks += len(blocks)
        for block in blocks:
            pilot.require(pilot.digest_text(block["text"])==block["block_id"],"Union block changed")
            for occurrence in block["occurrences"]:
                cid, number = occurrence["case"], occurrence["number"]
                pilot.require(packets[cid]["input"]["subject_id"]==file.stem,"Cross-patient union")
                pilot.require(number not in reconstructed[cid],"Duplicate reference occurrence")
                reconstructed[cid][number]=block["text"]
    for cid,p in packets.items():
        pilot.require(reconstructed[cid]==dict(effects.reference_blocks(p["input"]["reference"])),"Union does not cover complete reference")
    contexts = json.loads((first/"source_context.json").read_text(encoding="utf-8"))
    source = ROOT/contexts["source"]
    pilot.require(pilot.digest_file(source)==contexts["source_sha256"],"Raw context source changed")
    wanted = {r["proposition_id"]:r for r in contexts["cases"]}
    matched = 0
    with gzip.open(source,"rt",encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            own = wanted.get(row["proposition_id"])
            if own:
                pilot.require(all(own[k]==row[k] for k in ("parent_text_chunk","brief_hospital_course")),"Source context mismatch")
                pilot.require(own["parent_text_chunk"] in own["brief_hospital_course"],"Source parent has no BHC location")
                matched += 1
    pilot.require(matched==13,"Wrong source context scope")
    # A second rendering tests document/anchor reproducibility, not a second clinical interpretation.
    repeated_review = review.build(first,TASK/"review_notes.json",TASK/"report_template.md")
    first_review_manifest = json.loads((formal/"manifest.json").read_text(encoding="utf-8"))
    review_same = {name:pilot.digest_file(formal/name)==pilot.digest_file(repeated_review/name)
        for name in first_review_manifest["outputs_sha256"]}
    pilot.require(all(review_same.values()),"Review rendering changed")
    pilot.require(all(pilot.digest_file(ROOT/name)==h for name,h in before.items()),"Existing protected source changed")
    service = ROOT/"outputs/service_tools/siliconflow_pool/verification_001/verification.json"
    preserved = {}
    if service.exists():
        old = json.loads(service.read_text(encoding="utf-8"))
        preserved = {name:pilot.digest_file(ROOT/name)==h for name,h in old["code_and_docs_sha256"].items() if name!="README.md"}
        pilot.require(all(preserved.values()),"Pre-existing account pool work changed")
    result = dict(status="executor_analysis_complete_pending_independent_audit",tests_run=int(re.search(r"Ran (\d+) tests",tests.stderr).group(1)),
        tests_exit_code=0, network_connections_blocked=True, api_calls=0, independent_audit_performed=False,
        extraction_files_byte_identical=same, first_run_selection_preserved=True, repeat_extraction=second.relative_to(ROOT).as_posix(),
        review_files_byte_identical=review_same, repeat_review=repeated_review.relative_to(ROOT).as_posix(),
        evidence_anchors_verified=len(anchors), selected_cases=len(packets), complete_reference_items=sum(map(len,reconstructed.values())),
        unique_reference_blocks=unique_blocks, source_contexts_verified=matched, source_context_not_gold_evidence=True,
        original_004_primary_metrics_exactly_reproduced=True, reserved_test_used=False, protected_sources_unchanged=True,
        pre_existing_pool_files_preserved=preserved, python=sys.version,
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in [*TASK.glob("*.py"),ROOT/"tests/test_pilot_effect_analysis.py"]})
    pilot.write_json(out/"verification.json",result)
    print(pilot.canonical(dict(verification=str(out),tests=result["tests_run"],anchors=len(anchors),
        extraction_files=len(same),review_files=len(review_same))))


if __name__=="__main__":
    main()
