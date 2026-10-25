"""Offline unit checks for fixed-set rendering, failures, cache and fees."""
from __future__ import annotations

import json

import prepare086 as p
import run086 as r


def main():
    jobs=p.lines(p.OUT/"V_jobs.jsonl")
    frozen=p.read(p.OUT/"freeze.json")
    groups=p.read(p.OUT/"groups.json")
    assert len(jobs)==180 and len(set(x["request_id"] for x in jobs))==180
    assert set(frozen["measured_groups"])==set(groups)
    assert len({x["body_sha256"] for x in jobs})==180
    x=jobs[0];clone=dict(x,body=json.loads(json.dumps(x["body"])))
    assert r.canonical(clone["body"])==r.canonical(x["body"])
    clone["body"]["messages"][0]["content"]+=" "
    assert r.h(r.canonical(clone["body"]))!=x["body_sha256"]
    clone=json.loads(json.dumps(x["body"]))
    clone["model"]="other"
    assert r.h(r.canonical(clone))!=x["body_sha256"]
    request={"job":x,"reservation_cny":r.reservation(x)}
    assert r.charge(request,None)==request["reservation_cny"]
    assert r.charge(request,{"http_status":0})==request["reservation_cny"]
    assert r.charge(request,{"http_status":429})==0
    assert r.charge(request,{"http_status":200,"body_text":"{}"})==request["reservation_cny"]
    usage={"usage":{"prompt_tokens":8000,"completion_tokens":500}}
    assert abs(r.charge(request,{"http_status":200,"body_text":json.dumps(usage)})-.0285)<1e-12
    assert r.CAP==30 and r.V_CAP<r.CAP
    # Mock process: only unanswered logical requests retry, never a successful answer.
    real_client,real_attempt,real_sleep=r.client,r.attempt,r.time.sleep
    statuses=iter([429,200]);called=[]
    try:
        r.client=lambda:object()
        r.attempt=lambda cli,job,n:(called.append(n) or {"http_status":next(statuses)})
        r.time.sleep=lambda _:None
        r.process(x,0)
        assert called==[1,2]
        called.clear();statuses=iter([200])
        r.process(x,0)
        assert called==[1]
    finally:
        r.client, r.attempt, r.time.sleep=real_client,real_attempt,real_sleep
    if (p.OUT/"E_jobs.jsonl").exists():
        e=p.read(p.OUT/"E_jobs_freeze.json")
        assert p.sha(p.OUT/"E_jobs.jsonl")==e["jobs_sha256"]
    print(json.dumps({"status":"PASS","mock_api_calls":0,"checks":17},ensure_ascii=False))


if __name__=="__main__":main()
