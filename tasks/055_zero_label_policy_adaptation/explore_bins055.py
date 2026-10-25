from pathlib import Path
import csv,json,numpy as np
ROOT=Path(__file__).resolve().parents[2]
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum()
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(pool):
 rr=[json.loads(s) for s in (ROOT/f"outputs/055_zero_label_policy_adaptation/features_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 def a(sc):return int(np.argmax([sc[x] for x in LABS]))
 b=np.array([a(r["ts_scores"])*3+a(r["ns_scores"]) for r in rr]);y=np.array([LI[r["GT"]] for r in rr]);return b,y
def fit(b,y,alpha=1.0):
 C=np.full((9,3),alpha,float)
 for x,t in zip(b,y):C[x,t]+=1
 C/=C.sum(axis=0,keepdims=True);return C
def pred(C,b,p):return np.array([int(np.argmax(np.log(C[x])+np.log(np.maximum(p,1e-12)))) for x in b])
def mcc(y,p):
 cm=np.zeros((3,3),float);np.add.at(cm,(y,p),1);s=cm.sum();c=np.trace(cm);t=cm.sum(1);q=cm.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (c*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 cm=np.zeros((3,3),int);np.add.at(cm,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(cm[k,k]/cm[k].sum(),4) for k in range(3)])
b51,y51=load("051")
for other,tgt in [("052","053"),("053","052")]:
 bo,yo=load(other);bt,yt=load(tgt);C=fit(np.r_[b51,bo],np.r_[y51,yo])
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])]);ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\n051+",other,"->",tgt,"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 print("fixed",met(yt,pred(C,bt,P0)));print("bbse",met(yt,pred(C,bt,pbb)));print("oracle",met(yt,pred(C,bt,ptrue)))
