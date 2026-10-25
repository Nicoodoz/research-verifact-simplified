from pathlib import Path
import json,csv,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();G=.1342909508820116
ALPHA=[5.,20.,100.,500.];TEMP=[.35,.6,1.0];PMODE=["fixed","anchor","update"];PK=[20.,100.]
def feat(sc1,sc2):
 def z(sc,g=0):
  x=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));x[0]+=g;return x
 a=z(sc1,G);b=z(sc2,0);return np.array([a[0]-a[2],a[1]-a[2],b[0]-b[2],b[1]-b[2]],float)
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 X=np.stack([feat(r["ts_scores"],r["ns_scores"]) for r in rr]);y=np.array([LI[r["GT"]] for r in rr])
 # PriorG hard prediction for BBSE/baseline
 CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();B=np.log(P0/CAL);B-=B[2]
 pg=[]
 for r in rr:
  a=np.log(np.maximum(np.array([r["ts_scores"][k]/100 for k in LABS],float),1e-6));a[0]+=G;pg.append(int(np.argmax(a+B)))
 return X,y,np.array(pg)
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
def fit_source(X,y):
 mu=X.mean(0);sd=X.std(0);sd=np.where(sd<1e-6,1,sd);Q=(X-mu)/sd
 means=np.stack([Q[y==k].mean(0) for k in range(3)])
 vars=np.stack([Q[y==k].var(0)+.15 for k in range(3)])
 return mu,sd,means,vars
def loglike(Q,means,vars,temp):
 O=np.empty((len(Q),3))
 for k in range(3):
  d=Q-means[k];O[:,k]=-.5*np.sum(np.log(vars[k])[None,:]+d*d/vars[k][None,:],axis=1)*temp
 return O
def adapt(Xs,ys,Xt,pinit,alpha,temp,pmode,pk):
 mu,sd,m0,v0=fit_source(Xs,ys);Q=(Xt-mu)/sd;m=m0.copy();v=v0.copy();p=pinit.copy()
 for _ in range(300):
  L=loglike(Q,m,v,temp)+np.log(np.maximum(p,1e-12))[None,:];L-=L.max(1,keepdims=True);R=np.exp(L);R/=R.sum(1,keepdims=True)
  N=R.sum(0)+1e-9;m1=np.empty_like(m);v1=np.empty_like(v)
  for k in range(3):
   tm=(R[:,k,None]*Q).sum(0)/N[k];ts=(R[:,k,None]*(Q*Q)).sum(0)/N[k]
   m1[k]=(alpha*m0[k]+N[k]*tm)/(alpha+N[k])
   sec=(alpha*(v0[k]+m0[k]**2)+N[k]*ts)/(alpha+N[k]);v1[k]=np.maximum(sec-m1[k]**2,.05)
  if pmode=="fixed":p1=pinit
  elif pmode=="anchor":p1=(pk*pinit+R.sum(0))/(pk+len(Q));p1/=p1.sum()
  else:p1=R.mean(0);p1=np.maximum(p1,1e-8);p1/=p1.sum()
  if max(np.max(abs(m1-m)),np.max(abs(v1-v)),np.max(abs(p1-p)))<1e-7:m,v,p=m1,v1,p1;break
  m,v,p=m1,v1,p1
 L=loglike(Q,m,v,temp)+np.log(np.maximum(p,1e-12))[None,:]
 return np.argmax(L,1),p
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);rec=np.array([C[k,k]/C[k].sum() for k in range(3)])
 return dict(PA=float((y==p).mean()),MCC=float(mcc(y,p)),falseS=float(((y!=0)&(p==0)).sum()/len(y)),rec=rec)
pools={k:load(k) for k in ("051","052","053")}
rows=[]
for target,other in [("052","053"),("053","052")]:
 # Hyperparameters selected only by 051<->other source-domain adaptation.
 candidates=[]
 for alpha in ALPHA:
  for temp in TEMP:
   for mode in PMODE:
    for pk in (PK if mode=="anchor" else [0.]):
     vals=[]
     for tr,val in [("051",other),(other,"051")]:
      Xs,ys,pgs=pools[tr];Xv,yv,pgv=pools[val];pest=bbse(Cpred(ys,pgs),pgv);pred,_=adapt(Xs,ys,Xv,pest,alpha,temp,mode,pk);vals.append(met(yv,pred))
     # robust target: class balance first enough to avoid collapse, then MCC/PA.
     minrec=min(float(np.min(v["rec"])) for v in vals);minm=min(v["MCC"] for v in vals);meanm=np.mean([v["MCC"] for v in vals]);meanpa=np.mean([v["PA"] for v in vals]);meanfs=np.mean([v["falseS"] for v in vals])
     key=(minrec,minm,meanm,meanpa,-meanfs)
     candidates.append((key,(alpha,temp,mode,pk),vals))
 best=max(candidates,key=lambda x:x[0]);key,cfg,vals=best
 # Final source uses 051 + nearest natural source; BBSE prior uses nearest natural source only.
 X1,y1,pg1=pools["051"];Xo,yo,pgo=pools[other];Xt,yt,pgt=pools[target];Xs=np.vstack([X1,Xo]);ys=np.r_[y1,yo]
 pest=bbse(Cpred(yo,pgo),pgt);pred,pfin=adapt(Xs,ys,Xt,pest,*cfg);mm=met(yt,pred);pgm=met(yt,pgt)
 print("\nTARGET",target,"selected",cfg,"CV",tuple(round(float(x),4) for x in key),"BBSE",np.round(pest,3),"finalp",np.round(pfin,3))
 for name,v in zip(("051",other),vals):print(" inner",name,{k:(np.round(x,3).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in v.items()})
 print(" adapt",{k:(np.round(x,3).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in mm.items()})
 print(" PG   ",{k:(np.round(x,3).tolist() if isinstance(x,np.ndarray) else round(float(x),4)) for k,x in pgm.items()})
 rows.append(dict(target=target,other_source=other,alpha=cfg[0],temp=cfg[1],prior_mode=cfg[2],prior_k=cfg[3],bbse_S=pest[0],bbse_NS=pest[1],bbse_NA=pest[2],final_S=pfin[0],final_NS=pfin[1],final_NA=pfin[2],PA=mm["PA"],MCC=mm["MCC"],falseS_rate=mm["falseS"],S_recall=mm["rec"][0],NS_recall=mm["rec"][1],NA_recall=mm["rec"][2],PG_PA=pgm["PA"],PG_MCC=pgm["MCC"],PG_falseS_rate=pgm["falseS"]))
with (OUT/"source_cv_gmm_actual.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
