"""Recover 044 evaluation from frozen jobs/mapping and immutable receipts.
Does not regenerate method, model, choices, jobs, labels, or API answers.
Eight interrupted request-without-receipt outcomes remain unknown and are never repeated.
"""
from pathlib import Path
import sys,json,hashlib,csv,math
from collections import Counter,defaultdict
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/044_incremental_evidence_recovery"
DEST=OUT/"results_recovery_001"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
from verifact_research.evaluation import evaluate,paired_compare
LABELS=("Supported","Not Supported","Not Addressed")
VALID=("valid","valid_with_format_anomaly")

def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def dhex(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def csvwrite(p,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r));p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def decision(scores,lam):
    order=("Not Supported","Not Addressed","Supported")
    return max(order,key=lambda k:math.log(max(float(scores[k])/100,1e-6))+(lam if k=="Supported" else 0))
def receipt(job):
    prefix=dhex(job["request_id"])[:24]
    found=[];unknown=[]
    for n in (1,2,3):
        d=OUT/"attempts"/f"{prefix}_{n:02}"
        if not d.exists():continue
        rp=d/"receipt.json"
        if not rp.exists():unknown.append(str(d.relative_to(ROOT)));continue
        rec=read(rp);tr=rec["transport"]
        if tr.get("http_status")==200:found.append((tr,rp))
    if len(found)>1:raise RuntimeError("duplicate HTTP200 "+job["request_id"])
    return (found[0] if found else (None,None)),unknown

