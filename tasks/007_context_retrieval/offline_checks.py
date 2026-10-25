"""Validate complete EHR spans and produce outcome-free old-case retrieval probes."""
import json
import re
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import prepare as p
from retrieval import spans, ARMS
from run_judge import load_preparation


def main():
    prep=p.OUT/"preparation_003"
    output=next(p.OUT/f"offline_checks_{i:03d}" for i in range(1,1000) if not (p.OUT/f"offline_checks_{i:03d}").exists())
    output.mkdir(exist_ok=False)
    jobs=load_preparation(prep)
    corpora=json.loads((prep/"corpora.json").read_text(encoding="utf-8"))
    notes=p.pilot.subset_csv(p.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(corpora))
    lookup={n["ROW_ID"]:n for n in notes}
    for corpus in corpora.values():
        for passage in corpus:
            text=lookup[passage["note_id"]]["TEXT"]
            assert text[passage["start"]:passage["end_exclusive"]]==passage["text"]
            assert p.pilot.digest_text(text)==passage["note_sha256"]
    # Check every included original note: no non-whitespace character omitted in indexing.
    indexed_notes={x["note_id"] for c in corpora.values() for x in c}
    for nid in indexed_notes:
        text=lookup[nid]["TEXT"]
        recovered="".join(text[a:b] for a,b in spans(text))
        assert re.sub(r"\s","",text)==re.sub(r"\s","",recovered)
    inputs=p.pilot.jsonl(prep/"inputs.jsonl")
    for item in inputs:
        owned=[j for j in jobs if j["request_id"].endswith(":"+item["proposition_id"])]
        for j in owned:
            data=json.loads(j["body"]["messages"][1]["content"])
            assert set(data)=={"proposition","reference"} and data["proposition"]==item["text"]
            assert "human_gt" not in data
            arm=j["request_id"].split(":")[0].replace("claim_repeat","claim")
            assert data["reference"]==item["retrieval"][arm]["reference"]
            for passage in item["retrieval"][arm]["passages"]:
                assert lookup[passage["note_id"]]["TEXT"][passage["start"]:passage["end_exclusive"]]==passage["text"]
    patterns={"006_N50":r"Left vent drain dc/d|removal of a left ventriculostomy", "006_N56":r"Neuro checks done Q2|Continue to monitor neuro status",
        "006_N45":r"opens eyes spontaneously", "006_N25":r"Delayed R wave progress", "006_N15":r"Hold Flomax|holding Flomax", "006_N23":r"found by his HCW",
        "005_C17":r"Stable post.op|stable post.op", "005_C18":r"100\s*mg|100mg"}
    probes=[]
    for item in p.pilot.jsonl(prep/"old_case_probes.jsonl"):
        pattern=patterns[item["case_id"]]
        all_hits=[x for x in corpora[item["subject_id"]] if re.search(pattern,x["text"],re.I)]
        probes.append(dict(case_id=item["case_id"],claim=item["text"],queries=item["queries"],
            marker_is_not_gold_evidence=True,corpus_matches=[dict(passage_id=x["passage_id"],note_id=x["note_id"],date=x["date"],text=x["text"]) for x in all_hits],
            hits={a:[dict(passage_id=x["passage_id"],note_id=x["note_id"],date=x["date"],text=x["text"]) for x in item["retrieval"][a]["passages"] if re.search(pattern,x["text"],re.I)] for a in ARMS}))
    p.pilot.write_json(output/"old_case_markers.json",probes)
    code=("import sys,unittest\nfrom unittest.mock import patch\nwith patch('socket.create_connection',side_effect=AssertionError('Network disabled')), patch('socket.socket.connect',side_effect=AssertionError('Network disabled')), patch('socket.socket.connect_ex',side_effect=AssertionError('Network disabled')):\n result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\nsys.exit(not result.wasSuccessful())")
    result=subprocess.run([sys.executable,"-B","-c",code],cwd=p.ROOT,capture_output=True,text=True,encoding="utf-8")
    (output/"tests.log").write_text(result.stdout+result.stderr,encoding="utf-8",newline="\n")
    assert result.returncode==0,"Tests failed"
    report=dict(tests_run=int(re.search(r"Ran (\d+) tests",result.stderr).group(1)),network_blocked_for_tests=True,
        paid_api_calls=0,indexed_notes_checked=len(indexed_notes),passages_checked=sum(map(len,corpora.values())),
        all_indexed_nonwhitespace_text_preserved=True,claims=len(inputs),requests=len(jobs),
        judge_receives_no_source_query_or_GT=True,all_displayed_evidence_is_exact_raw_note_span=True,
        prep_manifest_sha256=p.pilot.digest_file(prep/"manifest.json"))
    p.pilot.write_json(output/"checks.json",report)
    print(p.pilot.canonical(report))
    print(p.pilot.canonical([dict(case=x["case_id"],corpus_hits=len(x["corpus_matches"]),hits={a:len(v) for a,v in x["hits"].items()}) for x in probes]))


if __name__=="__main__":
    main()
