"""After V-only D* freeze, create E jobs without reading E labels or predictions."""
from __future__ import annotations

import json
from pathlib import Path

import prepare086 as p

ROOT=p.ROOT;OUT=p.OUT


def main():
    freeze=p.read(OUT/"freeze.json")
    selected=p.read(OUT/"D_star_freeze.json")
    assert selected["status"]=="FROZEN_BEFORE_E_NEW_API_AND_E_GT" and selected["E_GT_read"] is False
    assert p.sha(OUT/"E_cases_blind.jsonl")==freeze["E_cases_blind_sha256"]
    e=p.lines(OUT/"E_cases_blind.jsonl")
    groups=p.read(OUT/"groups.json")
    candidate={x["candidate_id"]:x for x in p.lines(OUT/"candidate_pool.jsonl")}
    semantics=p.read(p.TEMPLATE)
    base=semantics["B_system_content"]
    appendix=semantics["F4_appendix_exact"]
    header=appendix[:appendix.index('{"physician_label"')]
    systems={name:p.render(base,header,[candidate[i] for i in detail["ordered_candidate_ids"]])
             for name,detail in groups.items()}
    assert all(p.h(systems[name])==groups[name]["system_sha256"] for name in groups)
    assert systems["F4"]==semantics["F4_system_content"]
    selected_name=selected["name"]
    control="R2" if selected_name=="R1" else "R1"
    arms=list(dict.fromkeys(("F4",selected_name,control)))
    bridge=sorted(e,key=lambda x:p.h("086E/Bbridge/"+x["id"]))[:12]
    bridge_ids={x["id"] for x in bridge}
    base_body=p.lines(OUT/"V_jobs.jsonl")[0]["body"]
    jobs=[]
    for x in e:
        scheduled=arms+(["B"] if x["id"] in bridge_ids else [])
        for arm in sorted(scheduled,key=lambda a:p.h("086E/order/"+x["id"]+"/"+a)):
            body=p.new_body(base_body,base if arm=="B" else systems[arm],x["claim"],x["reference"])
            canonical=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            if arm=="F4" and p.h(canonical)!=x["source_F4_body_sha256"]:
                raise RuntimeError("Historical F4 body not identical on E ID")
            jobs.append({"phase":"E","id":x["id"],"sid":x["sid"],"arm":arm,"body":body,
                         "body_sha256":p.h(canonical),
                         "request_id":p.h("086/E/"+arm+"/"+x["id"]+"/"+p.h(canonical))[:24]})
    assert len(jobs)==110*len(arms)+12
    assert len({x["request_id"] for x in jobs})==len(jobs)
    p.putl(OUT/"E_jobs.jsonl",jobs)
    p.put(OUT/"E_jobs_freeze.json",{"status":"FROZEN_BEFORE_E_NEW_API_AND_E_GT",
        "D_star":selected_name,"nonutility_control":control,"arms":arms,
        "E_n":110,"B_bridge_n":12,"B_bridge_ids":sorted(bridge_ids),
        "jobs_n":len(jobs),"jobs_sha256":p.sha(OUT/"E_jobs.jsonl"),
        "D_star_freeze_sha256":p.sha(OUT/"D_star_freeze.json"),
        "E_sample_sha256":freeze["E_cases_blind_sha256"],"E_GT_read":False})
    print(json.dumps({"D_star":selected_name,"arms":arms,"jobs":len(jobs),
                      "bridge_B":12,"E_GT_read":False},ensure_ascii=False))


if __name__=="__main__":main()
