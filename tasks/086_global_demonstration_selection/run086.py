"""Append-only V/E Alibaba Judge runner with one ¥30 original-price ledger."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/086_global_demonstration_selection"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

CAP=30.0
V_CAP=9.0
MODEL="deepseek-v4-flash-0731"
RETRY={0,429,500,502,503,504}
PARSER_VERSION="024_core_fields_v1"


def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def h(x):return hashlib.sha256(x.encode("utf-8")).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def lines(path):return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s]
def save_new(path,item):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(item,f,ensure_ascii=False,sort_keys=True);f.write("\n");f.flush();os.fsync(f.fileno())


def reservation(job):
    body=job["body"]
    return ((len(canonical(body).encode("utf-8"))+2000)*3+body["max_tokens"]*9)/1e6


def charge(req,transport):
    if transport is None or transport.get("http_status")==0:return req["reservation_cny"]
    if transport["http_status"]!=200:return 0.0
    try:
        payload=json.loads(transport["body_text"])
        usage=payload["usage"]
        inp,out=int(usage["prompt_tokens"]),int(usage["completion_tokens"])
        assert 0<=inp<=len(canonical(req["job"]["body"]).encode("utf-8"))+2000
        assert 0<=out<=req["job"]["body"]["max_tokens"]
        return (inp*3+out*9)/1e6
    except (KeyError,ValueError,TypeError,AssertionError):return req["reservation_cny"]


def state():
    rows=[];success={};count=Counter()
    for rp in sorted((OUT/"attempts").glob("*/request.json")):
        req=read(rp)
        receipt=rp.parent/"receipt.json"
        tr=read(receipt)["transport"] if receipt.exists() else None
        row={"request_id":req["job"]["request_id"],"attempt_no":req["attempt_no"],
             "phase":req["job"]["phase"],"id":req["job"]["id"],"sid":req["job"]["sid"],
             "arm":req["job"]["arm"],"http_status":tr.get("http_status") if tr else None,
             "cost_or_unknown_cny":charge(req,tr),
             "request_source":rp.relative_to(ROOT).as_posix(),
             "receipt_source":receipt.relative_to(ROOT).as_posix() if tr else None}
        rows.append(row);count[row["request_id"]]+=1
        if tr and tr.get("http_status")==200:
            if row["request_id"] in success:raise RuntimeError("duplicate HTTP200 for one logical request")
            success[row["request_id"]]=row
    return rows,success,count


def client():
    conf=load_config(ROOT/".env.aliyun")
    if conf.base_url!="https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1":
        raise RuntimeError("Aliyun workspace endpoint changed; stop before charges")
    return DirectClient(Config(conf.api_key,conf.base_url,MODEL),timeout=240)


def check_jobs(stage):
    freeze=read(OUT/"freeze.json")
    if freeze["status"]!="FROZEN_BEFORE_086_NEW_API_AND_E_GT" or freeze["task_cap_original_cny"]!=CAP:
        raise RuntimeError("086 freeze/cap mismatch")
    path=OUT/("V_jobs.jsonl" if stage=="V" else "E_jobs.jsonl")
    digest=freeze["V_jobs_sha256"] if stage=="V" else read(OUT/"E_jobs_freeze.json")["jobs_sha256"]
    if sha(path)!=digest:raise RuntimeError("Frozen jobs changed")
    if stage=="E":
        selected=read(OUT/"D_star_freeze.json")
        if selected["status"]!="FROZEN_BEFORE_E_NEW_API_AND_E_GT":raise RuntimeError("D* not frozen")
        if sha(OUT/"E_cases_blind.jsonl")!=freeze["E_cases_blind_sha256"]:raise RuntimeError("E sample changed")
    jobs=lines(path)
    if len({j["request_id"] for j in jobs})!=len(jobs):raise RuntimeError("Duplicate request IDs")
    if stage=="V" and len(jobs)!=180:raise RuntimeError("V job count mismatch")
    if stage=="E" and not 122<=len(jobs)<=342:raise RuntimeError("E job count mismatch")
    cli=client()
    for j in jobs:
        if j["phase"]!=stage or j["body_sha256"]!=h(canonical(j["body"])):raise RuntimeError("Job drift")
        cli.validate(j["body"])
        b=j["body"]
        if b["model"]!=MODEL or b["enable_thinking"] is not True or b["reasoning_effort"]!="high":raise RuntimeError("Judge condition drift")
        if b["temperature"]!=0 or b["max_tokens"]!=8192:raise RuntimeError("Generation condition drift")
    return jobs


def attempt(cli,job,n):
    aid=job["request_id"]+f"__try{n}"
    folder=OUT/"attempts"/h(aid)[:24]
    folder.mkdir(parents=True,exist_ok=False)
    req={"attempt_id":aid,"attempt_no":n,"job":job,"parser_version":PARSER_VERSION,
         "reservation_cny":reservation(job),"task_cap_original_cny":CAP,
         "price_source":"https://help.aliyun.com/en/model-studio/model-pricing"}
    save_new(folder/"request.json",req)
    t0=time.monotonic()
    try:tr=cli.send(job["body"])
    except Exception as exc:
        tr={"http_status":0,"body_text":"","outcome_unknown":True,
            "failure_phase":"unknown_after_attempt","error_type":type(exc).__name__}
    tr["client_elapsed_seconds"]=time.monotonic()-t0
    save_new(folder/"receipt.json",{"request_sha256":sha(folder/"request.json"),"transport":tr})
    if tr.get("http_status")==200:
        try:
            payload=json.loads(tr["body_text"])
            if payload.get("model")!=MODEL:raise RuntimeError("model_mismatch")
        except (ValueError,TypeError,AttributeError) as exc:raise RuntimeError("malformed_provider_envelope") from exc
    return tr


def process(job,past):
    cli=client()
    for n in range(past+1,4):
        tr=attempt(cli,job,n)
        status=tr["http_status"]
        if status==200:return
        if status not in RETRY:raise RuntimeError(f"nonretryable_http_{status}")
        if n==3:raise RuntimeError(f"recovery_exhausted_http_{status}")
        time.sleep(3*(2**(n-1)))


def run(stage,workers):
    if not 1<=workers<=3:raise ValueError("1..3 workers")
    jobs=check_jobs(stage)
    (OUT/"attempts").mkdir(exist_ok=True)
    lock=OUT/"run.lock"
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    pending=[];running={};stop=None;last=time.monotonic()
    try:
        past,success,counts=state()
        known={j["request_id"] for j in jobs}
        if any(j["phase"]==stage and j["request_id"] not in known for j in past):raise RuntimeError("foreign stage request")
        pending=[j for j in jobs if j["request_id"] not in success]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                while pending and len(running)<workers and stop is None:
                    j=pending[0];rid=j["request_id"]
                    if counts[rid]>=3:stop="retries_exhausted_previous";break
                    current,success,counts=state()
                    active={x["request_id"] for x in running.values()}
                    used=sum(x["cost_or_unknown_cny"] for x in current if x["request_id"] not in active)
                    # Active jobs' prior attempts are excluded from `used`, so keep
                    # their entire three-attempt envelope reserved until completion.
                    inflight=sum(reservation(x)*3 for x in running.values())
                    reserve=reservation(j)*(3-counts[rid])
                    if used+inflight+reserve>(V_CAP if stage=="V" else CAP)+1e-9:
                        # Existing calls may finish and release conservative reservations.
                        if running:break
                        stop="stage_or_total_budget_reservation_would_exceed";break
                    pending.pop(0)
                    running[pool.submit(process,j,counts[rid])]=j
                if not running:break
                done,_=concurrent.futures.wait(running,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    job=running.pop(future)
                    try:future.result()
                    except Exception as exc:stop=f"{type(exc).__name__}:{str(exc)[:100]}"
                if time.monotonic()-last>30:
                    current,success,_=state()
                    print(json.dumps({"stage":stage,"success_stage":sum(x["phase"]==stage for x in success.values()),
                        "pending":len(pending),"running":len(running),
                        "used_or_unknown_cny":round(sum(x["cost_or_unknown_cny"] for x in current),6),"stop":stop}),flush=True)
                    last=time.monotonic()
        rows,success,_=state()
        result={"stage":stage,"jobs":len(jobs),"success":sum(j["request_id"] in success for j in jobs),
                "all_task_attempts":len(rows),"used_or_unknown_cny":sum(x["cost_or_unknown_cny"] for x in rows),
                "stop":stop}
        print(json.dumps(result,ensure_ascii=False),flush=True)
        if result["used_or_unknown_cny"]>CAP+1e-9:raise RuntimeError("HARD_CAP_BREACH")
        if stop or result["success"]!=len(jobs):raise RuntimeError(stop or "stage_incomplete")
    finally:lock.unlink()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("V","E","preflightV","preflightE"))
    p.add_argument("--workers",type=int,default=3)
    args=p.parse_args()
    actual=args.stage[-1]
    if args.stage.startswith("preflight"):
        jobs=check_jobs(actual)
        print(json.dumps({"stage":actual,"jobs":len(jobs),
              "first_three_attempt_reservation_cny":reservation(jobs[0])*3,
              "current_attempts":len(state()[0]),"network_calls":0},ensure_ascii=False))
    else:run(actual,args.workers)


if __name__=="__main__":main()
