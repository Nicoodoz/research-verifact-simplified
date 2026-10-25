from pathlib import Path
import csv,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2];BS=np.arange(.5,3.01,.25);BN=np.arange(-1.5,1.51,.25)
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 Z=[];y=[]
 for r in rr:
  sc=r["ts_scores"];z=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));z[0]+=G;Z.append(z);y.append(LI[r["GT"]])
 return np.array(Z),np.array(y)
def Cmat(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def expm(C,p):
 M=C*p[None,:];pa=float(np.trace(M));fs=float(M[0,1]+M[0,2]);s=M.sum();t=M.sum(0);q=M.sum(1);c=np.trace(M);d=((s*s-q@q)*(s*s-t@t))**.5;m=(c*s-q@t)/d if d else 0.;rec=[float(C[k,k]) for k in range(3)];return pa,float(m),fs,rec
def build(Z,y):
 return [(float(bs),float(bn),Cmat(y,np.argmax(Z+np.array([bs,bn,0])[None,:],1))) for bs in BS for bn in BN]+[(float(B0[0]),float(B0[1]),Cmat(y,np.argmax(Z+B0[None,:],1)))]
def choose(dompol,p,obj,guard=False):
 # dompol list of same policy grids per source domain
 best=None;base=[]
 for D in dompol:
  b=min(D,key=lambda x:abs(x[0]-B0[0])+abs(x[1]-B0[1]));base.append(expm(b[2],p))
 for j in range(len(dompol[0])):
  stats=[expm(D[j][2],p) for D in dompol];bs,bn=dompol[0][j][:2]
  if guard:
   # candidate must not worsen predicted MCC or false-S in either source domain; allow <=1pp PA loss
   if any(stats[d][1]+1e-12<base[d][1] or stats[d][2]>base[d][2]+1e-12 or stats[d][0]+.01<base[d][0] for d in range(len(stats))):continue
  minpa=min(x[0] for x in stats);minm=min(x[1] for x in stats);maxfs=max(x[2] for x in stats);minrec=min(min(x[3]) for x in stats)
  key=(minm,minpa,-maxfs,minrec) if obj=="MCC" else (minpa,minm,-maxfs,minrec)
  if best is None or key>best[0]:best=(key,bs,bn,stats)
 if best is None:return (None,float(B0[0]),float(B0[1]),base)
 return best
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
pools={k:load(k) for k in ("051","052","053")}
for other,tgt in [("052","053"),("053","052")]:
 pbbrow=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(pbbrow["p_Supported"]),float(pbbrow["p_Not Supported"]),float(pbbrow["p_Not Addressed"])])
 Zt,yt=pools[tgt];dom=[build(*pools["051"]),build(*pools[other])]
 print("\n",other,"->",tgt,"pbb",np.round(pbb,3))
 for guard in (False,True):
  for obj in ("PA","MCC"):
   q=choose(dom,pbb,obj,guard);pr=np.argmax(Zt+np.array([q[1],q[2],0])[None,:],1);print("robust",obj,"guard",guard,"bias",q[1],q[2],"target",met(yt,pr))
 print("frozen",met(yt,np.argmax(Zt+B0[None,:],1)))
