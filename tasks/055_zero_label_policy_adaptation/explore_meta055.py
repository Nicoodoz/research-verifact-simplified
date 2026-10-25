from pathlib import Path
import csv,json,math,numpy as np
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.metrics import matthews_corrcoef
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum()
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def f(sc):
 p=np.array([sc[k]/100 for k in LABS],float);z=np.log(np.maximum(p,1e-6))
 return list(p)+[z[0]-z[1],z[0]-z[2],z[1]-z[2],-np.sum(p*np.log(np.maximum(p,1e-6)))]
def load(pool):
 rr=[json.loads(s) for s in (OUT/f"features_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 X=np.array([f(r["ts_scores"])+f(r["ns_scores"]) for r in rr]);y=np.array([LI[r["GT"]] for r in rr]);g=np.array([r["sid"] for r in rr])
 return X,y,g
def reweight_proba(P,p):
 q=P*np.maximum(p,1e-8)[None,:];q/=q.sum(1,keepdims=True);return q
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
def models():
 for leaf in [2,5,10,20]:
  yield f"ET{leaf}",ExtraTreesClassifier(n_estimators=300,min_samples_leaf=leaf,class_weight="balanced",max_features=None,random_state=55,n_jobs=1)
  yield f"RF{leaf}",RandomForestClassifier(n_estimators=300,min_samples_leaf=leaf,class_weight="balanced_subsample",max_features="sqrt",random_state=55,n_jobs=1)
 yield "HGB",HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=7,l2_regularization=2,learning_rate=.05,random_state=55,class_weight="balanced")
X51,y51,g51=load("051")
for other,tgt in [("052","053"),("053","052")]:
 Xo,yo,go=load(other);Xt,yt,_=load(tgt);X=np.vstack([X51,Xo]);y=np.r_[y51,yo]
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])]);ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\n",other,"->",tgt,"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 for name,m in models():
  try:
   m.fit(X,y);P=m.predict_proba(Xt);classes=list(m.classes_);Q=np.zeros((len(P),3))
   for j,k in enumerate(classes):Q[:,int(k)]=P[:,j]
   # balanced training approximates uniform prior, so apply target prior directly
   print(name,"fixed",met(yt,np.argmax(reweight_proba(Q,P0),1)),"bbse",met(yt,np.argmax(reweight_proba(Q,pbb),1)),"oracle",met(yt,np.argmax(reweight_proba(Q,ptrue),1)))
  except Exception as e: print(name,"ERR",repr(e))
