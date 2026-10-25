"""Analyze completed 052 first-tier same-cohort validation. No API calls."""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
import run052
sys.path.insert(0,str(ROOT/"src"))
from verifact_research.evaluation import evaluate,paired_compare
LABELS=c.LABELS

def log_scores(sc):return {k:math.log(max(sc[k]/100,1e-6)) for k in LABELS}
def decode_vals(v):return max(("Not Supported","Not Addressed","Supported"),key=lambda k:v[k])
def cal_pred(sc,theta,kind):
    v=log_scores(sc)
    if kind=="G":v["Supported"]+=theta[0]
    elif kind=="M":v["Supported"]+=theta[0];v["Not Supported"]+=theta[1]
    else:raise ValueError(kind)
    return decode_vals(v)
def a_features(ds,q):
    dz=log_scores(ds);qz=log_scores(q);dp={k:ds[k]/100 for k in LABELS};qp={k:q[k]/100 for k in LABELS}
    du0=c.c020.decision(ds,0);qu0=c.c020.decision(q,0);qu2=c.c020.decision(q,2)
    entropy=-sum(dp[k]*math.log(max(dp[k],1e-6)) for k in LABELS)
    return dict(s=dp["Supported"],ns=dp["Not Supported"],na=dp["Not Addressed"],
      s_margin=dz["Supported"]-max(dz["Not Supported"],dz["Not Addressed"]),
      non_s_margin=abs(dz["Not Supported"]-dz["Not Addressed"]),entropy=entropy,u0_ns=float(du0=="Not Supported"),
      peer_s=qp["Supported"],peer_margin=qz["Supported"]-max(qz["Not Supported"],qz["Not Addressed"]),
      peer_u0_s=float(qu0=="Supported"),peer_u2_s=float(qu2=="Supported"),same_u0=float(qu0==du0))
