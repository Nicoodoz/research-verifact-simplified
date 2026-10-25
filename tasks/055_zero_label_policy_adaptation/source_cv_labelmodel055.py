from pathlib import Path
import json,csv,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
STRENGTH=[5,10,20,50,100,200,500];TEMP=[.2,.25,.3,.35,.4,.5,.6,.75,1.0];UP=[False,True];MODES=["raw","PGS"]
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  nt=z(r["ns_scores"]);ts=z(r["ts_scores"],G);L.append([np.argmax(nt),np.argmax(nt+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(nt+B0)]);Y.append(LI[r["GT"]])
 return np.array(Y),np.array(L)
def Cpred(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(3)+1)>0)[0];rho=idx[-1];th=css[rho]/(rho+1);return np.maximum(v-th,0)
def bbse(C,hard):
 q=np.bincount(hard,minlength=3)/len(hard);p=P0.copy();step=1/(np.sum(C*C)+1e-12)
 for _ in range(3000):
  n=project(p-step*C.T@(C@p-q))
  if np.max(abs(n-p))<1e-11:break
  p=n
 p=np.maximum(p,1e-9);return p/p.sum()
def base_counts(y,L):
 C=np.full((L.shape[1],3,3),.5)
 for i in range(len(y)):
  for m in range(L.shape[1]):C[m,y[i],L[i,m]]+=1
 return C/C.sum(2,keepdims=True)
def fitC(base,LA,p,strength,temp,update):
 C=base.copy();pp=p.copy()
 for _ in range(300):
  lp=np.log(np.maximum(pp,1e-12))[None,:].repeat(len(LA),0)
  for m in range(LA.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,LA[:,m]],1e-12))
  lp-=lp.max(1,keepdims=True);R=np.exp(lp);R/=R.sum(1,keepdims=True);N=np.empty_like(C)
  for m in range(LA.shape[1]):
   for y in range(3):
    v=strength*base[m,y].copy()
    for l in range(3):v[l]+=R[LA[:,m]==l,y].sum()
    N[m,y]=v/v.sum()
  pn=R.mean(0) if update else pp
  if max(np.max(abs(N-C)),np.max(abs(pn-pp)))<1e-9:C,pp=N,pn;break
  C,pp=N,pn
 return C,pp
def predict(C,L,p,temp):
 lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(L),0)
 for m in range(L.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,L[:,m]],1e-12))
 return np.argmax(lp,1)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);rec=np.array([C[k,k]/C[k].sum() for k in range(3)])
 return dict(PA=float((y==p).mean()),MCC=float(mcc(y,p)),falseS=float(((y!=0)&(p==0)).sum()/len(y)),rec=rec)
def apply(train_y,train_L,target_L,cfg):
 st,t,u,mode=cfg;base=base_counts(train_y,train_L);Cbb=Cpred(train_y,train_L[:,4]);p=bbse(Cbb,target_L[:,4]);C,pp=fitC(base,target_L,p,st,t,u);pr=predict(C,target_L,pp,t)
 if mode=="PGS":pr=np.where((pr==0)&(target_L[:,4]!=0),target_L[:,4],pr)
 return pr,p
def cv_score(domains,cfg):
 vals=[]
 for trname,valname in [(domains[0],domains[1]),(domains[1],domains[0])]:
  yt,Lt=pools[trname];yv,Lv=pools[valname];pr,p=apply(yt,Lt,Lv,cfg);vals.append(met(yv,pr))
 minm=min(v["MCC"] for v in vals);meanm=np.mean([v["MCC"] for v in vals]);minpa=min(v["PA"] for v in vals);meanpa=np.mean([v["PA"] for v in vals]);meanfs=np.mean([v["falseS"] for v in vals]);minrec=min(float(np.min(v["rec"])) for v in vals)
 return (minm,meanm,minpa,meanpa,-meanfs,minrec),vals
pools={k:load(k) for k in ("051","052","053")}
rows=[]
for target,domains in [("052",("051","053")),("053",("051","052"))]:
 best=None
 candidates=[(st,t,u,m) for st in STRENGTH for t in TEMP for u in UP for m in MODES]
 for cfg in candidates:
  key,vals=cv_score(domains,cfg)
  if best is None or key>best[0]:best=(key,cfg,vals)
 key,cfg,vals=best
 ys=np.r_[pools[domains[0]][0],pools[domains[1]][0]];Ls=np.vstack([pools[domains[0]][1],pools[domains[1]][1]]);yt,Lt=pools[target];pr,p=apply(ys,Ls,Lt,cfg);mm=met(yt,pr);pg=met(yt,Lt[:,4])
 print("\nTARGET",target,"sources",domains,"selected",cfg,"CVkey",tuple(round(float(x),4) for x in key),"prior",np.round(p,3))
 for d,v in zip(domains,vals):print(" inner",d,{k:(np.round(x,4).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in v.items()})
 print(" target-adapt",{k:(np.round(x,4).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in mm.items()})
 print(" target-PG",{k:(np.round(x,4).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in pg.items()})
 rows.append(dict(target=target,sources="+".join(domains),strength=cfg[0],temp=cfg[1],update_prior=cfg[2],mode=cfg[3],est_S=p[0],est_NS=p[1],est_NA=p[2],PA=mm["PA"],MCC=mm["MCC"],falseS_rate=mm["falseS"],S_recall=mm["rec"][0],NS_recall=mm["rec"][1],NA_recall=mm["rec"][2],PG_PA=pg["PA"],PG_MCC=pg["MCC"],PG_falseS_rate=pg["falseS"]))
with (OUT/"source_cv_labelmodel_actual.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
