"""Freeze 044 patient split, local append options, blind utility-training sample and Judge jobs."""
import json,sys
from collections import defaultdict,Counter
import common044 as c

R031=c.ROOT/"outputs/031_training_expansion_confirmation"
R042=c.ROOT/"outputs/042_coverage_aware_evidence_packing"
PLAN=c.OUT/"planning_001"

def rerank_scores(job):
    prefix=c.digest(job["request_id"])[:24]
    hits=sorted((R031/"attempts").glob(prefix+"_*"))
    good=[]
    for d in hits:
        rp=d/"receipt.json"
        if not rp.exists():continue
        rec=c.read(rp);tr=rec["transport"]
        if tr.get("http_status")==200:good.append(tr)
    c.require(len(good)==1,"rerank terminal receipt count "+job["request_id"])
    raw=json.loads(good[0]["body_text"])
    return {job["passage_ids"][z["index"]]:float(z["relevance_score"]) for z in raw["results"]}

def balanced_sample(rows,n):
    groups=defaultdict(list)
    for x in rows:groups[(x["sid"],x["author"])].append(x)
    for k in groups:groups[k].sort(key=lambda z:(c.stable_hash("044/train-sample/v1:",z["id"]),z["id"]))
    out=[];pos=Counter()
    keys=sorted(groups,key=lambda k:c.stable_hash("044/train-group/v1:","|".join(k)))
    while len(out)<n:
        progressed=False
        for k in keys:
            i=pos[k]
            if i<len(groups[k]):
                out.append(groups[k][i]);pos[k]+=1;progressed=True
                if len(out)==n:break
        c.require(progressed,"insufficient training sample")
    return out
def main():
    c.require(not PLAN.exists(),"planning exists")
    selector={x["id"]:x for x in c.lines(R042/"planning_001/selector_outputs.jsonl")}
    eligible=list(selector.values())
    c.require(Counter(x["role"] for x in eligible)==Counter({"expansion":705,"confirmation":696}),"eligibility drift")
    exp=[x for x in eligible if x["role"]=="expansion"]
    patients=sorted({x["sid"] for x in exp},key=lambda s:c.stable_hash("044/split/v1:",s))
    c.require(len(patients)==10,"eligible expansion patient count")
    train_patients=patients[:7];screen_patients=patients[7:]
    train_pool=[x for x in exp if x["sid"] in train_patients];screen=[x for x in exp if x["sid"] in screen_patients]
    c.require(len(train_pool)==513 and len(screen)==192,"split count drift")
    train=balanced_sample(train_pool,240)

    inputs={r["proposition_id"]:r for r in c.lines(R031/"materials_001/inputs.jsonl")}
    passages={r["passage_id"]:r for r in c.lines(R031/"materials_001/corpus.jsonl")}
    cans={r["proposition_id"]:r for r in c.lines(R031/"retrieval_001/candidates.jsonl")}
    rjobs={r["proposition_id"]:r for r in c.lines(R031/"retrieval_001/jobs.jsonl")}

    cases=[];reproduced=0
    for n,x in enumerate(eligible,1):
        pid=x["id"];item=inputs[pid];job=rjobs[pid]
        scores=rerank_scores(job)
        candidate_ids=cans[pid]["candidate_ids"]["C48"]
        base=c.pc.select_evidence(candidate_ids,scores,passages,item["admission"],cap=8000,max_items=16,max_per_note=2)
        c.require(base["reference"]==x["baseline_reference"],"baseline reproduction "+pid);reproduced+=1
        options=c.build_options(item["text"],candidate_ids,scores,base["selected_ids"],passages,base["selection_skips"])
        ranked=sorted(candidate_ids,key=lambda p:(-scores[p],p))
        refs={};added_ids={};features={}
        for name,pids in options.items():
            refs[name],added_ids[name]=c.append_reference(base["reference"],pids,passages)
            features[name]=c.option_features(item["text"],name,pids,scores,ranked,base["selected_ids"],passages)
        cases.append(dict(id=pid,sid=x["sid"],author=x["author"],role=x["role"],claim=item["text"],
          A_reference=base["reference"],A_ids=base["selected_ids"],options=options,references=refs,added_ids=added_ids,features=features))
        if n%300==0:print("prepared",n,flush=True)
    train_ids={x["id"] for x in train};logical=[];jobs={}
    for x in cases:
        if x["id"] not in train_ids:continue
        refs={"A":x["A_reference"],**x["references"]}
        for cond,ref in refs.items():
            body=c.score_body(x["claim"],ref);rid="044_train_"+c.body_hash(body)[:32]
            jobs.setdefault(rid,dict(request_id=rid,kind="score",model_key="deepseek",stage="train",body=body))
            logical.append(dict(id=x["id"],sid=x["sid"],author=x["author"],condition=cond,request_id=rid,
              reference_sha256=c.digest(ref)))
    jobrows=sorted(jobs.values(),key=lambda j:j["request_id"])
    bound=sum(c.bound(j) for j in jobrows);c.require(bound<c.CAP,"training conservative bound exceeds task cap")

    PLAN.mkdir(parents=True)
    c.jsonl(PLAN/"cases.jsonl",cases)
    c.jsonl(PLAN/"train_cohort_blind.jsonl",[{k:x[k] for k in ("id","sid","author","role","claim")} for x in train])
    c.jsonl(PLAN/"screen_cohort_blind.jsonl",[{k:x[k] for k in ("id","sid","author","role","claim")} for x in screen])
    c.jsonl(PLAN/"train_logical.jsonl",logical);c.jsonl(PLAN/"train_jobs.jsonl",jobrows)
    feature_keys=sorted(next(iter(cases))["features"]["simple"].keys());c.put(PLAN/"feature_schema.json",dict(keys=feature_keys))
    sources=[R042/"planning_001/selector_outputs.jsonl",R031/"materials_001/inputs.jsonl",R031/"materials_001/corpus.jsonl",
      R031/"retrieval_001/candidates.jsonl",R031/"retrieval_001/jobs.jsonl",c.TASK/"protocol.md",c.TASK/"common044.py",c.TASK/"prepare044.py"]
    c.put(PLAN/"freeze.json",dict(created_utc=c.now(),eligible_n=len(eligible),baseline_reproduced=reproduced,
      train_patients=train_patients,screen_patients=screen_patients,train_pool_n=len(train_pool),train_sample_n=len(train),screen_n=len(screen),
      confirmation_n=696,GT_connected=False,train_unique_jobs=len(jobrows),train_bound_cny=bound,
      source_sha256={str(p.relative_to(c.ROOT)).replace("\\","/"):c.sha(p) for p in sources}))
    print("044 planning frozen",len(train_patients),"train patients",len(train),"train claims",len(screen),"screen",
          "unique jobs",len(jobrows),"bound",round(bound,3),flush=True)

if __name__=="__main__":main()
