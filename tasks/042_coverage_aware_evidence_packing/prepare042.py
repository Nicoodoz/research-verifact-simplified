"""Freeze GT-blind eligible cohort, reproduce baseline references and build 042 screen jobs."""
import json,sys
from collections import defaultdict,Counter
import common042 as c

R031=c.ROOT/"outputs/031_training_expansion_confirmation"
PLAN=c.OUT/"planning_001"

sys.path.insert(0,str(c.ROOT/"tasks/031_training_expansion_confirmation"))
import api031

def main():
    c.require(not PLAN.exists(),"042 planning already exists")
    meta=c.csvread(R031/"planning_001/claim_metadata.csv")
    inputs={r["proposition_id"]:r for r in c.lines(R031/"materials_001/inputs.jsonl")}
    mats={r["proposition_id"]:r for r in c.lines(R031/"judge_inputs_001/materials.jsonl")}
    passages={r["passage_id"]:r for r in c.lines(R031/"materials_001/corpus.jsonl")}
    cans={r["proposition_id"]:r for r in c.lines(R031/"retrieval_001/candidates.jsonl")}
    rjobs={r["proposition_id"]:r for r in c.lines(R031/"retrieval_001/jobs.jsonl")}
    attempts,terminal,_=api031.state()
    eligible=[r for r in meta if r["role"] in ("expansion","confirmation") and r["proposition_id"] in cans]
    c.require(len([r for r in eligible if r["role"]=="expansion"])==705,"expansion eligibility drift")
    c.require(len([r for r in eligible if r["role"]=="confirmation"])==696,"confirmation eligibility drift")
    c.require(set(r["proposition_id"] for r in eligible)<=set(rjobs),"native rerank job missing")
    outputs=[];bad=[]
    for i,r in enumerate(eligible,1):
        pid=r["proposition_id"];item=inputs[pid];job=rjobs[pid]
        c.require(job["request_id"] in terminal,"rerank response missing "+pid)
        tr=terminal[job["request_id"]]["transport"];raw=json.loads(tr["body_text"])
        scores={job["passage_ids"][z["index"]]:float(z["relevance_score"]) for z in raw["results"]}
        ids=cans[pid]["candidate_ids"]["C48"]
        c.require(set(ids)<=set(scores),"candidate score missing")
        base=c.baseline_select(ids,scores,passages,item["admission"])
        old=mats[pid]
        same=base["reference"]==old["reference"]
        if not same:bad.append(pid)
        soft=c.softnote_select(ids,scores,passages,item["admission"])
        cov=c.covmmr_select(item["text"],ids,scores,passages,item["admission"])
        outputs.append(dict(id=pid,sid=r["subject_id"],author=r["author_type"],role=r["role"],claim=item["text"],
          baseline_reference=base["reference"],softnote_reference=soft["reference"],covmmr_reference=cov["reference"],
          baseline_ids=base["selected_ids"],softnote_ids=soft["selected_ids"],covmmr_ids=cov["selected_ids"],
          baseline_chars=base["body_characters"],softnote_chars=soft["body_characters"],covmmr_chars=cov["body_characters"],
          softnote_changed=soft["reference"]!=base["reference"],covmmr_changed=cov["reference"]!=base["reference"]))
        if i%200==0:print("prepared",i,flush=True)
    c.require(not bad,"baseline reproduction failed "+str(bad[:5]))
    expansion=[x for x in outputs if x["role"]=="expansion"]
    grouped=defaultdict(list)
    for x in expansion:grouped[(x["sid"],x["author"])].append(x)
    selected={}
    for key,rr in sorted(grouped.items()):
        for x in sorted(rr,key=lambda z:(c.screen_rank(z["id"]),z["id"]))[:10]:selected[x["id"]]=x
    if len(selected)<240:
        rest=[x for x in expansion if x["id"] not in selected]
        for x in sorted(rest,key=lambda z:(c.screen_rank(z["id"]),z["id"]))[:240-len(selected)]:selected[x["id"]]=x
    screen=sorted(selected.values(),key=lambda z:(z["sid"],z["author"],c.screen_rank(z["id"])))
    c.require(len(screen)==240 and len({x["id"] for x in screen})==240,"screen size")
    # Freeze before any GT connection: only claim metadata and evidence are present here.
    logical=[];jobs={};refkey={"baseline":"baseline_reference","softnote":"softnote_reference","covmmr":"covmmr_reference"}
    for x in screen:
        for cond in ("baseline","softnote","covmmr"):
            body=c.score_body(x["claim"],x[refkey[cond]])
            bh=c.body_hash(body);rid="042_screen_"+bh[:32]
            jobs.setdefault(rid,dict(request_id=rid,kind="chat",stage="screen",body=body))
            logical.append(dict(id=x["id"],sid=x["sid"],author=x["author"],condition=cond,request_id=rid,
                                reference_sha256=c.digest(x[refkey[cond]]),reference_chars=len(x[refkey[cond]])))
    jobrows=sorted(jobs.values(),key=lambda j:j["request_id"])
    reservation=sum(c.bound(j) for j in jobrows)
    c.require(reservation<=c.CAP,"screen conservative budget exceeds task cap")
    PLAN.mkdir(parents=True)
    c.jsonl(PLAN/"selector_outputs.jsonl",outputs)
    c.jsonl(PLAN/"screen_cohort_blind.jsonl",[{k:x[k] for k in ("id","sid","author","role","claim")} for x in screen])
    c.jsonl(PLAN/"screen_logical.jsonl",logical)
    c.jsonl(PLAN/"screen_jobs.jsonl",jobrows)
    source_files=[
      R031/"planning_001/claim_metadata.csv",R031/"materials_001/inputs.jsonl",R031/"materials_001/corpus.jsonl",
      R031/"judge_inputs_001/materials.jsonl",R031/"retrieval_001/candidates.jsonl",R031/"retrieval_001/jobs.jsonl",
      c.TASK/"protocol.md",c.TASK/"common042.py",c.TASK/"prepare042.py"]
    c.put(PLAN/"freeze.json",dict(created_utc=c.now(),GT_connected=False,
      eligibility=dict(expansion=705,confirmation=696),screen_n=240,unique_screen_jobs=len(jobrows),
      selector_changes=dict(softnote=sum(x["softnote_changed"] for x in screen),covmmr=sum(x["covmmr_changed"] for x in screen)),
      conservative_screen_reservation_cny=reservation,
      source_sha256={str(p.relative_to(c.ROOT)).replace("\\","/"):c.sha(p) for p in source_files}))
    print("042 planning frozen; eligible",len(outputs),"screen",len(screen),"unique jobs",len(jobrows),
          "soft changes",sum(x["softnote_changed"] for x in screen),"cov changes",sum(x["covmmr_changed"] for x in screen),
          "bound",round(reservation,3),flush=True)

if __name__=="__main__":main()
