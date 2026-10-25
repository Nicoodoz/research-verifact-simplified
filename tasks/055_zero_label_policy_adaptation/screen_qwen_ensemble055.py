from pathlib import Path
import json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
def load(pool):
 rr=[json.loads(s) for s in (OUT/f"features_qwen_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 Y=[];L=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  ns=z(r["ns_scores"]);ts=z(r["ts_scores"],G);q=z(r["qwen_scores"])
  L.append([np.argmax(ns),np.argmax(ns+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(q),np.argmax(q+[2,0,0])]);Y.append(LI[r["GT"]])
 return np.array(Y),np.array(L)
def nb_fit(y,L,idx,alpha):
 C=np.full((len(idx),3,3),alpha,float)
 for i,m in enumerate(idx):
  for yy,ll in zip(y,L[:,m]):C[i,yy,ll]+=1
 C/=C.sum(2,keepdims=True);return C
def nb_loglike(C,L,idx):
 O=np.zeros((len(L),3))
 for i,m in enumerate(idx):
  for y in range(3):O[:,y]+=np.log(np.maximum(C[i,y,L[:,m]],1e-12))
 return O
def em_prior(A,init):
 p=init.copy()
 for _ in range(1000):
  X=A+np.log(np.maximum(p,1e-12))[None,:];X-=X.max(1,keepdims=True);R=np.exp(X);R/=R.sum(1,keepdims=True);n=R.mean(0)
  if np.max(abs(n-p))<1e-10:return n
  p=n
 return p
def patt_fit(y,L,idx,alpha):
 code=np.zeros(len(L),int)
 for m in idx:code=code*3+L[:,m]
 K=3**len(idx);T=np.full((3,K),alpha,float)
 for yy,c in zip(y,code):T[yy,c]+=1
 T/=T.sum(1,keepdims=True);return T
def patt_loglike(T,L,idx):
 c=np.zeros(len(L),int)
 for m in idx:c=c*3+L[:,m]
 return np.log(np.maximum(T[:,c].T,1e-12))
def pred(A,p):
 return np.argmax(A+np.log(np.maximum(p,1e-12))[None,:],1)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)],prev=np.round(np.bincount(p,minlength=3)/len(p),3).tolist())
pools={k:load(k) for k in ("052","053")}
subs=[(4,5),(4,6),(1,4,5),(1,4,6),(0,1,4,5),(0,1,4,6),(1,3,4,5),(1,3,4,6),(0,1,2,3,4,5,6)]
for src,tgt in [("052","053"),("053","052")]:
 ys,Ls=pools[src];yt,Lt=pools[tgt]
 print("\n",src,"->",tgt,"PG",met(yt,Lt[:,4]),"Q0",met(yt,Lt[:,5]),"Q2",met(yt,Lt[:,6]))
 for kind in ("NB","PATT"):
  for idx in subs:
   best=None
   alphas=[.1,.5,1,2,5,10] if kind=="PATT" else [.1,.5,1,2,5]
   for a in alphas:
    if kind=="NB":M=nb_fit(ys,Ls,idx,a);As=nb_loglike(M,Ls,idx);At=nb_loglike(M,Lt,idx)
    else:M=patt_fit(ys,Ls,idx,a);As=patt_loglike(M,Ls,idx);At=patt_loglike(M,Lt,idx)
    # select alpha source-only by balanced class log likelihood of pattern conditional (no prior)
    score=float(np.mean([np.mean(As[ys==k,k]) for k in range(3)]))
    if best is None or score>best[0]:best=(score,a,At)
   _,a,At=best;p=em_prior(At,P0);pr=pred(At,p)
   print(kind,idx,"a",a,"p",np.round(p,3),met(yt,pr))
