"""Analyze 050 six-repeat screen and fixed three-run aggregations."""
from pathlib import Path
from collections import Counter
import json,math,statistics,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/050_repeated_score_aggregation"))
import common050 as c
import run050
LABELS=("Supported","Not Supported","Not Addressed")

def pred_score(scores,lam=2):
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:math.log(max(float(scores[k])/100,1e-6))+(lam if k=="Supported" else 0))

def mean_scores(arr):
    return {k:sum(float(s[k]) for s in arr)/len(arr) for k in LABELS}
def median_scores(arr):
    return {k:statistics.median(float(s[k]) for s in arr) for k in LABELS}
def logmean_pred(arr):
    vals={}
    for k in LABELS:
        vals[k]=sum(math.log(max(float(s[k])/100,1e-6)) for s in arr)/len(arr)+(2 if k=="Supported" else 0)
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:vals[k])
def majority(vals,tiebreak):
    cts=Counter(vals);m=max(cts.values());top=[k for k,v in cts.items() if v==m]
    return top[0] if len(top)==1 else tiebreak

def triplet_preds(rows):
    scores=[r["scores"] for r in rows];u2=[r["U2"] for r in rows];raw=[r["raw"] for r in rows]
    ms=mean_scores(scores);med=median_scores(scores)
    meanp=pred_score(ms,2);medp=pred_score(med,2);logp=logmean_pred(scores)
    vote=majority(u2,meanp)
    rawmaj=majority(raw,pred_score(ms,0))
    cntS=sum(z=="Supported" for z in u2)
    cons2="Supported" if rawmaj!="Supported" and cntS>=2 else rawmaj
    cons3="Supported" if rawmaj!="Supported" and cntS>=3 else rawmaj
    return {"Mean3":meanp,"Median3":medp,"LogMean3":logp,"Vote3":vote,
            "Cons2":cons2,"Cons3":cons3,"RawMaj":rawmaj}

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    _,term=run050.state()
    item_rounds={};round_rows=[]
    for pid,x in cases.items():
        rr=[]
        for rnd in range(6):
            rid=f"050_screen_r{rnd}_"+c.stable("",pid)[:24]
            p=term[rid]["parsed"];sc=p.get("scores")
            c.require(p.get("status") in c.VALID and sc is not None,"invalid screen score "+rid)
            row=dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],cohort_type=x["cohort_type"],
              round=rnd,raw=p.get("verdict"),U0=c.ulabel(sc,0),U2=c.ulabel(sc,2),scores=sc,
              correct_U2=c.ulabel(sc,2)==x["GT"],false_S_U2=x["GT"]!="Supported" and c.ulabel(sc,2)=="Supported",
              correct_raw=p.get("verdict")==x["GT"])
            rr.append(row);round_rows.append(row)
        item_rounds[pid]=rr

    round_summary=[]
    for rnd in range(6):
        z=[r for r in round_rows if r["round"]==rnd]
        round_summary.append(dict(round=rnd,n=len(z),U2_correct=sum(r["correct_U2"] for r in z),
          U2_false_S=sum(r["false_S_U2"] for r in z),raw_correct=sum(r["correct_raw"] for r in z),
          raw_changed_items=sum(len({q["raw"] for q in item_rounds[r["id"]]})>1 for r in z),
          U2_changed_items=sum(len({q["U2"] for q in item_rounds[r["id"]]})>1 for r in z)))
    single_mean_correct=sum(z["U2_correct"] for z in round_summary)/6
    single_mean_false=sum(z["U2_false_S"] for z in round_summary)/6

    tripA={};tripB={};item_diag=[]
    for pid,x in cases.items():
        a=item_rounds[pid][:3];b=item_rounds[pid][3:]
        pa=triplet_preds(a);pb=triplet_preds(b);tripA[pid]=pa;tripB[pid]=pb
        item_diag.append(dict(id=pid,sid=x["sid"],GT=x["GT"],cohort_type=x["cohort_type"],
          raw_unique=len({r["raw"] for r in item_rounds[pid]}),U2_unique=len({r["U2"] for r in item_rounds[pid]}),
          U2_S_count=sum(r["U2"]=="Supported" for r in item_rounds[pid]),
          supported_score_min=min(float(r["scores"]["Supported"]) for r in item_rounds[pid]),
          supported_score_max=max(float(r["scores"]["Supported"]) for r in item_rounds[pid])))

    methods=("Mean3","Median3","LogMean3","Vote3","Cons2","Cons3","RawMaj")
    method_summary=[]
    round0=round_summary[0];round3=round_summary[3]
    ceil_single_false=math.ceil(single_mean_false-1e-12)
    for method in methods:
        predA=[tripA[pid][method] for pid in cases];predB=[tripB[pid][method] for pid in cases]
        gt=[cases[pid]["GT"] for pid in cases]
        corrA=sum(p==g for p,g in zip(predA,gt));corrB=sum(p==g for p,g in zip(predB,gt))
        fsA=sum(g!="Supported" and p=="Supported" for p,g in zip(predA,gt))
        fsB=sum(g!="Supported" and p=="Supported" for p,g in zip(predB,gt))
        agree=sum(a==b for a,b in zip(predA,predB))/len(gt)
        mean_corr=(corrA+corrB)/2;mean_fs=(fsA+fsB)/2
        accuracy=(mean_corr>=single_mean_correct+1.5 and corrA>=round0["U2_correct"]-1 and corrB>=round3["U2_correct"]-1 and fsA<=ceil_single_false and fsB<=ceil_single_false and agree>=.90)
        risk=(mean_fs<=single_mean_false-1.5 and mean_corr>=single_mean_correct-.5 and agree>=.90)
        method_summary.append(dict(method=method,A_correct=corrA,B_correct=corrB,mean_correct=mean_corr,
          A_false_S=fsA,B_false_S=fsB,mean_false_S=mean_fs,AB_agreement=agree,
          single_mean_correct=single_mean_correct,single_mean_false_S=single_mean_false,
          accuracy_pass=bool(accuracy),risk_pass=bool(risk),passes=bool(accuracy or risk)))
    priority={"Vote3":0,"Mean3":1,"Median3":2,"LogMean3":3,"Cons2":4,"Cons3":5,"RawMaj":99}
    promoted=[z for z in method_summary if z["method"]!="RawMaj" and z["passes"]]
    promoted.sort(key=lambda z:(-z["mean_correct"],z["mean_false_S"],-z["AB_agreement"],priority[z["method"]]))
    promoted_names=[z["method"] for z in promoted[:2]]

    subgroup=[]
    for typ in ("historical_conflict","stable_control"):
        ids=[pid for pid,x in cases.items() if x["cohort_type"]==typ]
        for method in ("U2_single_mean",)+methods:
            if method=="U2_single_mean":
                correct=sum(sum(r["correct_U2"] for r in item_rounds[pid])/6 for pid in ids)
                false_s=sum(sum(r["false_S_U2"] for r in item_rounds[pid])/6 for pid in ids)
                subgroup.append(dict(cohort_type=typ,method=method,n=len(ids),mean_correct=correct,mean_false_S=false_s))
            else:
                ca=sum(tripA[pid][method]==cases[pid]["GT"] for pid in ids);cb=sum(tripB[pid][method]==cases[pid]["GT"] for pid in ids)
                fa=sum(cases[pid]["GT"]!="Supported" and tripA[pid][method]=="Supported" for pid in ids)
                fb=sum(cases[pid]["GT"]!="Supported" and tripB[pid][method]=="Supported" for pid in ids)
                subgroup.append(dict(cohort_type=typ,method=method,n=len(ids),mean_correct=(ca+cb)/2,mean_false_S=(fa+fb)/2))

    attempts,_=run050.state()
    result=dict(created_utc=c.now(),screen_n=len(cases),round_summary=round_summary,
      single_mean_correct=single_mean_correct,single_mean_false_S=single_mean_false,
      raw_unstable_items=sum(x["raw_unique"]>1 for x in item_diag),
      U2_unstable_items=sum(x["U2_unique"]>1 for x in item_diag),
      method_summary=method_summary,promoted=promoted_names,subgroup=subgroup,
      cost_cny=sum(a["cost"] for a in attempts),api_attempts=len(attempts),
      http200=sum(a["http_status"]==200 for a in attempts))
    c.put(c.OUT/"screen_analysis.json",result)
    c.csvwrite(c.OUT/"screen_rounds.csv",round_summary)
    c.csvwrite(c.OUT/"screen_methods.csv",method_summary)
    c.csvwrite(c.OUT/"screen_item_diagnostics.csv",item_diag)
    c.csvwrite(c.OUT/"screen_subgroups.csv",subgroup)
    c.put(c.OUT/"screen_decision.json",dict(created_utc=c.now(),promoted=promoted_names,
      stop=not bool(promoted_names),
      rule="accuracy/risk pass across both independent triplets; max2 fixed priority"))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
