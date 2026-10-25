"""Analyze 043 paired mechanism effects and reason audits. No API calls."""
from collections import Counter,defaultdict
import math
import common043 as c
import api043

PLAN=c.OUT/"planning_001";AUD=c.OUT/"audit_001";OUT=c.OUT/"analysis_001"

def paired(by,a,b,key):
    ids=sorted(set(pid for pid,cond in by if cond==a)&set(pid for pid,cond in by if cond==b))
    rescue=harm=0;delta_by_patient=defaultdict(int)
    for pid in ids:
        x=by[(pid,a)];y=by[(pid,b)]
        xa=x[key]=="Supported";yb=y[key]=="Supported"
        if (not xa) and yb:rescue+=1;delta_by_patient[x["sid"]]+=1
        elif xa and (not yb):harm+=1;delta_by_patient[x["sid"]]-=1
    disc=rescue+harm
    try:
        from scipy.stats import binomtest
        p=float(binomtest(rescue,disc,.5).pvalue) if disc else 1.0
    except Exception:p=None
    dirs=Counter("positive" if v>0 else "negative" if v<0 else "tie" for v in delta_by_patient.values())
    # Include patients with no discordance as ties.
    pats=set(by[(pid,a)]["sid"] for pid in ids)
    dirs["tie"]+=len(pats)-len(delta_by_patient)
    return dict(A=a,B=b,prediction=key,n=len(ids),rescue_nonS_to_S=rescue,harm_S_to_nonS=harm,
      net_S=rescue-harm,discordant=disc,exact_binomial_p=p,
      patient_positive=dirs["positive"],patient_negative=dirs["negative"],patient_tie=dirs["tie"])

def main():
    c.require(not OUT.exists(),"analysis exists");OUT.mkdir(parents=True)
    attempts,terminal=api043.state();cases={x["id"]:x for x in c.lines(PLAN/"cases.jsonl")}
    scorejobs=c.lines(PLAN/"score_jobs.jsonl");rows=[]
    for j in scorejobs:
        t=terminal[j["request_id"]];p=t["parsed"];x=cases[j["proposition_id"]]
        row=dict(id=x["id"],sid=x["sid"],author=x["author"],condition=j["condition"],round=j["round"],status=p["status"])
        if p["status"] in c.VALID:
            sc=p["scores"];row.update(score_verdict=p["verdict"],U0=c.ulabel(sc,0),U2=c.ulabel(sc,2),
              score_Supported=sc["Supported"],score_Not_Supported=sc["Not Supported"],score_Not_Addressed=sc["Not Addressed"],
              reason=p["parsed"].get("reason"),checks_json=__import__("json").dumps(p["parsed"].get("checks"),ensure_ascii=False))
        rows.append(row)
    c.csvwrite(OUT/"score_predictions.csv",rows)
    r0=[r for r in rows if r["round"]==0 and r["status"] in c.VALID];by={(r["id"],r["condition"]):r for r in r0}
    summaries=[]
    for cond in ("A","B","C"):
        rr=[r for r in r0 if r["condition"]==cond]
        z=dict(condition=cond,n_valid=len(rr),n_total=55)
        for key in ("score_verdict","U0","U2"):
            z[key+"_Supported"]=sum(r[key]=="Supported" for r in rr)
            z[key+"_Supported_rate"]=z[key+"_Supported"]/len(rr)
        summaries.append(z)
    c.csvwrite(OUT/"label_summary.csv",summaries)

    pairs=[]
    for a,b in (("A","B"),("C","B")):
        for key in ("score_verdict","U0","U2"):pairs.append(paired(by,a,b,key))
    c.csvwrite(OUT/"paired_effects.csv",pairs)

    # Repeat stability.
    rep=[]
    for cond in ("A","B","C"):
        ids=sorted(set(r["id"] for r in rows if r["condition"]==cond and r["round"]==1 and r["status"] in c.VALID))
        for key in ("score_verdict","U0","U2"):
            valid=[pid for pid in ids if (pid,cond) in by]
            changes=sum(by[(pid,cond)][key]!=next(r[key] for r in rows if r["id"]==pid and r["condition"]==cond and r["round"]==1 and r["status"] in c.VALID) for pid in valid)
            rep.append(dict(condition=cond,prediction=key,n=len(valid),label_changes=changes,change_rate=changes/len(valid) if valid else None))
    c.csvwrite(OUT/"repeat_stability.csv",rep)
    # Reason audits.
    audlog=c.lines(AUD/"logical.jsonl");audrows=[]
    for x in audlog:
        t=terminal[x["request_id"]];p=t["parsed"];s=by.get((x["id"],x["condition"]))
        row=dict(id=x["id"],condition=x["condition"],status=p["status"],score_verdict=s["score_verdict"] if s else None)
        if p["status"]=="valid":
            row.update(label_reason_alignment=p["label_reason_alignment"],grounding=p["grounding"],
                       added_evidence_material=p["added_evidence_material"],explanation=p.get("explanation"))
        audrows.append(row)
    c.csvwrite(OUT/"reason_audits.csv",audrows)
    audsum=[]
    for cond in ("A","B","C"):
        rr=[r for r in audrows if r["condition"]==cond];vv=[r for r in rr if r["status"]=="valid"];ss=[r for r in vv if r["score_verdict"]=="Supported"]
        audsum.append(dict(condition=cond,n_total=len(rr),n_valid=len(vv),
          consistent=sum(r["label_reason_alignment"]=="consistent" for r in vv),
          grounded=sum(r["grounding"]=="grounded" for r in vv),
          consistent_and_grounded=sum(r["label_reason_alignment"]=="consistent" and r["grounding"]=="grounded" for r in vv),
          Supported_reason_n=len(ss),
          Supported_consistent_grounded=sum(r["label_reason_alignment"]=="consistent" and r["grounding"]=="grounded" for r in ss),
          added_material_yes=sum(r["added_evidence_material"]=="yes" for r in vv)))
    c.csvwrite(OUT/"reason_summary.csv",audsum)

    # Compact key result.
    pe={(r["A"],r["B"],r["prediction"]):r for r in pairs}
    key=dict(cohort_n=55,score_round0_valid=Counter(r["condition"] for r in r0),
      score_verdict_S={z["condition"]:z["score_verdict_Supported"] for z in summaries},
      U0_S={z["condition"]:z["U0_Supported"] for z in summaries},U2_S={z["condition"]:z["U2_Supported"] for z in summaries},
      B_vs_A_score=pe[("A","B","score_verdict")],B_vs_C_score=pe[("C","B","score_verdict")],
      audit_valid=Counter(r["condition"] for r in audrows if r["status"]=="valid"),
      cost_cny=sum(a["charge_cny"] for a in attempts))
    c.put(OUT/"key_results.json",key)
    print(__import__("json").dumps(key,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