def main():
    if DEST.exists():raise RuntimeError("results_recovery_001 exists")
    DEST.mkdir(parents=True)
    cases={x["id"]:x for x in lines(OUT/"planning_001/eval_cases.jsonl")}
    mapping=lines(OUT/"eval_score/mapping.jsonl");jobs=lines(OUT/"eval_score/jobs.jsonl")
    byjob={j["request_id"]:j for j in jobs};terminal={};unknown={}
    parser=Counter();usage={};cost=0.0
    for j in jobs:
        (tr,rp),unk=receipt(j)
        if unk:unknown[j["request_id"]]=unk
        if tr is None:continue
        p=core024.parse(tr,True)
        if p.get("model_returned") not in (None,"deepseek-v4-flash-0731"):
            p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_model")
        terminal[j["request_id"]]=p;parser[p["status"]]+=1
        u=json.loads(tr["body_text"]).get("usage",{});usage[j["request_id"]]=u
        if isinstance(u.get("prompt_tokens"),int) and isinstance(u.get("completion_tokens"),int):
            cost+=(u["prompt_tokens"]*3+u["completion_tokens"]*9)/1e6
    rows=[]
    for m in mapping:
        p=terminal.get(m["request_id"]);r=dict(m,status=p["status"] if p else ("unknown_no_receipt" if m["request_id"] in unknown else "missing"))
        if p and p["status"] in VALID:
            sc=p["scores"];r.update(Score=p["verdict"],U0=decision(sc,0),U2=decision(sc,2),scores=sc,
              reason=(p.get("parsed") or {}).get("reason"),checks=(p.get("parsed") or {}).get("checks"))
        rows.append(r)
    put(DEST/"score_rows.json",rows)
    round0=[r for r in rows if r["round"]==0];by={(r["id"],r["condition"]):r for r in round0}
    names=("base","rank","learned")
    ids=sorted(i for i in cases if all(by.get((i,n),{}).get("Score") for n in names))
    missing=[dict(id=i,condition=n,status=by.get((i,n),{}).get("status")) for i in cases for n in names if not by.get((i,n),{}).get("Score")]
    put(DEST/"coverage.json",dict(planned_claims=len(cases),common_valid_claims=len(ids),common_ids=ids,
      missing=missing,unknown_request_ids=sorted(unknown),unknown_request_count=len(unknown),
      valid_by_condition={n:sum(bool(by.get((i,n),{}).get("Score")) for i in cases) for n in names},
      parser_status=dict(parser)))

    metrics=[];full={}
    for scope in ("all","human","llm"):
        use=[i for i in ids if scope=="all" or cases[i]["author"]==scope]
        if not use:continue
        cohort=[dict(proposition_id=i,subject_id=cases[i]["sid"],human_gt=cases[i]["GT"]) for i in use]
        for n in names:
            for lab in ("Score","U0","U2"):
                pred=[dict(proposition_id=i,verdict=by[(i,n)][lab]) for i in use]
                e=evaluate(cohort,pred,profile="research_patient",iterations=1000);full[f"{scope}/{n}/{lab}"]=e
                row=dict(scope=scope,condition=n,label=lab,n=len(use),
                  correct=sum(by[(i,n)][lab]==cases[i]["GT"] for i in use),
                  PA=e["percent_agreement"],MCC=e["mcc"],AC1=e["gwet_ac1"],
                  false_S=e["per_class"]["Supported"]["fp"],
                  final_vs_Score_disagreement=sum(by[(i,n)][lab]!=by[(i,n)]["Score"] for i in use))
                for L,s in zip(LABELS,("S","NS","NA")):row[s+"_recall"]=e["per_class"][L]["recall"]
                metrics.append(row)
    csvwrite(DEST/"metrics.csv",metrics);put(DEST/"metrics_full.json",full)
    pairs=[];pairfull={}
    cohort=[dict(proposition_id=i,subject_id=cases[i]["sid"],human_gt=cases[i]["GT"]) for i in ids]
    for a,b in (("base","rank"),("base","learned"),("rank","learned")):
        for lab in ("Score","U0","U2"):
            pa=[dict(proposition_id=i,verdict=by[(i,a)][lab]) for i in ids]
            pb=[dict(proposition_id=i,verdict=by[(i,b)][lab]) for i in ids]
            pc=paired_compare(cohort,pa,pb,iterations=1000);pairfull[f"{b}-{a}/{lab}"]=pc
            fixes=sum(by[(i,a)][lab]!=cases[i]["GT"] and by[(i,b)][lab]==cases[i]["GT"] for i in ids)
            harms=sum(by[(i,a)][lab]==cases[i]["GT"] and by[(i,b)][lab]!=cases[i]["GT"] for i in ids)
            ds={}
            for sid in sorted({cases[i]["sid"] for i in ids}):
                ds[sid]=sum(int(by[(i,b)][lab]==cases[i]["GT"])-int(by[(i,a)][lab]==cases[i]["GT"]) for i in ids if cases[i]["sid"]==sid)
            row=dict(baseline=a,candidate=b,label=lab,n=len(ids),rescued=fixes,harmed=harms,net_correct=fixes-harms,
              patient_positive=sum(v>0 for v in ds.values()),patient_negative=sum(v<0 for v in ds.values()),patient_tie=sum(v==0 for v in ds.values()),
              false_S_delta=sum(int(by[(i,b)][lab]=="Supported")-int(by[(i,a)][lab]=="Supported") for i in ids if cases[i]["GT"]!="Supported"))
            for key,short in (("percent_agreement","PA"),("mcc","MCC"),("gwet_ac1","AC1")):
                z=pc["metrics"][key];row[short+"_delta"]=z["delta"];row[short+"_lo"],row[short+"_hi"]=z["ci95"]
            pairs.append(row)
    csvwrite(DEST/"paired.csv",pairs);put(DEST/"paired_full.json",pairfull)
    lookup={(r["id"],r["condition"],r["round"]):r for r in rows};repids=sorted({r["id"] for r in rows if r["round"]==1})
    reps=[]
    for n in names:
        valid=[i for i in repids if lookup.get((i,n,0),{}).get("Score") and lookup.get((i,n,1),{}).get("Score")]
        for lab in ("Score","U0","U2"):
            reps.append(dict(condition=n,label=lab,n=len(valid),
              changed=sum(lookup[(i,n,0)][lab]!=lookup[(i,n,1)][lab] for i in valid),
              r0_correct=sum(lookup[(i,n,0)][lab]==cases[i]["GT"] for i in valid),
              r1_correct=sum(lookup[(i,n,1)][lab]==cases[i]["GT"] for i in valid)))
    csvwrite(DEST/"repeats.csv",reps)

    choices=lines(OUT/"model/eval_choices.jsonl");choice_counts=Counter(x["choice"] for x in choices)
    deploy=[]
    for n in names:
        vals=[]
        seen=[]
        for i in cases:
            r=by.get((i,n));rid=r["request_id"] if r else None;u=usage.get(rid,{})
            if isinstance(u.get("prompt_tokens"),int):vals.append(u["prompt_tokens"])
        deploy.append(dict(condition=n,n=len(vals),mean_prompt_tokens=float(np.mean(vals)) if vals else None,
          median_prompt_tokens=float(np.median(vals)) if vals else None,online_Judge_calls=1))
    csvwrite(DEST/"deployment_tokens.csv",deploy)
    summary=dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      evaluation_planned=696,common_valid=len(ids),patients=len({cases[i]["sid"] for i in ids}),
      choice_counts=dict(choice_counts),unknown_request_count=len(unknown),parser_status=dict(parser),
      metrics=[x for x in metrics if x["scope"]=="all"],paired=pairs,repeats=reps,deployment_tokens=deploy,
      eval_score_received_cost_cny=cost,method_model_summary=read(OUT/"model/summary.json"),
      note="Recovered from frozen eval jobs/mapping and immutable receipts; 8 interrupted requests without receipt remain unknown and were not repeated.")
    put(DEST/"summary.json",summary);print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
