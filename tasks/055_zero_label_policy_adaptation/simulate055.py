"""055 zero-label prevalence-conditioned policy simulation. Offline only."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,math,hashlib,numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
TASK=ROOT/"tasks/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum()
CAL=np.array([48.,47.,48.]);CAL/=CAL.sum()
G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
BS=np.arange(.5,3.01,.25);BN=np.arange(-1.5,1.51,.25)
SCEN={
 "source":P0,
 "high_S":np.array([.90,.05,.05]),
 "S70":np.array([.70,.15,.15]),
 "S60":np.array([.60,.20,.20]),
 "NS_heavy":np.array([.60,.30,.10]),
 "NA_heavy":np.array([.60,.10,.30]),
}
BATCH=(60,120,240,480);REPS=500;NULL_REPS=1000;EVAL_N=240;SEED=20260922055

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,o):
 Path(p).write_text(json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,np.generic):return clean(v.item())
 if isinstance(v,float) and not np.isfinite(v):return None
 return v
def csvwrite(p,rows):
 rows=list(rows);fields=list(dict.fromkeys(k for r in rows for k in r))
 with Path(p).open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:clean(v) for k,v in r.items()} for r in rows])
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
def base_z(sc):
 z=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));z[0]+=G;return z
def load_feature_pool(name):
 rr=lines(OUT/f"features_{name}.jsonl");base={}
 if name!="051":
  with (ROOT/"outputs/054_unlabeled_prior_shift/case_table.csv").open(encoding="utf-8",newline="") as f:
   base={r["id"]:r for r in csv.DictReader(f) if r["pool"]==name}
 out=[]
 for r in rr:
  x=dict(id=r["id"],sid=r["sid"],GT=r["GT"],y=LI[r["GT"]],Z=base_z(r["ts_scores"]))
  if name!="051":
   b=base[r["id"]];x.update(frozen=LI[b["frozen"]],U2=LI[b["U2"]],GateA=LI[b["GateA"]],O=LI[b["O_Verifact"]])
  else:x["frozen"]=int(np.argmax(x["Z"]+B0))
  out.append(x)
 return out
def cond_cm(y,pred):
 C=np.zeros((3,3),float);np.add.at(C,(pred,y),1);den=C.sum(axis=0,keepdims=True);C=C/den;return C
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(len(v))+1)>0)[0]
 rho=int(idx[-1]);theta=css[rho]/(rho+1);return np.maximum(v-theta,0)
def bbse(C,hard_pred):
 q=np.bincount(np.asarray(hard_pred,int),minlength=3)/len(hard_pred);p=P0.copy();step=1/(float(np.sum(C*C))+1e-12)
 for _ in range(3000):
  cp=np.array([sum(C[i,j]*p[j] for j in range(3)) for i in range(3)]);res=cp-q
  grad=np.array([sum(C[i,j]*res[i] for i in range(3)) for j in range(3)])
  new=project(p-step*grad)
  if np.max(np.abs(new-p))<1e-11:break
  p=new
 p=np.maximum(p,1e-9);return p/p.sum()
def alloc(prior,n):
 x=prior*n;b=np.floor(x).astype(int);left=int(n-b.sum());order=np.argsort(-(x-b),kind="stable")
 for i in order[:left]:b[i]+=1
 return b
def sample_idx(by,prior,n,rng):
 cnt=alloc(prior,n);a=[]
 for k,c in enumerate(cnt):a.extend(rng.choice(by[k],size=int(c),replace=True).tolist())
 rng.shuffle(a);return np.array(a,int)
def expected(C,prior):
 M=C*prior[None,:];pa=float(np.trace(M));fs=float(M[0,1]+M[0,2]);t=M.sum(0);q=M.sum(1);s=float(M.sum());cc=float(np.trace(M))
 den=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5
 mcc=(cc*s-float(np.sum(q*t)))/den if den else 0.
 return pa,mcc,fs,[float(C[k,k]) for k in range(3)]
def build_policies(Z,y):
 pairs=[(float(bs),float(bn)) for bs in BS for bn in BN]+[(float(B0[0]),float(B0[1]))];seen=set();out=[]
 for bs,bn in pairs:
  key=(round(bs,12),round(bn,12))
  if key in seen:continue
  seen.add(key);pr=np.argmax(Z+np.array([bs,bn,0.])[None,:],axis=1);out.append(dict(bs=bs,bn=bn,C=cond_cm(y,pr)))
 return out
def choose_policy(policies,prior,obj):
 best=None
 for d in policies:
  pa,mcc,fs,rec=expected(d["C"],prior)
  key=(mcc,pa,-fs,min(rec)) if obj=="MCC" else (pa,mcc,-fs,min(rec))
  row=(key,d["bs"],d["bn"],pa,mcc,fs,rec)
  if best is None or row[0]>best[0]:best=row
 return best
def predict_bias(Z,bs,bn):return np.argmax(Z+np.array([bs,bn,0.])[None,:],axis=1)
def predict_naive_prior(Z,p):return np.argmax(Z+np.log(np.maximum(p,1e-12)/CAL)[None,:],axis=1)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=float(C.sum());cc=float(np.trace(C));t=C.sum(1);q=C.sum(0)
 den=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5
 return (cc*s-float(np.sum(q*t)))/den if den else 0.
def metrics(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);rec=[C[k,k]/C[k].sum() for k in range(3)]
 return dict(PA=float(np.mean(y==p)),MCC=float(mcc(y,p)),false_S=int(np.sum((y!=0)&(p==0))),
  S_recall=float(rec[0]),NS_recall=float(rec[1]),NA_recall=float(rec[2]))
def summarize(a):
 a=np.asarray(a,float);return dict(mean=float(np.nanmean(a)),median=float(np.nanmedian(a)),q025=float(np.nanquantile(a,.025)),q975=float(np.nanquantile(a,.975)))
def null_threshold(source,C,n,reps,rng):
 y=np.array([r["y"] for r in source]);f=np.array([r["frozen"] for r in source]);by=[np.where(y==k)[0] for k in range(3)];vals=[]
 for _ in range(reps):
  ix=sample_idx(by,P0,n,rng);vals.append(float(np.sum(np.abs(bbse(C,f[ix])-P0))))
 return float(np.quantile(vals,.95)),vals
def main():
 p51=load_feature_pool("051");p52=load_feature_pool("052");p53=load_feature_pool("053")
 pools={"052":p52,"053":p53};rng=np.random.default_rng(SEED)
 metric_rows=[];prior_rows=[];select_rows=[];actual_rows=[];freeze_sources={}
 for target_name in ("052","053"):
  other="053" if target_name=="052" else "052";source=p51+pools[other];target=pools[target_name]
  Zs=np.stack([r["Z"] for r in source]);ys=np.array([r["y"] for r in source]);fs=np.array([r["frozen"] for r in source])
  Zt=np.stack([r["Z"] for r in target]);yt=np.array([r["y"] for r in target]);ft=np.array([r["frozen"] for r in target])
  Cbb=cond_cm(ys,fs);policies=build_policies(Zs,ys);by=[np.where(yt==k)[0] for k in range(3)]
  thresholds={}
  for n in sorted(set(BATCH+(len(target),))):
   tau,_=null_threshold(source,Cbb,n,NULL_REPS,rng);thresholds[n]=tau
  freeze_sources[target_name]=dict(other_source=other,source_n=len(source),source_GT=dict(Counter(ys.tolist())),
    bbse_confusion=Cbb.tolist(),thresholds={str(k):v for k,v in thresholds.items()},policy_n=len(policies))
  # Natural target batch: no target labels used until after selection.
  pbb=bbse(Cbb,ft);dist=float(np.sum(np.abs(pbb-P0)));trigger=dist>thresholds[len(target)]
  selected={}
  for obj in ("PA","MCC"):
   q=choose_policy(policies,pbb,obj);selected[obj]=q
   bs,bn=(q[1],q[2]) if trigger else (float(B0[0]),float(B0[1]))
   actual_rows.append(dict(target=target_name,method="Detect"+obj,trigger=trigger,prior_L1=dist,est_S=pbb[0],est_NS=pbb[1],est_NA=pbb[2],bs=bs,bn=bn,**metrics(yt,predict_bias(Zt,bs,bn))))
  actual_rows += [
   dict(target=target_name,method="FrozenPriorG",trigger=False,prior_L1=dist,est_S=pbb[0],est_NS=pbb[1],est_NA=pbb[2],bs=B0[0],bn=B0[1],**metrics(yt,predict_bias(Zt,B0[0],B0[1]))),
   dict(target=target_name,method="NaiveBBSEPriorG",trigger=True,prior_L1=dist,est_S=pbb[0],est_NS=pbb[1],est_NA=pbb[2],**metrics(yt,predict_naive_prior(Zt,pbb)))]
  for m in ("U2","GateA","O"):
   actual_rows.append(dict(target=target_name,method={"O":"O_Verifact"}.get(m,m),trigger=False,prior_L1=dist,est_S=pbb[0],est_NS=pbb[1],est_NA=pbb[2],**metrics(yt,np.array([r[m] for r in target]))))
  for scen,pt in SCEN.items():
   for n in BATCH:
    agg=defaultdict(list);sel=Counter();trigs=[];pL1=[]
    for rep in range(REPS):
     ia=sample_idx(by,pt,n,rng);ie=sample_idx(by,pt,EVAL_N,rng);pest=bbse(Cbb,ft[ia]);dd=float(np.sum(np.abs(pest-P0)));active=dd>thresholds[n]
     ye=yt[ie];ze=Zt[ie];trigs.append(float(active));pL1.append(float(np.sum(np.abs(pest-pt))))
     preds={"FrozenPriorG":predict_bias(ze,B0[0],B0[1]),"NaiveBBSEPriorG":predict_naive_prior(ze,pest),
       "U2":np.array([target[i]["U2"] for i in ie]),"GateA":np.array([target[i]["GateA"] for i in ie]),"O_Verifact":np.array([target[i]["O"] for i in ie])}
     for obj in ("PA","MCC"):
      q=choose_policy(policies,pest,obj);bs,bn=(q[1],q[2]) if active else (float(B0[0]),float(B0[1]));preds["Detect"+obj]=predict_bias(ze,bs,bn);sel[(obj,round(bs,6),round(bn,6))]+=1
      qo=choose_policy(policies,pt,obj);preds["OraclePolicy"+obj]=predict_bias(ze,qo[1],qo[2])
      preds["Always"+obj]=predict_bias(ze,q[1],q[2])
     for m,pr in preds.items():
      mm=metrics(ye,pr)
      for k,v in mm.items():agg[(m,k)].append(v)
    prior_rows.append(dict(target=target_name,scenario=scen,batch_n=n,BBSE_L1_mean=float(np.mean(pL1)),BBSE_L1_q025=float(np.quantile(pL1,.025)),BBSE_L1_q975=float(np.quantile(pL1,.975)),
      trigger_rate=float(np.mean(trigs)),threshold=thresholds[n],true_shift_L1=float(np.sum(np.abs(pt-P0)))))
    methods=sorted({k[0] for k in agg})
    for m in methods:
     row=dict(target=target_name,scenario=scen,batch_n=n,method=m,reps=REPS)
     for met in ("PA","MCC","false_S","S_recall","NS_recall","NA_recall"):
      s=summarize(agg[(m,met)]);row.update({f"{met}_{k}":v for k,v in s.items()})
     if m!="FrozenPriorG":
      for met in ("PA","MCC","false_S"):
       d=np.asarray(agg[(m,met)])-np.asarray(agg[("FrozenPriorG",met)]);s=summarize(d);row.update({f"delta_{met}_vs_frozen_{k}":v for k,v in s.items()})
     metric_rows.append(row)
    for (obj,bs,bn),count in sel.items():select_rows.append(dict(target=target_name,scenario=scen,batch_n=n,objective=obj,bs=bs,bn=bn,count=count,rate=count/REPS))
    print(target_name,scen,n,"trigger",round(float(np.mean(trigs)),3),flush=True)
 csvwrite(OUT/"simulation_metrics.csv",metric_rows);csvwrite(OUT/"prior_and_trigger.csv",prior_rows);csvwrite(OUT/"policy_selection.csv",select_rows);csvwrite(OUT/"actual_batch_results.csv",actual_rows)
 freeze=dict(created_utc="2026-09-22",seed=SEED,reps=REPS,null_reps=NULL_REPS,eval_n=EVAL_N,batch_sizes=list(BATCH),source_prior=P0.tolist(),calibration_prior=CAL.tolist(),G=G,B0=B0.tolist(),
  policy_grid=dict(S=[float(BS[0]),float(BS[-1]),.25],NS=[float(BN[0]),float(BN[-1]),.25],NA=0),scenarios={k:v.tolist() for k,v in SCEN.items()},sources=freeze_sources,
  protocol_sha256=sha(TASK/"protocol.md"),api_calls=0)
 put(OUT/"freeze.json",freeze)
 print("055 COMPLETE",len(metric_rows),len(prior_rows),len(actual_rows),flush=True)
if __name__=="__main__":main()
