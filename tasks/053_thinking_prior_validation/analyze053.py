from pathlib import Path
from collections import Counter,defaultdict
import csv,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c,run053
sys.path.insert(0,str(ROOT/"src"))
from verifact_research.evaluation import evaluate,paired_compare

def a_features(ds,q):
    dz=c.log_scores(ds);qz=c.log_scores(q);dp={k:ds[k]/100 for k in c.LABELS};qp={k:q[k]/100 for k in c.LABELS}
    du0=c.decision(ds,0);qu0=c.decision(q,0);qu2=c.decision(q,2)
    ent=-sum(dp[k]*math.log(max(dp[k],1e-6)) for k in c.LABELS)
    return dict(s=dp["Supported"],ns=dp["Not Supported"],na=dp["Not Addressed"],
      s_margin=dz["Supported"]-max(dz["Not Supported"],dz["Not Addressed"]),
      non_s_margin=abs(dz["Not Supported"]-dz["Not Addressed"]),entropy=ent,u0_ns=float(du0=="Not Supported"),
      peer_s=qp["Supported"],peer_margin=qz["Supported"]-max(qz["Not Supported"],qz["Not Addressed"]),
      peer_u0_s=float(qu0=="Supported"),peer_u2_s=float(qu2=="Supported"),same_u0=float(qu0==du0))
def gate_prob(model,feat):
    m=model["final_fit"];z=[(feat[k]-mean)/scale for k,mean,scale in zip(m["features"],m["mean"],m["scale"])]
    s=sum(a*b for a,b in zip(z,m["coef"]))+m["intercept"];return 1/(1+math.exp(-s))

