"""Before-send checks: claim isolation, complete passages, shared scores and cache."""
from pathlib import Path
import common as c
import planning_core as pc


def check():
    c.check_files(c.OUT/"judge_preparation_001")
    base={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/inputs.jsonl")}
    inputs={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"judge_preparation_001/inputs.jsonl")}
    candidates={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"candidates_001/candidates.jsonl")}
    passages={x["passage_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/corpus.jsonl")}
    jobs={x["request_id"]:x for x in c.pilot.jsonl(c.OUT/"judge_preparation_001/jobs.jsonl")}
    assignments=c.pilot.read_csv(c.OUT/"judge_preparation_001/assignments.csv")[1]
    seen={}
    assert len(assignments)==432 and len({(x["method"],x["proposition_id"]) for x in assignments})==432
    for a in assignments:
        pid,method=a["proposition_id"],a["method"]
        item=inputs[pid]
        selection=item["retrieval"][method]
        expected=pc.select_evidence(candidates[pid]["candidate_ids"][method],item["scores"],passages,base[pid]["admission"])
        assert all(selection[key]==value for key,value in expected.items())
        assert selection["body_characters"]<=8000
        assert all(passages[key]["subject_id"]==base[pid]["subject_id"] for key in selection["selected_ids"])
        body=jobs[a["request_id"]]["body"]
        data=c.pilot.strict_json(body["messages"][1]["content"])
        assert data==dict(proposition=base[pid]["text"],reference=selection["reference"])
        assert c.pilot.fingerprint(body)==a["body_sha256"]
        if a["body_sha256"] in seen:
            assert seen[a["body_sha256"]]==a["request_id"]
        seen[a["body_sha256"]]=a["request_id"]
    repeat=c.read_json(c.OUT/"judge_preparation_001/repeat_assignments.json")
    assert len(repeat)==12 and len({(x["subject_id"],x["author_type"]) for x in repeat})==12
    for r in repeat:
        assert jobs[r["request_id"]]["body"]==jobs[r["canonical_request_id"]]["body"]
    return dict(claims=144,logical_assignments=432,canonical_jobs=len(seen),repeat_jobs=12,
        original_claim_and_ehr_only=True,shared_selector_recomputed=True,whole_passages_and_independent_ceiling=True,
        duplicate_bodies_share_canonical_result=True,execution_self_check=True,independent_audit=False)


if __name__=="__main__":
    value=check()
    target=c.OUT/"offline_checks_002"
    target.mkdir(parents=True,exist_ok=False)
    c.pilot.write_json(target/"checks.json",value)
    print(c.pilot.canonical(value))
