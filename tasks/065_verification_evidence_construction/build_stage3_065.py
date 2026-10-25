from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as c
import run065

def main():
    if (c.OUT/"stage3_jobs.jsonl").exists():raise RuntimeError("stage3 exists")
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases_blind.jsonl")}
    jobs2=c.lines(c.OUT/"stage2_jobs.jsonl")
    jmap={(x["id"],x["condition"]):x for x in jobs2}
    attempts,term=run065.state()
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    mappings=[];jobs=[]
    for pid,x in cases.items():
        for cond in ("B","C"):
            j=jmap[(pid,cond)];rid=j["request_id"]
            c.require(rid in term,"missing composer "+rid)
            p=term[rid]["parsed"]
            if p.get("status")!="valid":
                mappings.append(dict(id=pid,condition=cond,composer_request_id=rid,
                    composer_status=p.get("status"),composer_errors=p.get("errors",[]),
                    selected_ids=[],selected_pids=[],kept_pids=[],passage_n=0,
                    reference_chars=0,external_selected=0,external_kept=0,
                    reference=None,judge_request_id=None))
                continue
            selected_ids=p["selected"]
            selected_pids=[j["candidate_lookup"][z] for z in selected_ids]
            ref,kept,chars=c.build_reference(selected_pids,corpus)
            h=c.stable("",pid)[:24]
            jid=f"065_{cond}_judge_"+h
            jobs.append(dict(request_id=jid,stage="stage3",kind="judge",
                model_key="deepseek",condition=cond,id=pid,body=c.score_body(x["claim"],ref)))
            mappings.append(dict(
                id=pid,condition=cond,composer_request_id=rid,composer_status="valid",
                selected_ids=selected_ids,selected_pids=selected_pids,
                kept_pids=kept,passage_n=len(kept),reference_chars=chars,
                external_selected=sum(str(z).startswith("E") for z in selected_ids),
                external_kept=sum(p2 not in set(x["c48_candidate_ids"]) for p2 in kept),
                reference=ref,judge_request_id=jid
            ))
    c.jsonl(c.OUT/"final_mapping.jsonl",mappings)
    c.jsonl(c.OUT/"stage3_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.CAP+1e-9,"stage3 cap")
    c.put(c.OUT/"stage3_freeze.json",dict(
        created_utc=c.now(),jobs=len(jobs),current_used_cny=used,
        stage3_bound_cny=bound,total_bound_cny=used+bound,
        composer_invalid=sum(x.get("composer_status")!="valid" for x in mappings),
        B_valid=sum(x["condition"]=="B" and x.get("composer_status")=="valid" for x in mappings),
        C_valid=sum(x["condition"]=="C" and x.get("composer_status")=="valid" for x in mappings),
        B_mean_passages=sum(x["passage_n"] for x in mappings if x["condition"]=="B" and x.get("composer_status")=="valid")/
                        max(1,sum(x["condition"]=="B" and x.get("composer_status")=="valid" for x in mappings)),
        C_mean_passages=sum(x["passage_n"] for x in mappings if x["condition"]=="C" and x.get("composer_status")=="valid")/
                        max(1,sum(x["condition"]=="C" and x.get("composer_status")=="valid" for x in mappings)),
        C_external_selected=sum(x["external_selected"] for x in mappings if x["condition"]=="C"),
        GT_used=False
    ))
    print("065 STAGE3 BUILT",len(jobs),"used",round(used,4),"bound",round(bound,4),flush=True)

if __name__=="__main__":main()
