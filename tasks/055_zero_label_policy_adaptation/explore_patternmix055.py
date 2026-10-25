from pathlib import Path
import json,csv,numpy as np
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
def codes(L,idx):
 c=np.zeros(len(L),int)
 for j in idx:c=c*3+L[:,j]
 return c,3**len(idx)
def tab(y,L,idx,alpha):
 co,K=codes(L,idx);T=np.full((3,K),alpha,float)
 for a,b in zip(y,co):T[a,b]+=1
 T/=T.sum(1,keepdims=True);return T
def choose_mix(T1,T2,c,p):
 best=None
 for w in np.linspace(0,1,101):
  T=w*T1+(1-w)*T2;prob=(p[:,None]*T).sum(0);ll=float(np.sum(np.log(np.maximum(prob[c],1e-15))))
  if best is None or ll>best[0]:best=(ll,w,T)
 return best
def pred(T,c,p):return np.argmax(np.log(np.maximum(T[:,c].T,1e-15))+np.log(np.maximum(p,1e-12))[None,:],1)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();cc=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (cc*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
pools={k:load(k) for k in ("051","052","053")}
subsets=[(0,1,2,3,4,5),(0,1,2,4),(0,1,4),(1,2,4),(0,2,4),(0,1,2),(1,4),(0,4),(2,4)]
for other,tgt in [("052","053"),("053","052")]:
 y1,L1=pools["051"];yo,Lo=pools[other];yt,Lt=pools[tgt];z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");p=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 print("\nTARGET",tgt,"prior",np.round(p,3),"PG",met(yt,Lt[:,4]))
 for idx in subsets:
  for a in [.1,.5,1,2,5,10]:
   T1=tab(y1,L1,idx,a);T2=tab(yo,Lo,idx,a);ct,K=codes(Lt,idx);ll,w,T=choose_mix(T1,T2,ct,p);pr=pred(T,ct,p);m=met(yt,pr)
   print("idx",idx,"a",a,"w051",round(w,2),m)
