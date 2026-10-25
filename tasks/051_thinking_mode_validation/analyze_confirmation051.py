"""Analyze frozen 051 confirmation. No API calls."""
from pathlib import Path
from collections import Counter,defaultdict
import json,re,statistics,sys
from sklearn.metrics import matthews_corrcoef
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051
LABELS=("Supported","Not Supported","Not Addressed")
CONDS=("N-S","N-V","T-S","T-V")

def valid(p): return p.get("status") in c.VALID
def native_usage(rec):
    try:
        n=json.loads(rec["transport"]["body_text"]);u=n.get("usage") or {}
        d=u.get("completion_tokens_details") or {}
        return dict(prompt=u.get("prompt_tokens"),completion=u.get("completion_tokens"),
          reasoning=d.get("reasoning_tokens",u.get("reasoning_tokens")))
    except Exception:return dict(prompt=None,completion=None,reasoning=None)

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"confirmation_cases_frozen.jsonl")}
    jobs=c.lines(c.OUT/"confirmation_jobs.jsonl")
    attempts,term=run051.state()
    rows=[];by={}
    for pid,x in cases.items():
        h=c.stable("",pid)[:24]
        for cond in CONDS:
            rid="051_conf_"+cond.replace("-","_")+"_"+h
            rec=term[rid];p=rec["parsed"];sc=p.get("scores")
            core=valid(p)
            raw=p.get("verdict") if core else None
            main=(c.c020.decision(sc,2) if cond=="N-S" and core else raw)
            u0=c.c020.decision(sc,0) if core and sc else None
            u2=c.c020.decision(sc,2) if core and sc else None
            usage=native_usage(rec)
            row=dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],condition=cond,status=p.get("status"),
              raw=raw,main=main,U0=u0,U2=u2,correct=(main==x["GT"]) if main else False,
              false_S=bool(main=="Supported" and x["GT"]!="Supported"),reasoning_present=p.get("reasoning_present"),
              reasoning_tokens=usage["reasoning"],prompt_tokens=usage["prompt"],completion_tokens=usage["completion"],
              reason=(p.get("parsed") or {}).get("reason"))
            rows.append(row);by[(pid,cond)]=row

    summary=[]
    for cond in CONDS:
        rr=[by[(pid,cond)] for pid in cases]
        val=[r for r in rr if r["main"] is not None]
        gt=[r["GT"] for r in val];pr=[r["main"] for r in val]
        z=dict(condition=cond,n=len(rr),valid_n=len(val),correct=sum(r["correct"] for r in rr),
          missing_as_error_correct=sum(r["correct"] for r in rr),false_S=sum(r["false_S"] for r in rr),
          PA_valid=sum(a==b for a,b in zip(gt,pr))/len(val),
          MCC_valid=float(matthews_corrcoef(gt,pr)) if len(set(gt))>1 and len(set(pr))>1 else 0.0,
          reasoning_present=sum(bool(r["reasoning_present"]) for r in rr))
        for lab in LABELS:
            den=sum(r["GT"]==lab for r in rr)
            z["correct_"+lab.replace(" ","_")]=sum(r["GT"]==lab and r["main"]==lab for r in rr)
            z["recall_"+lab.replace(" ","_")]=z["correct_"+lab.replace(" ","_")]/den
        vals=[r["reasoning_tokens"] for r in rr if isinstance(r["reasoning_tokens"],int)]
        z["reasoning_tokens_mean"]=sum(vals)/len(vals) if vals else None
        z["reasoning_tokens_median"]=statistics.median(vals) if vals else None
        summary.append(z)

    comparisons=[]
    def comp(a,b,a_field="main",b_field="main",require_valid=True):
        rescue=[];harm=[];same=0;n=0
        for pid,x in cases.items():
            ra=by[(pid,a)];rb=by[(pid,b)]
            pa=ra[a_field];pb=rb[b_field]
            if require_valid and (pa is None or pb is None):continue
            n+=1
            ac=pa==x["GT"];bc=pb==x["GT"]
            if ac and not bc:rescue.append(pid)
            elif bc and not ac:harm.append(pid)
            else:same+=1
        return dict(a=a,b=b,a_field=a_field,b_field=b_field,n=n,rescue=len(rescue),harm=len(harm),
          net=len(rescue)-len(harm),ties=same,rescue_patients=len({cases[i]["sid"] for i in rescue}),
          harm_patients=len({cases[i]["sid"] for i in harm}),rescue_ids=rescue,harm_ids=harm)
    comparisons.append(comp("T-V","N-S"))
    comparisons.append(comp("T-V","N-V"))
    comparisons.append(comp("T-S","N-S","raw","raw"))
    comparisons.append(comp("T-V","T-S","raw","raw"))

    patient_rows=[]
    for sid in sorted({x["sid"] for x in cases.values()}):
        ids=[pid for pid,x in cases.items() if x["sid"]==sid]
        for pair in (("T-V","N-S"),("T-V","N-V")):
            a,b=pair
            ca=sum(by[(pid,a)]["main"]==cases[pid]["GT"] for pid in ids)
            cb=sum(by[(pid,b)]["main"]==cases[pid]["GT"] for pid in ids)
            fsa=sum(by[(pid,a)]["false_S"] for pid in ids)
            fsb=sum(by[(pid,b)]["false_S"] for pid in ids)
            patient_rows.append(dict(sid=sid,a=a,b=b,n=len(ids),a_correct=ca,b_correct=cb,
              delta_correct=ca-cb,a_false_S=fsa,b_false_S=fsb,delta_false_S=fsa-fsb))

    author_rows=[]
    for author in sorted({x["author"] for x in cases.values()}):
        ids=[pid for pid,x in cases.items() if x["author"]==author]
        for cond in CONDS:
            rr=[by[(pid,cond)] for pid in ids]
            author_rows.append(dict(author=author,condition=cond,n=len(rr),
              correct=sum(r["correct"] for r in rr),false_S=sum(r["false_S"] for r in rr),
              S_recall=sum(r["GT"]=="Supported" and r["main"]=="Supported" for r in rr)/max(1,sum(r["GT"]=="Supported" for r in rr)),
              NS_recall=sum(r["GT"]=="Not Supported" and r["main"]=="Not Supported" for r in rr)/max(1,sum(r["GT"]=="Not Supported" for r in rr)),
              NA_recall=sum(r["GT"]=="Not Addressed" and r["main"]=="Not Addressed" for r in rr)/max(1,sum(r["GT"]=="Not Addressed" for r in rr))))

    # Structural citation audit for final T-V explanations.
    citation_rows=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];rec=term["051_conf_T_V_"+h];p=rec["parsed"]
        checks=(p.get("parsed") or {}).get("checks") or []
        nums=[int(z) for z in re.findall(r"(?m)^(\d+)\. Date:",x["reference"])]
        valid_ids=set(nums)
        cited=[e for ck in checks for e in (ck.get("evidence_ids",[]) if isinstance(ck,dict) else []) if isinstance(e,int)]
        citation_rows.append(dict(id=pid,sid=x["sid"],GT=x["GT"],status=p.get("status"),
          checks_n=len(checks),citations_n=len(cited),all_citations_exist=all(e in valid_ids for e in cited),
          has_any_citation=bool(cited),reason_nonempty=bool((p.get("parsed") or {}).get("reason"))))

    sm={z["condition"]:z for z in summary}
    tv=sm["T-V"];ns=sm["N-S"];nv=sm["N-V"]
    tv_ns=next(z for z in comparisons if z["a"]=="T-V" and z["b"]=="N-S")
    tv_nv=next(z for z in comparisons if z["a"]=="T-V" and z["b"]=="N-V")
    patient_tv_ns=[r for r in patient_rows if r["a"]=="T-V" and r["b"]=="N-S"]
    final_assessment=dict(
      TV_vs_NS_net=tv_ns["net"],TV_vs_NV_net=tv_nv["net"],
      TV_false_S_delta_vs_NS=tv["false_S"]-ns["false_S"],
      TV_false_S_delta_vs_NV=tv["false_S"]-nv["false_S"],
      TV_patient_positive=sum(r["delta_correct"]>0 for r in patient_tv_ns),
      TV_patient_negative=sum(r["delta_correct"]<0 for r in patient_tv_ns),
      TV_patient_tie=sum(r["delta_correct"]==0 for r in patient_tv_ns),
      TV_all_citations_exist=sum(r["all_citations_exist"] for r in citation_rows),
      TV_has_any_citation=sum(r["has_any_citation"] for r in citation_rows))

    result=dict(created_utc=c.now(),n=len(cases),summary=summary,comparisons=comparisons,
      patient_rows=patient_rows,author_rows=author_rows,citation_audit=citation_rows,
      final_assessment=final_assessment,
      cost_cny=sum(a["cost"] for a in attempts),api_attempts=len(attempts),
      http200=sum(a["http_status"]==200 for a in attempts))
    c.put(c.OUT/"confirmation_analysis.json",result)
    c.csvwrite(c.OUT/"confirmation_predictions.csv",rows)
    c.csvwrite(c.OUT/"confirmation_summary.csv",summary)
    c.csvwrite(c.OUT/"confirmation_comparisons.csv",comparisons)
    c.csvwrite(c.OUT/"confirmation_patients.csv",patient_rows)
    c.csvwrite(c.OUT/"confirmation_authors.csv",author_rows)
    c.csvwrite(c.OUT/"confirmation_citation_audit.csv",citation_rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
