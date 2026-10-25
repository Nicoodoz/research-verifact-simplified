from pathlib import Path
import csv,json,hashlib,math,numpy as np
from sklearn.tree import DecisionTreeClassifier
ROOT=Path(__file__).resolve().parents[2]
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum()
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(pool):
 rr=[json.loads(s) for s in (ROOT/f"outputs/055_zero_label_policy_adaptation/features_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 X=np.array([[r["ts_scores"][k]/100 for k in LABS]+[r["ns_scores"][k]/100 for k in LABS] for r in rr],float)
 y=np.array([LI[r["GT"]] for r in rr]);g=np.array([r["sid"] for r in rr]);return X,y,g
def leaf_model(tree,X,y,alpha=.5):
 leaf=tree.apply(X);ids=np.unique(leaf);tab={}
 totals=np.bincount(y,minlength=3).astype(float)
 for l in ids:
  ix=leaf==l;c=np.bincount(y[ix],minlength=3).astype(float)
  tab[int(l)]=(c+alpha)/(totals+alpha*len(ids))
 return tab
def posterior(tree,tab,X,p):
 leaf=tree.apply(X);P=np.empty((len(X),3))
 for i,l in enumerate(leaf):
  like=tab.get(int(l),np.ones(3)*1e-9);q=like*p;q=np.maximum(q,1e-15);P[i]=q/q.sum()
 return P
def balnll(y,P):
 c=np.bincount(y,minlength=3);w=np.array([len(y)/(3*c[k]) for k in y]);return float(-(w*np.log(np.maximum(P[np.arange(len(y)),y],1e-12))).sum()/w.sum())
def mcc(y,p):
 cm=np.zeros((3,3),float);np.add.at(cm,(y,p),1);s=cm.sum();c=np.trace(cm);t=cm.sum(1);q=cm.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (c*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 cm=np.zeros((3,3),int);np.add.at(cm,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(cm[k,k]/cm[k].sum(),4) for k in range(3)])
X51,y51,g51=load("051")
for other,tgt in [("052","053"),("053","052")]:
 Xo,yo,go=load(other);Xt,yt,_=load(tgt);X=np.vstack([X51,Xo]);y=np.r_[y51,yo];g=np.r_[g51,go]
 fold=np.array([int(hashlib.sha256(s.encode()).hexdigest()[:8],16)%5 for s in g]);best=None
 for depth in [1,2,3,4,5]:
  P=np.zeros((len(y),3))
  for f in range(5):
   tr=fold!=f;va=fold==f
   if not va.any():continue
   tree=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=10,class_weight="balanced",random_state=55).fit(X[tr],y[tr])
   tab=leaf_model(tree,X[tr],y[tr]);P[va]=posterior(tree,tab,X[va],np.ones(3)/3)
  ll=balnll(y,P)
  if best is None or ll<best[0]:best=(ll,depth)
 ll,depth=best;tree=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=10,class_weight="balanced",random_state=55).fit(X,y);tab=leaf_model(tree,X,y)
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])]);ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\n051+",other,"->",tgt,"depth",depth,"sourceOOF balNLL",round(ll,4),"leaves",tree.get_n_leaves(),"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 for nm,p in [("fixed",P0),("bbse",pbb),("oracle",ptrue)]:print(nm,met(yt,np.argmax(posterior(tree,tab,Xt,p),axis=1)))
