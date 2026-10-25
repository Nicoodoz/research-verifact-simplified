from pathlib import Path
import csv,json,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  nt=z(r["ns_scores"]);ts=z(r["ts_scores"],G);L.append([np.argmax(nt),np.argmax(nt+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(nt+B0)]);Y.append(LI[r["GT"]])
 return np.array(Y),np.array(L)
def base_counts(y,L):
 C=np.full((L.shape[1],3,3),.5)
 for i in range(len(y)):
  for m in range(L.shape[1]):C[m,y[i],L[i,m]]+=1
 return C/C.sum(2,keepdims=True)
def adapt(yS,LS,LT,p,strength=20,temp=.3):
 base=base_counts(yS,LS);C=base.copy()
 for _ in range(300):
  lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(LT),0)
  for m in range(LT.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,LT[:,m]],1e-12))
  lp-=lp.max(1,keepdims=True);R=np.exp(lp);R/=R.sum(1,keepdims=True)
  N=np.empty_like(C)
  for m in range(LT.shape[1]):
   for y in range(3):
    v=strength*base[m,y].copy()
    for l in range(3):v[l]+=R[LT[:,m]==l,y].sum()
    N[m,y]=v/v.sum()
  if np.max(abs(N-C))<1e-9:C=N;break
  C=N
 lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(LT),0)
 for m in range(LT.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,LT[:,m]],1e-12))
 lp-=lp.max(1,keepdims=True);R=np.exp(lp);R/=R.sum(1,keepdims=True)
 return R
def predthr(R,tS):
 nons=np.where(R[:,1]>=R[:,2],1,2);return np.where(R[:,0]>=tS,0,nons)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return [(y==p).mean(),mcc(y,p),int(((y!=0)&(p==0)).sum())]+[C[k,k]/C[k].sum() for k in range(3)]
pools={k:load(k) for k in ("051","052","053")}
for other,tgt in [("052","053"),("053","052")]:
 y1,L1=pools["051"];yo,Lo=pools[other];yt,Lt=pools[tgt];ys=np.r_[y1,yo];Ls=np.vstack([L1,Lo])
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");p=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 R=adapt(ys,Ls,Lt,p)
 print("\n",other,"->",tgt)
 for t in np.arange(.35,.951,.05):
  print(round(float(t),2),*[round(x,4) for x in met(yt,predthr(R,t))])