def metric(cases,mapping):
    ids=[i for i in cases if mapping.get(i) in c.LABELS]
    coh=[dict(proposition_id=i,subject_id=cases[i]["sid"],human_gt=cases[i]["GT"]) for i in ids]
    pp=[dict(proposition_id=i,verdict=mapping[i]) for i in ids]
    ev=evaluate(coh,pp,profile="research_patient",missing="available",iterations=1000)
    row=dict(n=len(cases),valid_n=len(ids),correct=sum(mapping.get(i)==cases[i]["GT"] for i in cases),
      PA=ev["percent_agreement"],MCC=ev["mcc"],AC1=ev["gwet_ac1"],
      false_S=sum(cases[i]["GT"]!="Supported" and mapping.get(i)=="Supported" for i in cases))
    for lab in c.LABELS:
        den=sum(x["GT"]==lab for x in cases.values())
        row["recall_"+lab.replace(" ","_")]=sum(cases[i]["GT"]==lab and mapping.get(i)==lab for i in cases)/den
    return row

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"evaluation_cases.jsonl")}
    freeze=c.read(c.OUT/"freeze.json");theta=freeze["calibration_theta"];ref=freeze["reference_prior_counts"];cc=freeze["calibration_counts"]
    original={x["id"]:x["verdict"] for x in c.lines(c.OUT/"original_verifact_predictions.jsonl")}
    attempts,term=run053.state()
    gate_model=c.read(ROOT/"outputs/033_gate_training_subset/recommendation_001/gate_A_all40.json")
    methods={m:{} for m in ["O_Verifact","U2","GateA","NS_PriorG","NS_PriorM","TS_raw","TS_U2","TS_PriorG","TS_PriorM"]}
    detail=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];ns=term["053_N_S_"+h]["parsed"];ts=term["053_T_S_"+h]["parsed"]
        c.require(ns.get("status") in c.VALID and ns.get("scores") is not None,"N-S invalid "+pid)
        u0=c.decision(ns["scores"],0);u2=c.decision(ns["scores"],2)
        methods["O_Verifact"][pid]=original[pid];methods["U2"][pid]=u2
        for kind in ("G","M"):
            v=c.calibrated(ns["scores"],theta["N-S"][kind],kind);v=c.prior_adjust(v,ref,cc["N-S"])
            methods["NS_Prior"+kind][pid]=c.decode_logits(v)
        ts_valid=ts.get("status") in c.VALID and ts.get("scores") is not None
        raw=ts.get("verdict") if ts.get("verdict") in c.LABELS else None
        methods["TS_raw"][pid]=raw
        if ts_valid:
            methods["TS_U2"][pid]=c.decision(ts["scores"],2)
            for kind in ("G","M"):
                v=c.calibrated(ts["scores"],theta["T-S"][kind],kind);v=c.prior_adjust(v,ref,cc["T-S"])
                methods["TS_Prior"+kind][pid]=c.decode_logits(v)
        else:
            for m in ("TS_U2","TS_PriorG","TS_PriorM"):methods[m][pid]=u2
        candidate=u0!="Supported" and u2=="Supported";gp=None;keep=None
        gate=u0
        if candidate:
            q=term.get("053_Q_"+h,{}).get("parsed",{})
            if q.get("status") in c.VALID and q.get("scores") is not None:
                gp=gate_prob(gate_model,a_features(ns["scores"],q["scores"]));keep=gp>=gate_model["threshold"];gate="Supported" if keep else u0
        methods["GateA"][pid]=gate
        _obj=ts.get("parsed") or {};_reason=_obj.get("reason");reason=_reason if isinstance(_reason,str) and _reason.strip() else None
        detail.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],NS_U0=u0,U2=u2,
          TS_status=ts.get("status"),TS_raw=raw,GateA=gate,gate_candidate=candidate,gate_prob=gp,
          **{m:methods[m][pid] for m in ("NS_PriorG","NS_PriorM","TS_U2","TS_PriorG","TS_PriorM")},
          **{m+"_reason_sync":bool(reason and raw==methods[m][pid]) for m in ("TS_U2","TS_PriorG","TS_PriorM")}))

    summary=[]
    for m,mp in methods.items():
        z=metric(cases,mp);z["method"]=m
        if m.startswith("TS_") and m!="TS_raw":
            z["reason_sync_n"]=sum(r[m+"_reason_sync"] for r in detail);z["reason_sync_rate"]=z["reason_sync_n"]/len(detail)
        summary.append(z)
    comparisons=[]
    pairs=[]
    for m in ("TS_U2","TS_PriorG","TS_PriorM","NS_PriorG","NS_PriorM"):
        pairs += [(m,"U2"),(m,"GateA"),(m,"O_Verifact")]
    pairs += [("TS_PriorG","TS_U2"),("TS_PriorM","TS_U2"),("TS_PriorM","TS_PriorG")]
    for a,b in pairs:
        ids=[i for i in cases if methods[a].get(i) in c.LABELS and methods[b].get(i) in c.LABELS]
        coh=[dict(proposition_id=i,subject_id=cases[i]["sid"],human_gt=cases[i]["GT"]) for i in ids]
        ap=[dict(proposition_id=i,verdict=methods[a][i]) for i in ids];bp=[dict(proposition_id=i,verdict=methods[b][i]) for i in ids]
        pc=paired_compare(coh,bp,ap,iterations=1000)
        rescue=sum(methods[a][i]==cases[i]["GT"] and methods[b][i]!=cases[i]["GT"] for i in ids)
        harm=sum(methods[b][i]==cases[i]["GT"] and methods[a][i]!=cases[i]["GT"] for i in ids)
        comparisons.append(dict(candidate=a,baseline=b,n=len(ids),rescue=rescue,harm=harm,net=rescue-harm,
          delta_PA=pc["metrics"]["percent_agreement"]["delta"],PA_ci95=pc["metrics"]["percent_agreement"]["ci95"],
          delta_MCC=pc["metrics"]["mcc"]["delta"],MCC_ci95=pc["metrics"]["mcc"]["ci95"],
          false_S_delta=sum(cases[i]["GT"]!="Supported" and methods[a][i]=="Supported" for i in ids)-
                        sum(cases[i]["GT"]!="Supported" and methods[b][i]=="Supported" for i in ids)))
    authors=[]
    for au in ("human","llm"):
        ids={i:x for i,x in cases.items() if x["author"]==au}
        for m,mp in methods.items():
            z=metric(ids,mp);z.update(author=au,method=m);authors.append(z)
    jobs={j["request_id"]:j for j in c.lines(c.OUT/"main_jobs.jsonl")+c.lines(c.OUT/"qwen_jobs.jsonl")}
    costs=defaultdict(float);calls=Counter()
    for a in attempts:
        cond=jobs[a["request_id"]]["condition"];costs[cond]+=a["cost"];calls[cond]+=1
    c.csvwrite(c.OUT/"predictions.csv",detail);c.csvwrite(c.OUT/"summary.csv",summary);c.csvwrite(c.OUT/"comparisons.csv",comparisons);c.csvwrite(c.OUT/"authors.csv",authors)
    c.csvwrite(c.OUT/"costs.csv",[dict(condition=k,calls=calls[k],cost_cny=costs[k]) for k in sorted(costs)])
    result=dict(created_utc=c.now(),GT_counts=dict(Counter(x["GT"] for x in cases.values())),author_counts=dict(Counter(x["author"] for x in cases.values())),
      summary=summary,comparisons=comparisons,cost_cny=sum(a["cost"] for a in attempts),attempts=len(attempts),http200=sum(a["http_status"]==200 for a in attempts),
      gate_candidates=sum(r["gate_candidate"] for r in detail),TS_invalid=sum(r["TS_status"] not in c.VALID for r in detail))
    c.put(c.OUT/"analysis.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
