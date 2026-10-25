from pathlib import Path
import csv,json,hashlib,math,numpy as np
ROOT=Path(__file__).resolve().parents[2]
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum();G=.1342909508820116
case=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/case_table.csv").open(encoding="utf-8")))
r051=[json.loads(s) for s in (ROOT/"outputs/055_zero_label_policy_adaptation/compact_051_scores.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def feat_scores(s,ns,na):
 z0=math.log(max(float(s)/100,1e-6))+G;z1=math.log(max(float(ns)/100,1e-6));z2=math.log(max(float(na)/100,1e-6))
 return [z0-z2,z1-z2]
def data(pool):
 if pool=="051":
  X=np.array([feat_scores(r["s"],r["ns"],r["na"]) for r in r051]);y=np.array([LI[r["GT"]] for r in r051]);g=np.array([r["sid"] for r in r051])
 else:
  rr=[r for r in case if r["pool"]==pool];X=np.array([[float(r["zS"])-float(r["zNA"]),float(r["zNS"])-float(r["zNA"])] for r in rr]);y=np.array([LI[r["GT"]] for r in rr]);g=np.array([r["sid"] for r in rr])
 return X,y,g
def prep(X):
 mu=X.mean(0);sd=X.std(0);sd=np.where(sd<1e-9,1,sd);return mu,sd
def logdens(Xtrain,ytrain,Xq,h,mu,sd):
 T=(Xtrain-mu)/sd;Q=(Xq-mu)/sd;O=np.empty((len(Q),3))
 for k in range(3):
  A=T[ytrain==k]
  for i,x in enumerate(Q):
   d0=A[:,0]-x[0];d1=A[:,1]-x[1];v=np.exp(-(d0*d0+d1*d1)/(2*h*h))
   O[i,k]=math.log(max(float(v.mean()),1e-300))
 return O
def post(L,p):
 A=L+np.log(np.maximum(p,1e-12))[None,:];A-=A.max(1,keepdims=True);E=np.exp(A);return E/E.sum(1,keepdims=True)
def pred(L,p):return np.argmax(L+np.log(np.maximum(p,1e-12))[None,:],axis=1)
def balnll(y,P):
 c=np.bincount(y,minlength=3);w=np.array([len(y)/(3*c[k]) for k in y]);return float(-(w*np.log(np.maximum(P[np.arange(len(y)),y],1e-12))).sum()/w.sum())
def mcc(y,p):
 cm=np.zeros((3,3),float);np.add.at(cm,(y,p),1);s=cm.sum();c=np.trace(cm);t=cm.sum(1);q=cm.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (c*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 cm=np.zeros((3,3),int);np.add.at(cm,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(cm[k,k]/cm[k].sum(),4) for k in range(3)])
X51,y51,g51=data("051")
for other,tgt in [("052","053"),("053","052")]:
 Xo,yo,go=data(other);Xt,yt,gt=data(tgt);X=np.vstack([X51,Xo]);y=np.r_[y51,yo];g=np.r_[g51,go]
 fold=np.array([int(hashlib.sha256(s.encode()).hexdigest()[:8],16)%5 for s in g]);best=None
 for h in [.25,.4,.6,.9,1.3,1.8]:
  P=np.zeros((len(y),3))
  for f in range(5):
   tr=fold!=f;va=fold==f
   if not va.any():continue
   mu,sd=prep(X[tr]);L=logdens(X[tr],y[tr],X[va],h,mu,sd);P[va]=post(L,np.ones(3)/3)
  loss=balnll(y,P)
  if best is None or loss<best[0]:best=(loss,h)
 loss,h=best;mu,sd=prep(X);Lt=logdens(X,y,Xt,h,mu,sd)
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled")
 pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\ntrain 051+",other,"target",tgt,"h",h,"sourceOOF balancedNLL",round(loss,4),"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 print("fixed",met(yt,pred(Lt,P0)));print("bbse",met(yt,pred(Lt,pbb)));print("oracle",met(yt,pred(Lt,ptrue)))
