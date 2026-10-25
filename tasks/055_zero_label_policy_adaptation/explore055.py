from pathlib import Path
import csv,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[2]
rows=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/case_table.csv").open(encoding="utf-8")))
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum()
def arr(pool):
 z=[r for r in rows if r["pool"]==pool]
 X=np.array([[float(r["zS"])-float(r["zNA"]),float(r["zNS"])-float(r["zNA"])] for r in z])
 y=np.array([LI[r["GT"]] for r in z]);g=np.array([r["sid"] for r in z])
 return X,y,g
def fit(X,y):
 mu=np.stack([X[y==k].mean(0) for k in range(3)])
 R=np.vstack([X[y==k]-mu[k] for k in range(3)]);den=max(1,len(X)-3)
 s00=float(np.sum(R[:,0]*R[:,0]))/den;s01=float(np.sum(R[:,0]*R[:,1]))/den;s11=float(np.sum(R[:,1]*R[:,1]))/den
 ridge=1e-4*(s00+s11)/2;s00+=ridge;s11+=ridge
 a,b,cc=s00,s01,s11;det=a*cc-b*b
 inv=np.array([[cc,-b],[-b,a]])/det
 return mu,inv
def loglik(model,X):
 mu,inv=model;out=[]
 for k in range(3):
  d=X-mu[k];q=inv[0,0]*d[:,0]*d[:,0]+2*inv[0,1]*d[:,0]*d[:,1]+inv[1,1]*d[:,1]*d[:,1];out.append(-.5*q)
 return np.stack(out,axis=1)
def pred(L,p):return np.argmax(L+np.log(np.maximum(p,1e-12))[None,:],axis=1)
def cmatrix(y,p):
 C=np.zeros((3,3));np.add.at(C,(p,y),1);C/=C.sum(axis=0,keepdims=True);return C
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(len(v))+1)>0)[0]
 rho=int(idx[-1]);theta=css[rho]/(rho+1);return np.maximum(v-theta,0)
def simplex(C,q):
 p=P0.copy();step=1/(float(np.sum(C*C))+1e-12)
 for _ in range(5000):
  cp=np.array([sum(C[i,j]*p[j] for j in range(3)) for i in range(3)]);res=cp-q
  grad=np.array([sum(C[i,j]*res[i] for i in range(3)) for j in range(3)])
  new=project(p-step*grad)
  if np.max(np.abs(new-p))<1e-12:break
  p=new
 p=np.maximum(p,1e-9);return p/p.sum()
def mcc(y,p):
 cm=np.zeros((3,3),float);np.add.at(cm,(y,p),1);s=cm.sum();c=np.trace(cm);t=cm.sum(1);q=cm.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (c*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 cm=np.zeros((3,3),int);np.add.at(cm,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),
 falseS=int(((y!=0)&(p==0)).sum()),rec=[round(cm[k,k]/cm[k].sum(),4) for k in range(3)])
for src,tgt in [("052","053"),("053","052")]:
 X,y,g=arr(src);Xt,yt,_=arr(tgt)
 folds=np.array([int(hashlib.sha256(s.encode()).hexdigest()[:8],16)%5 for s in g]);oof=np.zeros(len(y),int)
 for f in range(5):
  tr=folds!=f;va=folds==f
  if va.any():oof[va]=pred(loglik(fit(X[tr],y[tr]),X[va]),P0)
 C=cmatrix(y,oof);model=fit(X,y);Lt=loglik(model,Xt);fixed=pred(Lt,P0)
 q=np.bincount(fixed,minlength=3)/len(fixed);pbb=simplex(C,q);por=np.bincount(yt,minlength=3)/len(yt)
 print(src,"->",tgt,"pbb",np.round(pbb,3),"true",np.round(por,3))
 print("fixed",met(yt,fixed));print("bbse",met(yt,pred(Lt,pbb)));print("oracle",met(yt,pred(Lt,por)))