def gate_probability(model,feat):
    m=model["final_fit"];z=[]
    for k,mean,scale in zip(m["features"],m["mean"],m["scale"]):z.append((feat[k]-mean)/scale)
    s=sum(a*b for a,b in zip(z,m["coef"]))+m["intercept"]
    return 1/(1+math.exp(-s))

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"evaluation_cases.jsonl")}
    blind={x["id"]:x for x in c.lines(c.OUT/"sample_blind.jsonl")}
    rules=c.read(c.OUT/"decision_rules_freeze.json");cal=rules["calibration_theta"]
    gate_map=c.read(c.OUT/"gate_patient_out_mapping.json")["models"]
    original={x["id"]:x["verdict"] for x in c.lines(c.OUT/"original_verifact_predictions.jsonl")}
    attempts,term=run052.state()
    preds={m:{} for m in rules["methods"]};rows=[];gate_rows=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24]
        pNS=term["052_N_S_"+h]["parsed"];pNV=term["052_N_V_"+h]["parsed"]
        pTS=term["052_T_S_"+h]["parsed"];pTV=term["052_T_V_"+h]["parsed"]
        ns_ok=pNS.get("status") in c.VALID and pNS.get("scores") is not None
        ts_ok=pTS.get("status") in c.VALID and pTS.get("scores") is not None
        nv=pNV.get("verdict") if pNV.get("status") in c.VALID else None
        tv=pTV.get("verdict") if pTV.get("status") in c.VALID else None
        ns_u0=c.c020.decision(pNS["scores"],0) if ns_ok else None
        ns_u2=c.c020.decision(pNS["scores"],2) if ns_ok else None
        ts_raw=pTS.get("verdict") if pTS.get("status") in c.VALID else None
        ts_u2=c.c020.decision(pTS["scores"],2) if ts_ok else None
        ns_g=cal_pred(pNS["scores"],cal["N-S"]["G"],"G") if ns_ok else None
        ns_m=cal_pred(pNS["scores"],cal["N-S"]["M"],"M") if ns_ok else None
        ts_g=cal_pred(pTS["scores"],cal["T-S"]["G"],"G") if ts_ok else None
        ts_m=cal_pred(pTS["scores"],cal["T-S"]["M"],"M") if ts_ok else None
        vals={"O_Verifact":original[pid],"U2":ns_u2,"NS_G":ns_g,"NS_M":ns_m,"NV":nv,
              "TS_raw":ts_raw,"TS_U2":ts_u2,"TS_G":ts_g,"TS_M":ts_m,"TV":tv}
        # Patient-out Gate A on fresh N-S candidate only.
        gate=ns_u0
        candidate=bool(ns_ok and ns_u0!="Supported" and ns_u2=="Supported")
        q_status="not_required";gprob=None;keep=None
        if candidate:
            qid="052_Q_"+h
            if qid in term and term[qid]["parsed"].get("status") in c.VALID and term[qid]["parsed"].get("scores") is not None:
                q=term[qid]["parsed"];q_status=q["status"];feat=a_features(pNS["scores"],q["scores"])
                gm=gate_map[x["sid"]];model=c.read(ROOT/gm["source"])
                gprob=gate_probability(model,feat);keep=gprob>=model["threshold"];gate="Supported" if keep else ns_u0
            else:q_status="invalid_or_missing";gate=ns_u0
        vals["GateA_patient_out"]=gate
        # Cascades: only N-V Supported triggers second-stage adoption; invalid second stage retains N-V.
        def cascade(second):return second if nv=="Supported" and second is not None else nv
        vals.update(NV_to_TS_raw=cascade(ts_raw),NV_to_TS_U2=cascade(ts_u2),NV_to_TS_G=cascade(ts_g),
                    NV_to_TS_M=cascade(ts_m),NV_to_TV=cascade(tv))
        for m,v in vals.items():preds[m][pid]=v
        gate_rows.append(dict(id=pid,sid=x["sid"],GT=x["GT"],candidate=candidate,NS_U0=ns_u0,NS_U2=ns_u2,
          q_status=q_status,gate_probability=gprob,gate_keep=keep,GateA=gate))
        rows.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],
          NS_status=pNS.get("status"),NV_status=pNV.get("status"),TS_status=pTS.get("status"),TV_status=pTV.get("status"),**vals))

    cohort=[dict(proposition_id=pid,subject_id=x["sid"],human_gt=x["GT"]) for pid,x in cases.items()]
    summary=[]
    for m,mapping in preds.items():
        valid_ids=[pid for pid in cases if mapping.get(pid) in LABELS]
        pp=[dict(proposition_id=pid,verdict=mapping[pid]) for pid in valid_ids]
        ev=evaluate(cohort,pp,profile="research_patient",missing="available",iterations=1000)
        correct=sum(mapping.get(pid)==cases[pid]["GT"] for pid in cases)
        false_s=sum(cases[pid]["GT"]!="Supported" and mapping.get(pid)=="Supported" for pid in cases)
        row=dict(method=m,n=len(cases),valid_n=len(valid_ids),correct=correct,PA_full_lower=correct/len(cases),
          PA_valid=ev["percent_agreement"],MCC_valid=ev["mcc"],AC1_valid=ev["gwet_ac1"],false_S=false_s,
          PA_ci95=ev["confidence_intervals"]["percent_agreement"],MCC_ci95=ev["confidence_intervals"]["mcc"],
          AC1_ci95=ev["confidence_intervals"]["gwet_ac1"])
        for lab in LABELS:
            den=sum(x["GT"]==lab for x in cases.values())
            row["recall_"+lab.replace(" ","_")]=sum(cases[pid]["GT"]==lab and mapping.get(pid)==lab for pid in cases)/den
        summary.append(row)

    pair_defs=[]
    firsttier=["NV","TS_raw","TS_U2","TS_G","TS_M","TV","NV_to_TS_raw","NV_to_TS_U2","NV_to_TS_G","NV_to_TS_M","NV_to_TV"]
    for m in firsttier+["NS_G","NS_M"]:pair_defs.append((m,"U2"))
    for m in firsttier:pair_defs.append((m,"GateA_patient_out"))
    pair_defs += [("TS_G","NS_G"),("TS_M","NS_M"),("NV_to_TS_U2","NV"),("NV_to_TS_G","NV"),
                  ("NV_to_TS_M","NV"),("NV_to_TV","NV"),("NV_to_TS_U2","TS_U2"),("NV_to_TV","TV")]
    comparisons=[];patient_deltas=[]
    seen=set()
    for a,b in pair_defs:
        if (a,b) in seen:continue
        seen.add((a,b));common=[pid for pid in cases if preds[a].get(pid) in LABELS and preds[b].get(pid) in LABELS]
        sub=[dict(proposition_id=pid,subject_id=cases[pid]["sid"],human_gt=cases[pid]["GT"]) for pid in common]
        ap=[dict(proposition_id=pid,verdict=preds[a][pid]) for pid in common];bp=[dict(proposition_id=pid,verdict=preds[b][pid]) for pid in common]
        pc=paired_compare(sub,bp,ap,iterations=1000)
        rescue=[pid for pid in common if preds[a][pid]==cases[pid]["GT"] and preds[b][pid]!=cases[pid]["GT"]]
        harm=[pid for pid in common if preds[b][pid]==cases[pid]["GT"] and preds[a][pid]!=cases[pid]["GT"]]
        comparisons.append(dict(candidate=a,baseline=b,n=len(common),rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),
          rescue_patients=len({cases[i]["sid"] for i in rescue}),harm_patients=len({cases[i]["sid"] for i in harm}),
          delta_PA=pc["metrics"]["percent_agreement"]["delta"],PA_ci95=pc["metrics"]["percent_agreement"]["ci95"],
          delta_MCC=pc["metrics"]["mcc"]["delta"],MCC_ci95=pc["metrics"]["mcc"]["ci95"],
          delta_AC1=pc["metrics"]["gwet_ac1"]["delta"],AC1_ci95=pc["metrics"]["gwet_ac1"]["ci95"],
          false_S_delta=sum(cases[i]["GT"]!="Supported" and preds[a][i]=="Supported" for i in common)-
                        sum(cases[i]["GT"]!="Supported" and preds[b][i]=="Supported" for i in common)))
        for sid in sorted({cases[i]["sid"] for i in common}):
            ids=[i for i in common if cases[i]["sid"]==sid]
            patient_deltas.append(dict(candidate=a,baseline=b,sid=sid,n=len(ids),
              delta_correct=sum(preds[a][i]==cases[i]["GT"] for i in ids)-sum(preds[b][i]==cases[i]["GT"] for i in ids),
              delta_false_S=sum(cases[i]["GT"]!="Supported" and preds[a][i]=="Supported" for i in ids)-
                            sum(cases[i]["GT"]!="Supported" and preds[b][i]=="Supported" for i in ids)))

    # Author strata.
    author_rows=[]
    for author in sorted({x["author"] for x in cases.values()}):
        ids=[pid for pid,x in cases.items() if x["author"]==author]
        for m in preds:
            vv=[pid for pid in ids if preds[m].get(pid) in LABELS]
            if not vv:continue
            author_rows.append(dict(author=author,method=m,n=len(ids),valid_n=len(vv),
              correct=sum(preds[m][i]==cases[i]["GT"] for i in ids),
              false_S=sum(cases[i]["GT"]!="Supported" and preds[m].get(i)=="Supported" for i in ids),
              S_recall=sum(cases[i]["GT"]=="Supported" and preds[m].get(i)=="Supported" for i in ids)/max(1,sum(cases[i]["GT"]=="Supported" for i in ids)),
              NS_recall=sum(cases[i]["GT"]=="Not Supported" and preds[m].get(i)=="Not Supported" for i in ids)/max(1,sum(cases[i]["GT"]=="Not Supported" for i in ids)),
              NA_recall=sum(cases[i]["GT"]=="Not Addressed" and preds[m].get(i)=="Not Addressed" for i in ids)/max(1,sum(cases[i]["GT"]=="Not Addressed" for i in ids))))

    # Frozen repeat diagnostics.
    repeat_ids=sorted({j["id"] for j in c.lines(c.OUT/"main_jobs.jsonl") if str(j.get("condition","")).endswith("_repeat")});c.require(len(repeat_ids)==12,"repeat ID recovery");repeat_rows=[]
    for pid in repeat_ids:
        h=c.stable("",pid)[:24]
        for cond in ("N-S","N-V","T-S","T-V"):
            p=term["052_"+cond.replace("-","_")+"_rep_"+h]["parsed"]
            if cond=="N-S":
                rp=c.c020.decision(p["scores"],2) if p.get("status") in c.VALID and p.get("scores") else None
                first=preds["U2"].get(pid)
            elif cond=="N-V":rp=p.get("verdict") if p.get("status") in c.VALID else None;first=preds["NV"].get(pid)
            elif cond=="T-S":rp=p.get("verdict") if p.get("status") in c.VALID else None;first=preds["TS_raw"].get(pid)
            else:rp=p.get("verdict") if p.get("status") in c.VALID else None;first=preds["TV"].get(pid)
            repeat_rows.append(dict(id=pid,sid=cases[pid]["sid"],condition=cond,first=first,repeat=rp,changed=rp!=first))
    repeat_summary=[]
    for cond in ("N-S","N-V","T-S","T-V"):
        rr=[r for r in repeat_rows if r["condition"]==cond]
        repeat_summary.append(dict(condition=cond,n=len(rr),changed=sum(r["changed"] for r in rr),agreement=1-sum(r["changed"] for r in rr)/len(rr)))

    jobs={j["request_id"]:j for j in c.lines(c.OUT/"main_jobs.jsonl")+c.lines(c.OUT/"qwen_jobs.jsonl")}
    cost_by=defaultdict(float);calls=Counter()
    for a in attempts:
        j=jobs[a["request_id"]];key=j["condition"];cost_by[key]+=a["cost"];calls[key]+=1
    costs=[dict(condition=k,calls=calls[k],cost_cny=cost_by[k]) for k in sorted(cost_by)]

    result=dict(created_utc=c.now(),n=len(cases),GT_counts=dict(Counter(x["GT"] for x in cases.values())),
      author_counts=dict(Counter(x["author"] for x in cases.values())),summary=summary,comparisons=comparisons,
      patient_deltas=patient_deltas,repeat_summary=repeat_summary,gate_candidate_n=sum(r["candidate"] for r in gate_rows),
      gate_q_valid=sum(r["q_status"] in c.VALID for r in gate_rows if r["candidate"]),costs=costs,
      cost_cny=sum(a["cost"] for a in attempts),attempts=len(attempts),http200=sum(a["http_status"]==200 for a in attempts))
    c.put(c.OUT/"analysis.json",result)
    c.csvwrite(c.OUT/"predictions.csv",rows);c.csvwrite(c.OUT/"summary.csv",summary);c.csvwrite(c.OUT/"comparisons.csv",comparisons)
    c.csvwrite(c.OUT/"patient_deltas.csv",patient_deltas);c.csvwrite(c.OUT/"authors.csv",author_rows)
    c.csvwrite(c.OUT/"gate_cases.csv",gate_rows);c.csvwrite(c.OUT/"repeat_summary.csv",repeat_summary);c.csvwrite(c.OUT/"costs.csv",costs)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
