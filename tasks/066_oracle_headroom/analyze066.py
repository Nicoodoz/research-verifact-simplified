from pathlib import Path
from collections import Counter
import csv,json,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c
import run066

LAB=list(c.LABELS);LI={x:i for i,x in enumerate(LAB)}
def mcc(y,p):
    M=np.zeros((3,3),float);np.add.at(M,(y,p),1)
    s=M.sum();cc=np.trace(M);a=M.sum(1);b=M.sum(0)
    d=((s*s-a@a)*(s*s-b@b))**.5
    return float((cc*s-a@b)/d) if d else 0.0
def metrics(gt,pred):
    y=np.array([LI[x] for x in gt]);p=np.array([LI[x] for x in pred])
    M=np.zeros((3,3),int);np.add.at(M,(y,p),1)
    rec=[M[k,k]/M[k].sum() if M[k].sum() else None for k in range(3)]
    fs=int(((y!=0)&(p==0)).sum())
    return dict(n=len(y),correct=int((y==p).sum()),PA=float((y==p).mean()),
                MCC=mcc(y,p),falseS=fs,S=rec[0],NS=rec[1],NA=rec[2],
                confusion=M.tolist())

def main():
    pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
    gt=[r["GT"] for r in pred];base=[r["TS_PriorG"] for r in pred]
    byid={r["id"]:r for r in pred}
    errors={r["id"] for r in pred if r["TS_PriorG"]!=r["GT"]}
    cases={x["id"]:x for x in c.lines(c.OUT/"error_cases.jsonl")}
    mapping={x["id"]:x for x in c.lines(c.OUT/"final_mapping.jsonl")}
    attempts,term=run066.state()

    # Evidence oracle on the 39 current baseline errors.
    evidence_fix={}
    evidence_rows=[]
    for pid in sorted(errors):
        x=cases[pid];mp=mapping[pid];rid=mp.get("judge_request_id")
        e_pred=None;valid=False;scores=None
        if rid and rid in term:
            q=term[rid]["parsed"]
            valid=q.get("status") in ("valid","valid_with_format_anomaly") and q.get("scores")
            if valid:
                scores=q["scores"];e_pred=c.priorg(scores)
        fix=bool(valid and e_pred==x["GT"])
        evidence_fix[pid]=fix
        if fix:
            if mp.get("c48_reconstructable") and mp.get("kept_all_in_c48"):
                loc="C48_selection_composition"
            elif mp.get("c48_reconstructable"):
                loc="retrieval_or_mixed"
            else:
                loc="upstream_unlocalized"
        else:
            loc="not_fixed"
        evidence_rows.append(dict(id=pid,sid=x["sid"],GT=x["GT"],baseline=x["baseline_pred"],
                                  evidence_pred=e_pred,evidence_valid=bool(valid),evidence_fix=fix,
                                  composer_decisive=mp.get("composer_decisive"),
                                  c48_reconstructable=mp.get("c48_reconstructable"),
                                  kept_all_in_c48=mp.get("kept_all_in_c48"),
                                  kept_external_n=mp.get("kept_external_n"),
                                  kept_n=len(mp.get("kept_pids",[])),localization=loc))

    # Observed same-reference reasoning oracle.
    qrows={}
    qfile=ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl"
    for x in c.lines(qfile):qrows[x["id"]]=x
    reasoning_fix={}
    reason_pred=[]
    for r in pred:
        cand=[r["TS_PriorG"]]
        if r.get("NS_U0") in LAB:cand.append(r["NS_U0"])
        if r.get("TS_status")=="valid" and r.get("TS_raw") in LAB:cand.append(r["TS_raw"])
        if r["id"] in qrows:
            q=qrows[r["id"]]["qwen_scores"]
            cand.append(max(LAB,key=lambda k:float(q[k])))
        ok=any(z==r["GT"] for z in cand)
        reasoning_fix[r["id"]]=ok
        reason_pred.append(r["GT"] if ok else r["TS_PriorG"])

    ev_pred=list(base);comb_pred=list(base)
    for i,r in enumerate(pred):
        if r["id"] in evidence_fix and evidence_fix[r["id"]]:
            ev_pred[i]=r["GT"]
        if reasoning_fix[r["id"]] or evidence_fix.get(r["id"],False):
            comb_pred[i]=r["GT"]

    groups=Counter()
    group_gt={k:Counter() for k in ("reasoning_only","evidence_only","both","neither")}
    for pid in errors:
        rr=reasoning_fix[pid];ee=evidence_fix.get(pid,False)
        key="both" if rr and ee else "reasoning_only" if rr else "evidence_only" if ee else "neither"
        groups[key]+=1;group_gt[key][byid[pid]["GT"]]+=1

    summary={
        "baseline":metrics(gt,base),
        "reasoning_oracle_observed":metrics(gt,reason_pred),
        "evidence_oracle":metrics(gt,ev_pred),
        "combined_oracle":metrics(gt,comb_pred),
        "baseline_errors":len(errors),
        "reasoning_fixed_errors":sum(reasoning_fix[x] for x in errors),
        "evidence_fixed_errors":sum(evidence_fix.get(x,False) for x in errors),
        "combined_fixed_errors":sum(reasoning_fix[x] or evidence_fix.get(x,False) for x in errors),
        "error_partition":dict(groups),
        "error_partition_by_gt":{k:dict(v) for k,v in group_gt.items()},
        "evidence_fixed_by_gt":dict(Counter(byid[x]["GT"] for x in errors if evidence_fix.get(x,False))),
        "reasoning_fixed_by_gt":dict(Counter(byid[x]["GT"] for x in errors if reasoning_fix[x])),
        "evidence_localization":dict(Counter(x["localization"] for x in evidence_rows if x["evidence_fix"])),
        "composer_decisive":sum(bool(x["composer_decisive"]) for x in evidence_rows),
        "evidence_valid":sum(bool(x["evidence_valid"]) for x in evidence_rows),
        "c48_reconstructable":sum(bool(x["c48_reconstructable"]) for x in evidence_rows),
        "cost_cny":sum(a["cost"] for a in attempts),
        "api_attempts":len(attempts),
        "http200":sum(a["http_status"]==200 for a in attempts),
        "reserved_used":False,
    }
    c.csvwrite(c.OUT/"evidence_cases.csv",evidence_rows)
    c.put(c.OUT/"analysis.json",summary)
    write_report(summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

def write_report(s):
    text="# 066 Oracle Headroom Decomposition\n\n"+json.dumps(s,ensure_ascii=False,indent=2)+"\n"
    (c.OUT/"report.md").write_text(text,encoding="utf-8")

if __name__=="__main__":
    main()
