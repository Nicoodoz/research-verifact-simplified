"""Post-hoc sensitivity for ALL zero-budget cases; never rewrites primary results."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import prepare as p
from retrieval import ARMS, reference, reference_line
from run_judge import MeteredRunner, load_accounts, file_hash, fingerprint, require, save
from score_results import normalize


def pack_saved(corpus,ranking,cap=9000):
    """Same packing rule as the main run, without min-across-queries zeroing."""
    lookup={x["passage_id"]:x for x in corpus}
    picked,size,seen=[],0,set()
    for rank,row in enumerate(ranking,1):
        x=lookup[row["passage_id"]]
        duplicate=(x["date"],x["category"],x["text"])
        if duplicate in seen:
            continue
        cost=len(reference_line(len(picked)+1,x))+1
        if size+cost>cap:
            remaining=cap-size-len(reference_line(len(picked)+1,dict(x,text="")))-12
            if remaining<80:
                continue
            raw=x["text"][:remaining]
            if " " in raw:
                raw=raw.rsplit(" ",1)[0]
            x=dict(x,text=raw,original_end_exclusive=x["end_exclusive"],end_exclusive=x["start"]+len(raw),display_truncated_for_budget=True)
            cost=len(reference_line(len(picked)+1,x))+1
            if size+cost>cap:
                continue
        picked.append(dict(x,retrieval_rank=rank,score=row["score"]))
        size+=cost
        seen.add(duplicate)
        if len(picked)==24:
            break
    return dict(passages=picked,retrieved_characters=size,fixed_character_ceiling=cap,top100=ranking)


def prepare_sensitivity():
    out=p.OUT/"zero_budget_sensitivity_001"
    out.mkdir(exist_ok=False)
    prep=p.OUT/"preparation_003"
    inputs=p.pilot.jsonl(prep/"inputs.jsonl")
    chosen=[x for x in inputs if x["retrieval"]["claim"]["matched_character_budget"]==0]
    assert [x["case_id"] for x in chosen]==["R031","R078","R083"]
    corpora=json.loads((prep/"corpora.json").read_text(encoding="utf-8"))
    originals={j["request_id"]:j for j in p.pilot.jsonl(prep/"requests.jsonl")}
    jobs,newinputs=[],[]
    for item in chosen:
        results={}
        for arm in ARMS:
            result=pack_saved(corpora[item["subject_id"]],item["retrieval"][arm]["top100"])
            result["reference"]=reference(result,item["admission"])
            result["reference_id"]=p.pilot.digest_text(result["reference"])
            results[arm]=result
            rid=arm+":"+item["proposition_id"]
            body=json.loads(json.dumps(originals[rid]["body"]))
            body["messages"][1]["content"]=p.pilot.canonical(dict(proposition=item["text"],reference=result["reference"]))
            bound=((len(p.pilot.canonical(body).encode("utf-8"))+1000)*3+2048*9)/1e6
            jobs.append(dict(request_id=rid,body=body,max_cost_cny=bound))
        newinputs.append(dict(item,retrieval=results))
    p.pilot.write_jsonl(out/"inputs.jsonl",newinputs)
    p.pilot.write_jsonl(out/"requests.jsonl",jobs)
    estimate=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+450*9)/1e6 for j in jobs)
    primary=json.loads((p.OUT/"run_001/completion.json").read_text(encoding="utf-8"))["estimated_settled_and_reserved_cny"]
    require(primary+1<=16 and estimate<=1,"Cumulative task budget would be exceeded")
    plan=dict(registered_utc=datetime.now(timezone.utc).isoformat(),authority="user_standing_approval_task_estimate_leq_16_CNY",
        reason="All 3 cases with primary shared budget zero; criterion is retrieval geometry, not correctness. Study whether nonempty source-query candidates were hidden by budget matching.",
        case_ids=[x["case_id"] for x in chosen],requests=12,estimated_cny=estimate,budget_cny=1,
        primary_used_cny=primary,cumulative_task_upper_guard_cny=primary+1,original_task_cap_cny=16,
        primary_outputs_unchanged=True,queries_rankings_claim_Judge_unchanged=True,
        actual_evidence_sizes_not_equal=True,conclusion_scope="Post-hoc rescue-at-common-ceiling diagnostic, not a replacement for matched-budget primary results",
        baseline_empty_bodies_repeated_as_explicit_controls=True,
        source_prep_manifest_sha256=file_hash(prep/"manifest.json"),code_sha256=file_hash(Path(__file__)),
        jobs_sha256=file_hash(out/"requests.jsonl"),inputs_sha256=file_hash(out/"inputs.jsonl"))
    p.pilot.write_json(out/"protocol_and_authority.json",plan)
    print(p.pilot.canonical(dict(cases=plan["case_ids"],requests=12,estimate=estimate,cap=1,cumulative_guard=primary+1)))


def execute():
    out=p.OUT/"zero_budget_sensitivity_001"
    plan=json.loads((out/"protocol_and_authority.json").read_text(encoding="utf-8"))
    require(plan["code_sha256"]==file_hash(Path(__file__)) and plan["jobs_sha256"]==file_hash(out/"requests.jsonl")
        and plan["inputs_sha256"]==file_hash(out/"inputs.jsonl") and plan["cumulative_task_upper_guard_cny"]<=16,"Sensitivity inputs/authority changed")
    jobs=p.pilot.jsonl(out/"requests.jsonl")
    require(len(jobs)==12 and not (out/"summary.json").exists(),"Do not regenerate a finished sensitivity run")
    runner=MeteredRunner(load_accounts(p.ROOT/".env.siliconflow_pool"),jobs,out/"receipts",1,file_hash(out/"protocol_and_authority.json"))
    result=runner.run(2)
    inputs={r["proposition_id"]:r for r in p.pilot.jsonl(out/"inputs.jsonl")}
    normalized=[]
    for job in jobs:
        progress=runner.state["jobs"][job["request_id"]]
        if progress["status"]=="response_received":
            receipt=runner._read_receipt(progress["receipts"][-1])
            normalized.append(normalize(job,inputs[job["request_id"].split(":",1)[1]],receipt["transport"]))
    p.pilot.write_jsonl(out/"normalized_responses.jsonl",normalized)
    p.pilot.write_json(out/"summary.json",dict(result,valid=sum(r["status"]=="success" for r in normalized),
        task_cumulative_used_or_reserved_cny=plan["primary_used_cny"]+runner.state["reserved_budget_cny"]))
    print(p.pilot.canonical(dict(result,valid=len([r for r in normalized if r["status"]=="success"]))))


if __name__=="__main__":
    prepare_sensitivity() if sys.argv[1]=="prepare" else execute()
