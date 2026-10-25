from pathlib import Path
import json,math,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/054_unlabeled_prior_shift"
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import run053,common053 as c
LABELS=("Supported","Not Supported","Not Addressed")

def feat(ds,q):
    dz={k:math.log(max(ds[k]/100,1e-6)) for k in LABELS};qz={k:math.log(max(q[k]/100,1e-6)) for k in LABELS}
    dp={k:ds[k]/100 for k in LABELS};qp={k:q[k]/100 for k in LABELS}
    du0=c.decision(ds,0);qu0=c.decision(q,0);qu2=c.decision(q,2)
    return dict(s=dp["Supported"],ns=dp["Not Supported"],na=dp["Not Addressed"],
      s_margin=dz["Supported"]-max(dz["Not Supported"],dz["Not Addressed"]),
      non_s_margin=abs(dz["Not Supported"]-dz["Not Addressed"]),
      entropy=-sum(dp[k]*math.log(max(dp[k],1e-6)) for k in LABELS),u0_ns=float(du0=="Not Supported"),
      peer_s=qp["Supported"],peer_margin=qz["Supported"]-max(qz["Not Supported"],qz["Not Addressed"]),
      peer_u0_s=float(qu0=="Supported"),peer_u2_s=float(qu2=="Supported"),same_u0=float(qu0==du0))
def prob(model,f):
    m=model["final_fit"];z=[(f[k]-a)/b for k,a,b in zip(m["features"],m["mean"],m["scale"])]
    s=sum(x*y for x,y in zip(z,m["coef"]))+m["intercept"];return 1/(1+math.exp(-s))

def main():
    cases={x["id"]:x for x in c.lines(ROOT/"outputs/053_thinking_prior_validation/evaluation_cases.jsonl")}
    original={x["id"]:x["verdict"] for x in c.lines(ROOT/"outputs/053_thinking_prior_validation/original_verifact_predictions.jsonl")}
    gm=c.read(ROOT/"outputs/033_gate_training_subset/recommendation_001/gate_A_all40.json")
    _,term=run053.state();rows=[];invalid=0
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];ns=term["053_N_S_"+h]["parsed"];ts=term["053_T_S_"+h]["parsed"]
        if ns.get("status") not in c.VALID or ns.get("scores") is None:raise RuntimeError("N-S invalid "+pid)
        u0=c.decision(ns["scores"],0);u2=c.decision(ns["scores"],2);gate=u0
        if u0!="Supported" and u2=="Supported":
            q=term.get("053_Q_"+h,{}).get("parsed",{})
            if q.get("status") in c.VALID and q.get("scores") is not None:
                gate="Supported" if prob(gm,feat(ns["scores"],q["scores"]))>=gm["threshold"] else u0
        if ts.get("status") not in c.VALID or ts.get("scores") is None:
            invalid+=1;continue
        rows.append(dict(id=pid,sid=x["sid"],GT=x["GT"],author=x["author"],ts_scores=ts["scores"],
          U2=u2,GateA=gate,O_Verifact=original[pid]))
    p=OUT/"compact_053.jsonl"
    with p.open("w",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    (OUT/"compact_053_meta.json").write_text(json.dumps(dict(valid=len(rows),invalid=invalid),indent=2)+"\n",encoding="utf-8")
    print("053 compact",len(rows),"invalid",invalid)
if __name__=="__main__":main()
