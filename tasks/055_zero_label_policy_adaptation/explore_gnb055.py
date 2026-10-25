from pathlib import Path
import csv,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2]
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum()
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def feat(sc):
 s=math.log(max(sc["Supported"]/100,1e-6));ns=math.log(max(sc["Not Supported"]/100,1e-6));na=math.log(max(sc["Not Addressed"]/100,1e-6))
 return [s-na,ns-na]
def load(pool):
 rr=[json.loads(s) for s in (ROOT/f"outputs/055_zero_label_policy_adaptation/features_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 X=np.array([feat(r["ts_scores"])+feat(r["ns_scores"]) for r in rr]);y=np.array([LI[r["GT"]] for r in rr])
 return X,y
def fit(X,y):
 mu=np.stack([X[y==k].mean(0) for k in range(3)])
 va=np.stack([X[y==k].var(0,ddof=1) for k in range(3)])
 floor=1e-3*np.maximum(X.var(0),1e-6);va=np.maximum(va,floor[None,:]);return mu,va
def loglik(m,X):
 mu,va=m;O=np.empty((len(X),3))
 for k in range(3):
  d=X-mu[k];O[:,k]=-.5*np.sum(np.log(va[k])[None,:]+d*d/va[k][None,:],axis=1)
 return O
def pred(L,p):return np.argmax(L+np.log(np.maximum(p,1e-12))[None,:],axis=1)
def mcc(y,p):
 cm=np.zeros((3,3),float);np.add.at(cm,(y,p),1);s=cm.sum();c=np.trace(cm);t=cm.sum(1);q=cm.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (c*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 cm=np.zeros((3,3),int);np.add.at(cm,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(cm[k,k]/cm[k].sum(),4) for k in range(3)])
X51,y51=load("051")
for other,tgt in [("052","053"),("053","052")]:
 Xo,yo=load(other);Xt,yt=load(tgt);X=np.vstack([X51,Xo]);y=np.r_[y51,yo]
 L=loglik(fit(X,y),Xt);z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled")
 pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])]);ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\n051+",other,"->",tgt,"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 print("fixed",met(yt,pred(L,P0)));print("bbse",met(yt,pred(L,pbb)));print("oracle",met(yt,pred(L,ptrue)))
