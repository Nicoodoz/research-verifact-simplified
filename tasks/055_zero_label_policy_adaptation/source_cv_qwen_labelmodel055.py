from pathlib import Path
import json,csv,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
CFG=[(s,t,u) for s in (5,20,100,500) for t in (.25,.3,.35,.4,.5,.6,.8) for u in (False,True)]
def load(pool):
 rr=[json.loads(s) for s in (OUT/f"features_qwen_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[];S=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  ns=z(r["ns_scores"]);ts=z(r["ts_scores"],G);q=z(r["qwen_scores"])
  L.append([np.argmax(ns),np.argmax(ns+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(q),np.argmax(q+[2,0,0])]);Y.append(LI[r["GT"]]);S.append(r["sid"])
 return np.array(Y),np.array(L),np.array(S)
def base_counts(y,L,alpha=.5):
 C=np.full((L.shape[1],3,3),alpha,float)
 for i in range(len(y)):
  for m in range(L.shape[1]):C[m,y[i],L[i,m]]+=1
 return C/C.sum(2,keepdims=True)
def fitC(base,LA,p,strength,temp,up):
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
  pn=R.mean(0) if up else pp
  if max(np.max(abs(N-C)),np.max(abs(pn-pp)))<1e-9:C,pp=N,pn;break
  C,pp=N,pn
 return C,pp
def predict(C,L,p,temp):
 lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(L),0)
 for m in range(L.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,L[:,m]],1e-12))
 return np.argmax(lp,1)
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
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);rec=np.array([C[k,k]/C[k].sum() for k in range(3)])
 return dict(PA=float((y==p).mean()),MCC=float(mcc(y,p)),falseS=int(((y!=0)&(p==0)).sum()),rec=rec,correct=int((y==p).sum()))
def cv(source,cfg):
 y,L,sid=source;fold=np.array([int(hashlib.sha256(x.encode()).hexdigest()[:8],16)%5 for x in sid]);pred=np.full(len(y),-1,int)
 for f in range(5):
  tr=fold!=f;va=fold==f
  if not np.any(va):continue
  base=base_counts(y[tr],L[tr]);p=bbse(Cpred(y[tr],L[tr,4]),L[va,4]);C,pp=fitC(base,L[va],p,*cfg);pred[va]=predict(C,L[va],pp,cfg[1])
 assert np.all(pred>=0);return met(y,pred)
pools={k:load(k) for k in ("052","053")}
rows=[]
for source_name,target_name in [("052","053"),("053","052")]:
 source=pools[source_name];yt,Lt,_=pools[target_name];basepg=met(source[0],source[1][:,4]);cand=[]
 for cfg in CFG:
  mm=cv(source,cfg)
  strict=mm["PA"]>=basepg["PA"]-1e-12 and mm["MCC"]>=basepg["MCC"]-1e-12 and mm["falseS"]<=basepg["falseS"] and np.all(mm["rec"]>=basepg["rec"]-1e-12)
  # safe score: favor MCC, then PA, then false-S and minimum class recall.
  key=(int(strict),mm["MCC"],mm["PA"],-mm["falseS"],float(np.min(mm["rec"])))
  cand.append((key,cfg,mm))
 best=max(cand,key=lambda x:x[0]);key,cfg,cvmm=best
 ys,Ls,_=source;base=base_counts(ys,Ls);p=bbse(Cpred(ys,Ls[:,4]),Lt[:,4]);C,pp=fitC(base,Lt,p,*cfg);pr=predict(C,Lt,pp,cfg[1]);tm=met(yt,pr);pgm=met(yt,Lt[:,4])
 print("\n",source_name,"->",target_name,"sourcePG",basepg,"selected",cfg,"strict",bool(key[0]),"CV",cvmm,"p",np.round(p,3),"pfin",np.round(pp,3))
 print("TARGET adapt",tm);print("TARGET PG",pgm)
 rows.append(dict(source=source_name,target=target_name,strength=cfg[0],temp=cfg[1],update_prior=cfg[2],source_strict=bool(key[0]),source_cv_PA=cvmm["PA"],source_cv_MCC=cvmm["MCC"],source_cv_falseS=cvmm["falseS"],source_cv_S=cvmm["rec"][0],source_cv_NS=cvmm["rec"][1],source_cv_NA=cvmm["rec"][2],est_S=p[0],est_NS=p[1],est_NA=p[2],final_S=pp[0],final_NS=pp[1],final_NA=pp[2],target_PA=tm["PA"],target_MCC=tm["MCC"],target_falseS=tm["falseS"],target_S=tm["rec"][0],target_NS=tm["rec"][1],target_NA=tm["rec"][2],PG_PA=pgm["PA"],PG_MCC=pgm["MCC"],PG_falseS=pgm["falseS"],PG_S=pgm["rec"][0],PG_NS=pgm["rec"][1],PG_NA=pgm["rec"][2]))
with (OUT/"source_cv_qwen_labelmodel_actual.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
