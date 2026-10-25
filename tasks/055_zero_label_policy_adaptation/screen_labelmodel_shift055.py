from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
SCEN={"high_S":np.array([.9,.05,.05]),"S70":np.array([.7,.15,.15]),"S60":np.array([.6,.2,.2]),"NS_heavy":np.array([.6,.3,.1]),"NA_heavy":np.array([.6,.1,.3])}
N=480;EVAL=240;REPS=200;RNG=np.random.default_rng(202609220551)
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  nt=z(r["ns_scores"]);ts=z(r["ts_scores"],G);L.append([np.argmax(nt),np.argmax(nt+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(nt+B0)]);Y.append(LI[r["GT"]])
 return np.array(Y),np.array(L)
def Cpred(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(3)+1)>0)[0];rho=idx[-1];th=css[rho]/(rho+1);return np.maximum(v-th,0)
def bbse(C,hard):
 q=np.bincount(hard,minlength=3)/len(hard);p=P0.copy();step=1/(np.sum(C*C)+1e-12)
 for _ in range(2000):
  n=project(p-step*C.T@(C@p-q))
  if np.max(abs(n-p))<1e-10:break
  p=n
 p=np.maximum(p,1e-9);return p/p.sum()
def base_counts(y,L):
 C=np.full((L.shape[1],3,3),.5)
 for i in range(len(y)):
  for m in range(L.shape[1]):C[m,y[i],L[i,m]]+=1
 return C/C.sum(2,keepdims=True)
def fitC(base,LA,p,strength,temp):
 C=base.copy()
 for _ in range(150):
  lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(LA),0)
  for m in range(LA.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,LA[:,m]],1e-12))
  lp-=lp.max(1,keepdims=True);R=np.exp(lp);R/=R.sum(1,keepdims=True);N=np.empty_like(C)
  for m in range(LA.shape[1]):
   for y in range(3):
    v=strength*base[m,y].copy()
    for l in range(3):v[l]+=R[LA[:,m]==l,y].sum()
    N[m,y]=v/v.sum()
  if np.max(abs(N-C))<1e-8:C=N;break
  C=N
 return C
def predict(C,L,p,temp):
 lp=np.log(np.maximum(p,1e-12))[None,:].repeat(len(L),0)
 for m in range(L.shape[1]):lp+=temp*np.log(np.maximum(C[m,:,L[:,m]],1e-12))
 return np.argmax(lp,1)
def alloc(p,n):
 x=p*n;b=np.floor(x).astype(int);left=n-b.sum();order=np.argsort(-(x-b),kind="stable")
 for i in order[:left]:b[i]+=1
 return b
def samp(by,p,n):
 c=alloc(p,n);a=[]
 for k,v in enumerate(c):a.extend(RNG.choice(by[k],size=v,replace=True).tolist())
 RNG.shuffle(a);return np.array(a)
def mcc(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(y,p),1);s=C.sum();c=np.trace(C);a=C.sum(1);b=C.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 C=np.zeros((3,3),int);np.add.at(C,(y,p),1);return np.array([(y==p).mean(),mcc(y,p),((y!=0)&(p==0)).sum(),C[0,0]/C[0].sum(),C[1,1]/C[1].sum(),C[2,2]/C[2].sum()])
pools={k:load(k) for k in ("051","052","053")}
for other,tgt in [("052","053"),("053","052")]:
 y1,L1=pools["051"];yo,Lo=pools[other];ys=np.r_[y1,yo];Ls=np.vstack([L1,Lo]);base=base_counts(ys,Ls);Cbb=Cpred(ys,Ls[:,4])
 yt,Lt=pools[tgt];by=[np.where(yt==k)[0] for k in range(3)]
 print("\nTARGET",tgt)
 for sn,ptrue in SCEN.items():
  vals={m:[] for m in ["PG","LM03","LM04","LM05","LM06","LM03_PGS"]}
  perr=[]
  for rep in range(REPS):
   ia=samp(by,ptrue,N);ie=samp(by,ptrue,EVAL);p=bbse(Cbb,Lt[ia,4]);perr.append(abs(p-ptrue).sum())
   vals["PG"].append(met(yt[ie],Lt[ie,4]))
   for nm,temp in [("LM03",.3),("LM04",.4),("LM05",.5),("LM06",.6)]:
    C=fitC(base,Lt[ia],p,20,temp);pr=predict(C,Lt[ie],p,temp);vals[nm].append(met(yt[ie],pr))
    if nm=="LM03":
     pg=Lt[ie,4];pr2=np.where((pr==0)&(pg!=0),pg,pr);vals["LM03_PGS"].append(met(yt[ie],pr2))
  print(sn,"pL1",round(float(np.mean(perr)),3))
  for m,A in vals.items():
   A=np.array(A);print(" ",m,*[round(float(x),3) for x in A.mean(0)])
