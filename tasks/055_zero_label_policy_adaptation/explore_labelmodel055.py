from pathlib import Path
import csv,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 Y=[];L=[]
 for r in rr:
  def z(sc,g=0):
   a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  nt=z(r["ns_scores"]);ts=z(r["ts_scores"],G)
  labs=[
   np.argmax(nt),np.argmax(nt+np.array([2.,0,0])),
   np.argmax(ts),np.argmax(ts+np.array([2.,0,0])),
   np.argmax(ts+B0),
   np.argmax(nt+np.array([B0[0],B0[1],0]))
  ]
  Y.append(LI[r["GT"]]);L.append(labs)
 return np.array(Y),np.array(L,int)
def source_counts(y,L,alpha=.5):
 M=L.shape[1];C=np.full((M,3,3),alpha,float)
 for i in range(len(y)):
  for m in range(M):C[m,y[i],L[i,m]]+=1
 return C
def em(yS,LS,LT,pinit,strength=100,temp=.5,update_prior=True):
 C0=source_counts(yS,LS,alpha=.5);base=C0/C0.sum(2,keepdims=True);C=base.copy();p=pinit.copy()
 M=LT.shape[1]
 for it in range(500):
  logp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(LT),0)
  for m in range(M):
   logp += temp*np.log(np.maximum(C[m,:,LT[:,m]],1e-12))
  logp-=logp.max(1,keepdims=True);R=np.exp(logp);R/=R.sum(1,keepdims=True)
  if update_prior:
   pn=R.mean(0);pn=np.maximum(pn,1e-8);pn/=pn.sum()
  else:pn=p.copy()
  Cn=np.empty_like(C)
  for m in range(M):
   for y in range(3):
    cnt=strength*base[m,y].copy()
    for l in range(3):cnt[l]+=R[LT[:,m]==l,y].sum()
    Cn[m,y]=cnt/cnt.sum()
  if max(np.max(abs(pn-p)),np.max(abs(Cn-C)))<1e-9:p,C=pn,Cn;break
  p,C=pn,Cn
 return R,p,C
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
pools={k:load(k) for k in ("051","052","053")}
for other,tgt in [("052","053"),("053","052")]:
 ys,Ls=pools["051"];yo,Lo=pools[other];yt,Lt=pools[tgt];yS=np.r_[ys,yo];LS=np.vstack([Ls,Lo])
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 print("\n",other,"->",tgt,"pbb",np.round(pbb,3))
 for strength in [20,50,100,200,500]:
  for temp in [.25,.5,1.]:
   for up in [False,True]:
    R,p,C=em(yS,LS,Lt,pbb,strength,temp,up);pr=R.argmax(1)
    print("a",strength,"t",temp,"up",up,"p",np.round(p,3),met(yt,pr))
 print("weak PriorG",met(yt,Lt[:,4]),"U2",met(yt,Lt[:,1]))
