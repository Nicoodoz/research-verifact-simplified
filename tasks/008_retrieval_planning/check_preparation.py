"""Offline integrity and isolation checks on the six new patients only."""
from collections import defaultdict
from pathlib import Path
import argparse
import common as c
import prepare_experiment as prep
import planning_core as pc


def check():
    base=c.OUT/"preparation_001"
    manifest=c.check_files(base)
    for name,h in manifest["raw_sha256"].items():
        assert c.pilot.digest_file(c.RAW/name)==h
    for name,h in manifest["code_sha256"].items():
        assert c.pilot.digest_file(c.ROOT/name)==h
    inputs=c.pilot.jsonl(base/"inputs.jsonl")
    corpus=c.pilot.jsonl(base/"corpus.jsonl")
    cohort=c.pilot.read_csv(base/"cohort.csv")[1]
    universe=c.pilot.read_csv(base/"candidate_universe.csv")[1]
    assert prep.choose(universe)==cohort and len(inputs)==len(cohort)==144
    assert {x["subject_id"] for x in inputs}==set(c.PATIENTS)
    props=c.pilot.subset_csv(c.RAW/"propositions/propositions.csv.gz","subject_id",set(c.PATIENTS))
    lookup={r["proposition_id"]:r for r in props}
    notes={x["ROW_ID"]:x for x in c.pilot.subset_csv(c.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(c.PATIENTS))}
    for item in inputs:
        prop=lookup[item["proposition_id"]]
        assert item["text"]==prop["text"]
        sentences=[x for x in props if x["proposition_type"]=="sentence" and x["author_type"]==item["author_type"]]
        assert pc.source_context(prop,sentences)==item["source"]
    coverage=defaultdict(set)
    for p in corpus:
        note=notes[p["note_id"]]
        assert p["text"]==note["TEXT"][p["start"]:p["end_exclusive"]]
        assert p["note_sha256"]==c.pilot.digest_text(note["TEXT"])
        assert p["subject_id"]==c.pilot.integer_id(note["SUBJECT_ID"])
        admission=next(x["admission"] for x in inputs if x["subject_id"]==p["subject_id"])
        assert admission["ADMITTIME"][:10]<=p["date"]<=admission["DISCHTIME"][:10]
        assert p["category"].strip().lower()!="discharge summary"
        coverage[p["note_id"]].update(range(p["start"],p["end_exclusive"]))
    for nid,covered in coverage.items():
        assert all(i in covered for i,ch in enumerate(notes[nid]["TEXT"]) if not ch.isspace())
    for job in c.pilot.jsonl(base/"planner_jobs.jsonl"):
        data=c.pilot.strict_json(job["body"]["messages"][1]["content"])
        item=next(x for x in inputs if job["request_id"]=="plan:"+x["proposition_id"])
        assert data==dict(claim=item["text"],source_context=item["source"]["local"])
        assert job["body"]["enable_thinking"] is False and job["body"]["model"]==c.CHAT_MODEL
    catalog=c.read_json(base/"embedding_catalog.json")
    assert all(c.pilot.digest_text(t)==key for key,t in catalog.items())
    assert prep.embedding_jobs(catalog,"base")==c.pilot.jsonl(base/"embedding_base_jobs.jsonl")
    assert sum(c.PHASE_CAPS.values())==40
    return dict(execution_self_check=True,independent_audit=False,claims=len(inputs),passages=len(corpus),
        complete_nonwhitespace_note_coverage=len(coverage),literal_source_offsets=True,raw_span_and_scope_checks=True,
        deterministic_selection_and_embedding_jobs=True,model_input_label_isolation=True,raw_hashes_unchanged=True,api_calls=0)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    result=check()
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        c.pilot.write_json(a.output/"checks.json",result)
    print(c.pilot.canonical(result))
