"""Offline simulation of frozen PriorG under unlabeled label shift. No API access."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,math,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/054_unlabeled_prior_shift"
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c53
from sklearn.metrics import matthews_corrcoef
LABELS=list(c53.LABELS); K=len(LABELS)
SOURCE_COUNTS=np.array([1108.,100.,170.])
SOURCE_PRIOR=SOURCE_COUNTS/SOURCE_COUNTS.sum()
CAL_COUNTS=np.array([48.,47.,48.])
CAL_PRIOR=CAL_COUNTS/CAL_COUNTS.sum()
G=float(c53.read(ROOT/"outputs/053_thinking_prior_validation/freeze.json")["calibration_theta"]["T-S"]["G"][0])
SCENARIOS={
 "source":SOURCE_PRIOR,
 "high_S":np.array([.90,.05,.05]),
 "S70":np.array([.70,.15,.15]),
 "S60":np.array([.60,.20,.20]),
 "NS_heavy":np.array([.60,.30,.10]),
 "NA_heavy":np.array([.60,.10,.30]),
}
BATCH_SIZES=(60,120,240,480); REPS=500; EVAL_N=240
SEED=20260922054

def softmax(z):
    z=np.asarray(z,float);z=z-np.max(z,axis=-1,keepdims=True)
    e=np.exp(z);return e/e.sum(axis=-1,keepdims=True)
def base_logits(scores):
    z=np.log(np.maximum(np.array([scores[k]/100 for k in LABELS],float),1e-6));z[0]+=G;return z
def posterior(z,prior):
    return softmax(np.asarray(z)+np.log(np.maximum(prior,1e-12)/CAL_PRIOR))
def hard(z,prior):return int(np.argmax(posterior(z,prior)))
def simplex_project(v):
    v=np.asarray(v,float);u=np.sort(v)[::-1];css=np.cumsum(u)-1
    idx=np.where(u-css/(np.arange(len(v))+1)>0)[0];rho=int(idx[-1]);theta=css[rho]/(rho+1)
    return np.maximum(v-theta,0)

def bbse(C,hard_pred):
    q=np.bincount(np.asarray(hard_pred,int),minlength=K)/len(hard_pred)
    p=SOURCE_PRIOR.copy();step=1/(float(np.sum(C*C))+1e-12)
    for _ in range(2000):
        new=simplex_project(p-step*(C.T@(C@p-q)))
        if np.max(np.abs(new-p))<1e-12:break
        p=new
    return np.maximum(p,1e-8)/np.maximum(p,1e-8).sum()
def em_prior(qs):
    p=SOURCE_PRIOR.copy()
    for _ in range(10000):
        w=qs*(p/SOURCE_PRIOR);r=w/w.sum(axis=1,keepdims=True);new=r.mean(axis=0)
        new=np.maximum(new,1e-10);new/=new.sum()
        if np.max(np.abs(new-p))<1e-10:return new
        p=new
    return p
def alloc(prior,n):
    x=prior*n;base=np.floor(x).astype(int);left=n-base.sum()
    order=np.argsort(-(x-base),kind="stable")
    for i in order[:left]:base[i]+=1
    return base
def sample_idx(by_class,prior,n,rng):
    cnt=alloc(prior,n);parts=[]
    for k,c in enumerate(cnt):parts.extend(rng.choice(by_class[k],size=int(c),replace=True).tolist())
    rng.shuffle(parts);return np.array(parts,int)
def metrics(y,pred):
    y=np.asarray(y,int);pred=np.asarray(pred,int)
    return dict(PA=float(np.mean(y==pred)),MCC=float(matthews_corrcoef(y,pred)),
      false_S=int(np.sum((pred==0)&(y!=0))),
      S_recall=float(np.mean(pred[y==0]==0)),NS_recall=float(np.mean(pred[y==1]==1)),NA_recall=float(np.mean(pred[y==2]==2)))
def gate_features(ds,q):
    dz={k:math.log(max(ds[k]/100,1e-6)) for k in LABELS};qz={k:math.log(max(q[k]/100,1e-6)) for k in LABELS}
    dp={k:ds[k]/100 for k in LABELS};qp={k:q[k]/100 for k in LABELS}
    du0=c53.decision(ds,0);qu0=c53.decision(q,0);qu2=c53.decision(q,2)
    return dict(s=dp["Supported"],ns=dp["Not Supported"],na=dp["Not Addressed"],
      s_margin=dz["Supported"]-max(dz["Not Supported"],dz["Not Addressed"]),
      non_s_margin=abs(dz["Not Supported"]-dz["Not Addressed"]),
      entropy=-sum(dp[k]*math.log(max(dp[k],1e-6)) for k in LABELS),u0_ns=float(du0=="Not Supported"),
      peer_s=qp["Supported"],peer_margin=qz["Supported"]-max(qz["Not Supported"],qz["Not Addressed"]),
      peer_u0_s=float(qu0=="Supported"),peer_u2_s=float(qu2=="Supported"),same_u0=float(qu0==du0))

def gate_prob(model,feat):
    m=model["final_fit"];z=[(feat[k]-mean)/scale for k,mean,scale in zip(m["features"],m["mean"],m["scale"])]
    s=sum(a*b for a,b in zip(z,m["coef"]))+m["intercept"];return 1/(1+math.exp(-s))
def load_pool(task):
    p=OUT/f"compact_{task}.jsonl";rows=[];meta=json.loads((OUT/f"compact_{task}_meta.json").read_text(encoding="utf-8"))
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():continue
            x=json.loads(line);z=base_logits(x["ts_scores"]);qs=posterior(z,SOURCE_PRIOR);gt=LABELS.index(x["GT"])
            rows.append(dict(pool=task,id=x["id"],sid=x["sid"],GT=x["GT"],y=gt,author=x["author"],z=z,qs=qs,
              frozen=int(np.argmax(qs)),u2=LABELS.index(x["U2"]),gate=LABELS.index(x["GateA"]),original=LABELS.index(x["O_Verifact"])))
    return rows,int(meta["invalid"])
def confusion(rows):
    cm=np.zeros((K,K),float)
    for r in rows:cm[r["frozen"],r["y"]]+=1
    C=cm/cm.sum(axis=0,keepdims=True)
    a,b,c=C[0];d,e,f=C[1];g,h,i=C[2]
    det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
    if abs(det)<1e-12:condF=float("inf")
    else:
        adj=np.array([[e*i-f*h,c*h-b*i,b*f-c*e],[f*g-d*i,a*i-c*g,c*d-a*f],[d*h-e*g,b*g-a*h,a*e-b*d]],float)
        inv=adj/det;condF=float(np.sqrt(np.sum(C*C))*np.sqrt(np.sum(inv*inv)))
    return cm,C,condF

def summarize(vals):
    a=np.asarray(vals,float)
    return dict(mean=float(np.mean(a)),median=float(np.median(a)),q025=float(np.quantile(a,.025)),q975=float(np.quantile(a,.975)))
def csvwrite(path,rows):
    rows=list(rows);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def put(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def main():
    rows052,inv052=load_pool("052");rows053,inv053=load_pool("053")
    pools={"052":rows052,"053":rows053}
    source_diag=[];Cs={}
    for name,rows in pools.items():
        cm,C,cond=confusion(rows);Cs[name]=C
        y=np.array([r["y"] for r in rows]);qs=np.stack([r["qs"] for r in rows])
        nll=float(-np.mean(np.log(np.maximum(qs[np.arange(len(y)),y],1e-12))))
        one=np.eye(K)[y];brier=float(np.mean(np.sum((qs-one)**2,axis=1)))
        source_diag.append(dict(pool=name,n_valid=len(rows),invalid_TS=(inv052 if name=="052" else inv053),
          condition_number=cond,nll=nll,brier=brier,confusion_pred_by_true=json.dumps(cm.astype(int).tolist())))
    case_rows=[]
    for name,rows in pools.items():
        for r in rows:
            case_rows.append(dict(pool=name,id=r["id"],sid=r["sid"],GT=r["GT"],author=r["author"],
              frozen=LABELS[r["frozen"]],U2=LABELS[r["u2"]],GateA=LABELS[r["gate"]],O_Verifact=LABELS[r["original"]],
              qS=r["qs"][0],qNS=r["qs"][1],qNA=r["qs"][2],zS=r["z"][0],zNS=r["z"][1],zNA=r["z"][2]))
    csvwrite(OUT/"case_table.csv",case_rows);csvwrite(OUT/"source_diagnostics.csv",source_diag)
    freeze=dict(seed=SEED,reps=REPS,eval_n=EVAL_N,batch_sizes=list(BATCH_SIZES),labels=LABELS,
      source_prior=SOURCE_PRIOR.tolist(),calibration_prior=CAL_PRIOR.tolist(),G=G,
      scenarios={k:v.tolist() for k,v in SCENARIOS.items()},invalid_TS={"052":inv052,"053":inv053},
      cross_source={"052":"053","053":"052"},protocol_sha256=c53.sha(ROOT/"tasks/054_unlabeled_prior_shift/protocol.md"))
    put(OUT/"freeze.json",freeze)

    # Natural-batch diagnostic: estimators receive the full target scores without target labels.
    actual_prior=[];actual_cls=[]
    for target,rows in pools.items():
        source="053" if target=="052" else "052";C=Cs[source]
        y=np.array([r["y"] for r in rows]);z=np.stack([r["z"] for r in rows]);qs=np.stack([r["qs"] for r in rows])
        true=np.bincount(y,minlength=K)/len(y);frozen=np.array([r["frozen"] for r in rows])
        pb=bbse(C,frozen);pe=em_prior(qs)
        actual_prior += [
          dict(target=target,estimator="true_GT_for_evaluation",**{f"p_{LABELS[k]}":true[k] for k in range(K)}),
          dict(target=target,estimator="source_frozen",**{f"p_{LABELS[k]}":SOURCE_PRIOR[k] for k in range(K)}),
          dict(target=target,estimator="BBSE_unlabeled",L1=float(np.sum(abs(pb-true))),**{f"p_{LABELS[k]}":pb[k] for k in range(K)}),
          dict(target=target,estimator="EM_unlabeled",L1=float(np.sum(abs(pe-true))),**{f"p_{LABELS[k]}":pe[k] for k in range(K)})]
        preds={"FrozenPriorG":np.argmax(np.stack([r["qs"] for r in rows]),axis=1),
          "OraclePriorG":np.array([hard(v,true) for v in z]),
          "BBSEPriorG":np.array([hard(v,pb) for v in z]),"EMPriorG":np.array([hard(v,pe) for v in z]),
          "U2":np.array([r["u2"] for r in rows]),"GateA":np.array([r["gate"] for r in rows]),"O_Verifact":np.array([r["original"] for r in rows])}
        for m,pred in preds.items():actual_cls.append(dict(target=target,method=m,**metrics(y,pred)))
    csvwrite(OUT/"actual_prior_estimates.csv",actual_prior);csvwrite(OUT/"actual_batch_results.csv",actual_cls)

    rng=np.random.default_rng(SEED);prior_records=[];cls_records=[]
    for target,rows in pools.items():
        source="053" if target=="052" else "052";C=Cs[source]
        yall=np.array([r["y"] for r in rows]);zall=np.stack([r["z"] for r in rows]);qsall=np.stack([r["qs"] for r in rows])
        frozen_all=np.array([r["frozen"] for r in rows]);u2all=np.array([r["u2"] for r in rows])
        gateall=np.array([r["gate"] for r in rows]);origall=np.array([r["original"] for r in rows])
        by=[np.where(yall==k)[0] for k in range(K)]
        for scen,pt in SCENARIOS.items():
            for batch_n in BATCH_SIZES:
                prior_vals={"BBSE":[],"EM":[]};metric_vals=defaultdict(lambda:defaultdict(list))
                for rep in range(REPS):
                    ia=sample_idx(by,pt,batch_n,rng);ie=sample_idx(by,pt,EVAL_N,rng)
                    pb=bbse(C,frozen_all[ia]);pe=em_prior(qsall[ia])
                    prior_vals["BBSE"].append(pb);prior_vals["EM"].append(pe)
                    ye=yall[ie];ze=zall[ie]
                    preds={"FrozenPriorG":frozen_all[ie],"OraclePriorG":np.array([hard(v,pt) for v in ze]),
                      "BBSEPriorG":np.array([hard(v,pb) for v in ze]),"EMPriorG":np.array([hard(v,pe) for v in ze]),
                      "U2":u2all[ie],"GateA":gateall[ie],"O_Verifact":origall[ie]}
                    for m,pred in preds.items():
                        mm=metrics(ye,pred)
                        for k,v in mm.items():metric_vals[m][k].append(v)

                for est,arrs in prior_vals.items():
                    A=np.stack(arrs);l1=np.sum(abs(A-pt),axis=1)
                    row=dict(target=target,source=source,scenario=scen,batch_n=batch_n,estimator=est,
                      true_S=pt[0],true_NS=pt[1],true_NA=pt[2],**{f"L1_{k}":v for k,v in summarize(l1).items()})
                    for k,lab in enumerate(LABELS):
                        s=summarize(A[:,k]);row.update({f"{lab}_{x}":v for x,v in s.items()})
                    prior_records.append(row)
                for m,vals in metric_vals.items():
                    row=dict(target=target,source=source,scenario=scen,batch_n=batch_n,method=m)
                    for metric_name,vs in vals.items():
                        s=summarize(vs);row.update({f"{metric_name}_{x}":v for x,v in s.items()})
                    if m!="FrozenPriorG":
                        for metric_name in ("PA","MCC","false_S"):
                            d=np.asarray(vals[metric_name])-np.asarray(metric_vals["FrozenPriorG"][metric_name])
                            s=summarize(d);row.update({f"delta_{metric_name}_vs_frozen_{x}":v for x,v in s.items()})
                    cls_records.append(row)
                print(target,scen,batch_n,"done",flush=True)
    csvwrite(OUT/"prior_estimation_summary.csv",prior_records)
    csvwrite(OUT/"classification_summary.csv",cls_records)
    put(OUT/"run_summary.json",dict(created_utc=c53.now(),status="PASS",API_calls=0,
      pools={k:len(v) for k,v in pools.items()},source_diagnostics=source_diag,
      prior_rows=len(prior_records),classification_rows=len(cls_records)))
    print("054 COMPLETE",len(prior_records),len(cls_records),flush=True)
if __name__=="__main__":main()
