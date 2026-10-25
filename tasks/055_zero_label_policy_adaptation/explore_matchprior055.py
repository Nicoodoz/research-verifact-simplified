from pathlib import Path
import csv,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
BS=np.arange(-1.0,4.01,.1);BN=np.arange(-2.5,2.51,.1)
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 Z=[];y=[]
 for r in rr:
  sc=r["ts_scores"];z=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));z[0]+=G;Z.append(z);y.append(LI[r["GT"]])
 return np.array(Z),np.array(y)
def cm(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5
 return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
def expected(C,p):
 M=C*p[None,:];pa=np.trace(M);fs=M[0,1]+M[0,2];s=M.sum();a=M.sum(0);b=M.sum(1);cc=np.trace(M);d=((s*s-a@a)*(s*s-b@b))**.5;mc=(cc*s-a@b)/d if d else 0.
 return float(pa),float(mc),float(fs)
def choose(Ztarget,pest,Zsource,ysource):
 best=None
 for bs in BS:
  # vectorize over BN
  P=np.argmax(Ztarget[:,None,:]+np.stack([np.full(len(BN),bs),BN,np.zeros(len(BN))],axis=1)[None,:,:],axis=2)
  for j,bn in enumerate(BN):
   pred=P[:,j];ph=np.bincount(pred,minlength=3)/len(pred);err=float(np.sum(np.abs(ph-pest)))
   ps=np.argmax(Zsource+np.array([bs,bn,0.])[None,:],axis=1);C=cm(ysource,ps);pa,mc,fs=expected(C,pest)
   # primary: match target prevalence; within 2/N total L1 use source MCC/PA/risk and closeness to B0
   key=(err,-mc,-pa,fs,abs(bs-B0[0])+abs(bn-B0[1]))
   if best is None or key<best[0]:best=(key,bs,bn,ph,pa,mc,fs)
 return best
Z51,y51=load("051")
for other,tgt in [("052","053"),("053","052")]:
 Zo,yo=load(other);Zt,yt=load(tgt);Zs=np.vstack([Z51,Zo]);ys=np.r_[y51,yo]
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled")
 pest=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 q=choose(Zt,pest,Zs,ys);pred=np.argmax(Zt+np.array([q[1],q[2],0])[None,:],axis=1)
 print("\n",other,"->",tgt,"pest",np.round(pest,3),"bias",round(q[1],2),round(q[2],2),"predprev",np.round(q[3],3),"sourceexp",round(q[4],3),round(q[5],3),round(q[6],3),"target",met(yt,pred))
 p0=np.argmax(Zt+B0[None,:],axis=1);print("frozen",met(yt,p0))
