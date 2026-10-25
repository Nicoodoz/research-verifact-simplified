"""Analyze 051 clinical screen, repeats, semantics, thinking usage and gates."""
from pathlib import Path
from collections import Counter,defaultdict
import json,statistics,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051
LABELS=("Supported","Not Supported","Not Addressed")
CONDS=("N-S","N-V","T-S","T-V")

def core(term,rid):
    p=term[rid]["parsed"];c.require(p.get("status") in c.VALID,"invalid "+rid)
    return p

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    sem={x["id"]:x for x in c.lines(c.OUT/"semantic_cases.jsonl")}
    freeze=c.read(c.OUT/"screen_freeze.json")
    frozen_jobs=c.lines(c.OUT/"screen_jobs.jsonl")
    repeat_ids={j["id"] for j in frozen_jobs if str(j.get("condition","")).endswith("_repeat") and j["id"] in cases}
    c.require(len(repeat_ids)==6,"expected six frozen clinical repeat IDs")
    attempts,term=run051.state()
    by={};rows=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24]
        for cond in CONDS:
            p=core(term,"051_"+cond.replace("-","_")+"_"+h)
            scores=p.get("scores")
            pred_raw=p["verdict"]
            pred_main=c.c020.decision(scores,lam=2) if cond=="N-S" else pred_raw
            pred_u0=c.c020.decision(scores,lam=0) if scores else None
            pred_u2=c.c020.decision(scores,lam=2) if scores else None
            r=dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],condition=cond,
              raw=pred_raw,main=pred_main,U0=pred_u0,U2=pred_u2,
              raw_correct=pred_raw==x["GT"],main_correct=pred_main==x["GT"],
              main_false_S=x["GT"]!="Supported" and pred_main=="Supported",
              reasoning_present=p.get("reasoning_present"),reasoning_tokens=p.get("reasoning_tokens"),
              reasoning_chars=p.get("reasoning_chars"),adherence=";".join(p.get("adherence",[])))
            rows.append(r);by[(pid,cond)]=r

    summary=[]
    for cond in CONDS:
        rr=[by[(pid,cond)] for pid in cases]
        z=dict(condition=cond,n=len(rr),correct=sum(r["main_correct"] for r in rr),
          raw_correct=sum(r["raw_correct"] for r in rr),false_S=sum(r["main_false_S"] for r in rr),
          reasoning_present=sum(bool(r["reasoning_present"]) for r in rr))
        for lab in LABELS:
            den=sum(r["GT"]==lab for r in rr)
            z["correct_"+lab.replace(" ","_")]=sum(r["GT"]==lab and r["main"]==lab for r in rr)
            z["recall_"+lab.replace(" ","_")]=z["correct_"+lab.replace(" ","_")]/den
        rt=[r["reasoning_tokens"] for r in rr if isinstance(r["reasoning_tokens"],int)]
        z["reasoning_tokens_mean"]=sum(rt)/len(rt) if rt else None
        z["reasoning_tokens_median"]=statistics.median(rt) if rt else None
        summary.append(z)

    sm={z["condition"]:z for z in summary}
    comparisons=[]
    def comp(a,b,a_key="main",b_key="main"):
        rescue=[];harm=[]
        for pid in cases:
            ra=by[(pid,a)];rb=by[(pid,b)]
            ac=(ra[a_key]==cases[pid]["GT"]);bc=(rb[b_key]==cases[pid]["GT"])
            if ac and not bc:rescue.append(pid)
            if bc and not ac:harm.append(pid)
        return dict(a=a,b=b,rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),
          rescue_patients=len({cases[i]["sid"] for i in rescue}),harm_patients=len({cases[i]["sid"] for i in harm}),
          rescue_ids=rescue,harm_ids=harm)
    comparisons.append(comp("T-V","N-S"))
    comparisons.append(comp("T-V","N-V"))
    # raw-to-raw thinking effect within scoring interface.
    comparisons.append(comp("T-S","N-S","raw","raw"))
    comparisons.append(comp("T-V","T-S","raw","raw"))

    # Prespecified T-V gate.
    base=sm["N-S"];tv=sm["T-V"];nv=sm["N-V"]
    tv_vs_base=next(z for z in comparisons if z["a"]=="T-V" and z["b"]=="N-S")
    tv_vs_nv=next(z for z in comparisons if z["a"]=="T-V" and z["b"]=="N-V")
    class_diffs={lab:tv["correct_"+lab.replace(" ","_")]-base["correct_"+lab.replace(" ","_")] for lab in LABELS}
    accuracy_pass=(tv_vs_base["net"]>=3 and tv_vs_base["rescue_patients"]>=3 and tv["false_S"]<=base["false_S"]
      and min(class_diffs.values())>=-2 and tv_vs_nv["net"]>=2)
    # risk improvements by patient.
    fixed_false=[]
    new_false=[]
    for pid in cases:
        b=by[(pid,"N-S")];t=by[(pid,"T-V")]
        if b["main_false_S"] and not t["main_false_S"]:fixed_false.append(pid)
        if (not b["main_false_S"]) and t["main_false_S"]:new_false.append(pid)
    risk_patients=len({cases[i]["sid"] for i in fixed_false})
    risk_pass=(base["false_S"]-tv["false_S"]>=2 and tv["correct"]>=base["correct"]-1 and risk_patients>=2 and tv["correct"]>=nv["correct"]-1)

    # T-S raw auxiliary gate.
    ns_raw_correct=sum(by[(pid,"N-S")]["raw_correct"] for pid in cases)
    ts_raw_correct=sum(by[(pid,"T-S")]["raw_correct"] for pid in cases)
    ts_raw_false=sum(cases[pid]["GT"]!="Supported" and by[(pid,"T-S")]["raw"]=="Supported" for pid in cases)
    ns_raw_false=sum(cases[pid]["GT"]!="Supported" and by[(pid,"N-S")]["raw"]=="Supported" for pid in cases)
    tscomp=next(z for z in comparisons if z["a"]=="T-S" and z["b"]=="N-S")
    ts_pass=(tscomp["net"]>=3 and tscomp["rescue_patients"]>=3 and ts_raw_false<=ns_raw_false and ts_raw_correct<=tv["correct"]+1)

    repeats=[]
    for pid in sorted(repeat_ids):
        h=c.stable("",pid)[:24]
        for cond in CONDS:
            p=core(term,"051_"+cond.replace("-","_")+"_rep_"+h)
            scores=p.get("scores")
            pred=c.c020.decision(scores,2) if cond=="N-S" else p["verdict"]
            repeats.append(dict(id=pid,sid=cases[pid]["sid"],condition=cond,
              first=by[(pid,cond)]["main"],repeat=pred,changed=pred!=by[(pid,cond)]["main"],
              repeat_reasoning_present=p.get("reasoning_present"),repeat_reasoning_tokens=p.get("reasoning_tokens")))
    repeat_summary=[]
    for cond in CONDS:
        rr=[r for r in repeats if r["condition"]==cond]
        repeat_summary.append(dict(condition=cond,n=len(rr),changed=sum(r["changed"] for r in rr),
          agreement=1-sum(r["changed"] for r in rr)/len(rr)))

    sem_rows=[]
    for pid,x in sem.items():
        h=c.stable("",pid)[:24]
        for cond in ("N-V","T-V"):
            p=core(term,"051_sem_"+cond.replace("-","_")+"_"+h)
            sem_rows.append(dict(id=pid,group=x["group"],expected=x["expected"],condition=cond,
              pred=p["verdict"],correct=p["verdict"]==x["expected"],
              reasoning_present=p.get("reasoning_present"),reasoning_tokens=p.get("reasoning_tokens")))
    sem_summary=[]
    for cond in ("N-V","T-V"):
        rr=[r for r in sem_rows if r["condition"]==cond]
        groups=defaultdict(list)
        for r in rr:groups[r["group"]].append(r)
        sem_summary.append(dict(condition=cond,n=len(rr),correct=sum(r["correct"] for r in rr),
          groups_both_correct=sum(all(z["correct"] for z in vals) for vals in groups.values()),
          groups_total=len(groups)))
    sem_tv=next(z for z in sem_summary if z["condition"]=="T-V")
    sem_nv=next(z for z in sem_summary if z["condition"]=="N-V")
    semantic_reverse=sem_tv["groups_both_correct"]<=sem_nv["groups_both_correct"]-3

    # Cost by condition, including preflight and repeats/semantics.
    jobs={j["request_id"]:j for j in c.lines(c.OUT/"preflight_jobs.jsonl")+c.lines(c.OUT/"screen_jobs.jsonl")}
    cost_by=defaultdict(float);n_by=Counter()
    for a in attempts:
        j=jobs.get(a["request_id"])
        if not j:continue
        key=j["condition"]
        cost_by[key]+=a["cost"];n_by[key]+=1
    cost_rows=[dict(condition=k,calls=n_by[k],cost_cny=cost_by[k]) for k in sorted(cost_by)]

    promoted=[]
    if (accuracy_pass or risk_pass) and not semantic_reverse:promoted.append("T-V")
    if ts_pass:promoted.append("T-S_raw")

    tv_repeat=next(z for z in repeat_summary if z["condition"]=="T-V")
    needs_stability_extension=False
    if "T-V" in promoted and tv_repeat["changed"]>1:
        promoted.remove("T-V");needs_stability_extension=True

    result=dict(created_utc=c.now(),clinical_n=len(cases),summary=summary,comparisons=comparisons,
      class_diffs_TV_vs_NS_U2=class_diffs,fixed_false_S_ids=fixed_false,new_false_S_ids=new_false,
      gates=dict(TV_accuracy=bool(accuracy_pass),TV_risk=bool(risk_pass),TS_raw=bool(ts_pass),
        semantic_reverse=bool(semantic_reverse),needs_stability_extension=bool(needs_stability_extension)),
      repeat_summary=repeat_summary,semantic_summary=sem_summary,promoted=promoted,
      cost_by_condition=cost_rows,cost_cny=sum(a["cost"] for a in attempts),
      api_attempts=len(attempts),http200=sum(a["http_status"]==200 for a in attempts))
    c.put(c.OUT/"screen_analysis.json",result)
    c.csvwrite(c.OUT/"screen_predictions.csv",rows)
    c.csvwrite(c.OUT/"screen_summary.csv",summary)
    c.csvwrite(c.OUT/"screen_comparisons.csv",comparisons)
    c.csvwrite(c.OUT/"screen_repeats.csv",repeats)
    c.csvwrite(c.OUT/"semantic_results.csv",sem_rows)
    c.csvwrite(c.OUT/"semantic_summary.csv",sem_summary)
    c.csvwrite(c.OUT/"costs.csv",cost_rows)
    c.put(c.OUT/"screen_decision.json",dict(created_utc=c.now(),promoted=promoted,
      needs_stability_extension=needs_stability_extension,
      stop=not bool(promoted) and not needs_stability_extension,
      rules="T-V accuracy/risk + thinking-vs-NV + semantic safeguard + repeat; T-S raw auxiliary gate"))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
