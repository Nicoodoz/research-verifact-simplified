"""Pre-API invariant checks. No E labels, no network, no AWS."""
from __future__ import annotations

import json
from collections import Counter

import prepare086 as p
import run086 as r


def main():
    f=p.read(p.OUT/"freeze.json")
    assert f["status"]=="FROZEN_BEFORE_086_NEW_API_AND_E_GT" and not f["E_GT_read"]
    assert f["task_cap_original_cny"]==30.0
    for rel,value in f["source_sha256"].items():assert p.sha(p.ROOT/rel)==value
    for name,path in (("candidate_pool_sha256","candidate_pool.jsonl"),("groups_sha256","groups.json"),
                      ("V_cases_sha256","V_cases.jsonl"),("E_cases_blind_sha256","E_cases_blind.jsonl"),
                      ("V_jobs_sha256","V_jobs.jsonl")):
        assert p.sha(p.OUT/path)==f[name]
    candidates=p.lines(p.OUT/"candidate_pool.jsonl")
    v=p.lines(p.OUT/"V_cases.jsonl")
    e=p.lines(p.OUT/"E_cases_blind.jsonl")
    groups=p.read(p.OUT/"groups.json")
    assert len(candidates)==12 and len(v)==36 and len(e)==110
    D={x["sid"] for x in candidates};V={x["sid"] for x in v};E={x["sid"] for x in e}
    assert (len(D),len(V),len(E))==(6,12,22) and not (D&V or D&E or V&E)
    assert Counter(x["GT"] for x in v)=={"Supported":14,"Not Supported":11,"Not Addressed":11}
    assert all("GT" not in x and "human_gt" not in x for x in e)
    byid={x["candidate_id"]:x for x in candidates}
    assert set(groups)=={"F4","R1","R2","REP","N1"}
    sem=p.read(p.TEMPLATE)
    header=sem["F4_appendix_exact"][:sem["F4_appendix_exact"].index('{"physician_label"')]
    for arm,g in groups.items():
        examples=[byid[x] for x in g["ordered_candidate_ids"]]
        assert len(examples)==4 and len({x["sid"] for x in examples})==4
        assert [x["physician_label"] for x in examples]==[
            "Supported","Not Supported","Supported","Not Addressed"]
        system=p.render(sem["B_system_content"],header,examples)
        assert p.h(system)==g["system_sha256"]
        assert abs(len(system)-len(sem["F4_system_content"]))/len(sem["F4_system_content"])<.02
    assert p.render(sem["B_system_content"],header,[byid[x] for x in groups["F4"]["ordered_candidate_ids"]])==sem["F4_system_content"]
    jobs=p.lines(p.OUT/"V_jobs.jsonl")
    assert len(jobs)==180 and len({x["request_id"] for x in jobs})==180
    case={x["id"]:x for x in v}
    for j in jobs:
        assert j["phase"]=="V" and j["sid"]==case[j["id"]]["sid"]
        assert p.h(r.canonical(j["body"]))==j["body_sha256"]
        target=json.loads(j["body"]["messages"][1]["content"])
        assert target=={"proposition":case[j["id"]]["claim"],"reference":case[j["id"]]["reference"]}
        assert j["body"]["model"]==r.MODEL and j["body"]["enable_thinking"] is True
    fake={"job":jobs[0],"reservation_cny":r.reservation(jobs[0])}
    assert r.charge(fake,None)==fake["reservation_cny"]
    assert r.charge(fake,{"http_status":0})==fake["reservation_cny"]
    assert r.charge(fake,{"http_status":429})==0
    assert r.charge(fake,{"http_status":200,"body_text":json.dumps({"usage":{"prompt_tokens":9000,"completion_tokens":1000}})})==.036
    assert r.reservation(jobs[0])*3<r.V_CAP<r.CAP
    print(json.dumps({"status":"PASS","D":len(D),"V":len(V),"E":len(E),"jobs":len(jobs),
                      "E_GT_read":False,"network_calls":0},ensure_ascii=False))


if __name__=="__main__":main()
