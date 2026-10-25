from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
def load(pool):
 rr=[json.loads(s) for s in (OUT/f"features_qwen_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  ns=z(r["ns_scores"]);ts=z(r["ts_scores"],G);q=z(r["qwen_scores"])
  L.append([np.argmax(ns),np.argmax(ns+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(q),np.argmax(q+[2,0,0])]);Y.append(LI[r["GT"]])
 return np.array(Y),np.array(L)
def base_counts(y,L,alpha=.5):
 C=np.full((L.shape[1],3,3),alpha,float)
 for i in range(len(y)):
  for m in range(L.shape[1]):C[m,y[i],L[i,m]]+=1
 return C/C.sum(2,keepdims=True)
def fitC(base,LA,p,strength,temp,update_prior):
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
  pn=R.mean(0) if update_prior else pp
  if max(np.max(abs(N-C)),np.max(abs(pn-pp)))<1e-9:C,pp=N,pn;break
  C,pp=N,pn
 return C,pp
def predict(C,L,p,temp):
 lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(L),0)
 for m in range(L.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,L[:,m]],1e-12))
 return np.argmax(lp,1)
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(3)+1)>0)[0];rho=idx[-1];th=css[rho]/(rho+1);return np.maximum(v-th,0)
def bbse(C,hard):
 q=np.bincount(hard,minlength=3)/len(hard);p=P0.copy();step=1/(np.sum(C*C)+1e-12)
 for _ in range(3000):
  n=project(p-step*C.T@(C@p-q))
  if np.max(abs(n-p))<1e-11:break
  p=n
 p=np.maximum(p,1e-9);return p/p.sum()
def Cpred(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
pools={k:load(k) for k in ("052","053")}
for src,tgt in [("052","053"),("053","052")]:
 ys,Ls=pools[src];yt,Lt=pools[tgt];base=base_counts(ys,Ls);pbb=bbse(Cpred(ys,Ls[:,4]),Lt[:,4])
 print("\n",src,"->",tgt,"pbb",np.round(pbb,3),"PG",met(yt,Lt[:,4]))
 for strength in (5,20,100,500):
  for temp in (.2,.3,.4,.5,.6,.8):
   for up in (False,True):
    C,p=fitC(base,Lt,pbb,strength,temp,up);pr=predict(C,Lt,p,temp);m=met(yt,pr)
    if m["PA"]>=.83 or m["MCC"]>=.57:
     print("s",strength,"t",temp,"up",up,"p",np.round(p,3),m)
