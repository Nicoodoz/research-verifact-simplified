from pathlib import Path
import csv,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2]
LABS=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LABS)}
P0=np.array([1108,100,170],float);P0/=P0.sum();CAL=np.array([48,47,48],float);CAL/=CAL.sum();G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
actual=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
def load(pool):
 rr=[json.loads(s) for s in (ROOT/f"outputs/055_zero_label_policy_adaptation/features_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
 Z=[];y=[]
 for r in rr:
  sc=r["ts_scores"];z=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));z[0]+=G;Z.append(z);y.append(LI[r["GT"]])
 return np.array(Z),np.array(y)
def cond_cm(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(axis=0,keepdims=True);return C
def expected(C,prior):
 M=C*prior[None,:];pa=float(np.trace(M));falseS=float(M[0,1]+M[0,2]);t=M.sum(0);q=M.sum(1);s=M.sum();cc=np.trace(M)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;mcc=(cc*s-float(np.sum(q*t)))/d if d else 0.
 rec=[C[k,k] for k in range(3)]
 return pa,mcc,falseS,rec
BS=np.arange(.5,3.01,.25);BN=np.arange(-1.5,1.51,.25)
def train_policies(Z,y):
 out=[];pairs=[(float(bs),float(bn)) for bs in BS for bn in BN]+[(float(B0[0]),float(B0[1]))];seen=set()
 for bs,bn in pairs:
  key=(round(bs,12),round(bn,12))
  if key in seen:continue
  seen.add(key);p=np.argmax(Z+np.array([bs,bn,0.])[None,:],axis=1);C=cond_cm(y,p);out.append((bs,bn,C))
 return out
def choose(policies,prior,obj):
 scored=[]
 for bs,bn,C in policies:
  pa,mcc,fs,rec=expected(C,prior)
  if obj=="MCC":key=(mcc,pa,-fs,min(rec))
  else:key=(pa,mcc,-fs,min(rec))
  scored.append((key,bs,bn,pa,mcc,fs,rec))
 return max(scored,key=lambda x:x[0])
def choose_safe(policies,prior):
 base=min(policies,key=lambda x:abs(x[0]-B0[0])+abs(x[1]-B0[1]))
 bpa,bm,bfs,brec=expected(base[2],prior);ok=[]
 for bs,bn,C in policies:
  pa,mcc,fs,rec=expected(C,prior)
  if mcc+1e-12>=bm and fs<=bfs+1e-12 and all(rec[k]+1e-12>=brec[k] for k in range(3)):
   ok.append(((pa,mcc,-fs),bs,bn,pa,mcc,fs,rec))
 return max(ok,key=lambda x:x[0]) if ok else ((bpa,bm,-bfs),base[0],base[1],bpa,bm,bfs,brec)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();cc=np.trace(C);t=C.sum(1);q=C.sum(0)
 d=((s*s-float(np.sum(q*q)))*(s*s-float(np.sum(t*t))))**.5;return (cc*s-float(np.sum(q*t)))/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1)
 return dict(correct=int((y==p).sum()),PA=round(float((y==p).mean()),4),MCC=round(float(mcc(y,p)),4),falseS=int(((y!=0)&(p==0)).sum()),rec=[round(C[k,k]/C[k].sum(),4) for k in range(3)])
Z51,y51=load("051")
print("PriorG base relative bias",B0)
for other,tgt in [("052","053"),("053","052")]:
 Zo,yo=load(other);Zt,yt=load(tgt);Z=np.vstack([Z51,Zo]);y=np.r_[y51,yo];pol=train_policies(Z,y)
 z=next(r for r in actual if r["target"]==tgt and r["estimator"]=="BBSE_unlabeled");pbb=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])]);ptrue=np.bincount(yt,minlength=3)/len(yt)
 print("\ntrain 051+",other,"target",tgt,"pbb",np.round(pbb,3),"true",np.round(ptrue,3))
 for pname,pv in [("BBSE",pbb),("Oracle",ptrue)]:
  for obj in ["MCC","PA"]:
   q=choose(pol,pv,obj);pred=np.argmax(Zt+np.array([q[1],q[2],0])[None,:],axis=1)
   print(pname,obj,"bias",q[1],q[2],"source_expected",round(q[3],3),round(q[4],3),round(q[5],3),[round(x,3) for x in q[6]],"target",met(yt,pred))
  q=choose_safe(pol,pv);pred=np.argmax(Zt+np.array([q[1],q[2],0])[None,:],axis=1)
  print(pname,"SAFE","bias",q[1],q[2],"source_expected",round(q[3],3),round(q[4],3),round(q[5],3),[round(x,3) for x in q[6]],"target",met(yt,pred))
 pred0=np.argmax(Zt+B0[None,:],axis=1);print("FrozenPriorG",met(yt,pred0))
