from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
BS=np.arange(.5,3.01,.25);BN=np.arange(-1.5,1.51,.25)
SCEN={"high_S":np.array([.9,.05,.05]),"S70":np.array([.7,.15,.15]),"S60":np.array([.6,.2,.2]),"NS_heavy":np.array([.6,.3,.1]),"NA_heavy":np.array([.6,.1,.3])}
N=480;EVAL=240;REPS=200;NULL=1000;RNG=np.random.default_rng(202609220556)
def load(name):
 rr=[json.loads(s) for s in (OUT/f"features_{name}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Z=[];y=[]
 for r in rr:
  sc=r["ts_scores"];z=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));z[0]+=G;Z.append(z);y.append(LI[r["GT"]])
 return np.array(Z),np.array(y)
def cm(y,p):
 C=np.zeros((3,3),float);np.add.at(C,(p,y),1);C/=C.sum(0,keepdims=True);return C
def expm(C,p):
 M=C*p[None,:];pa=float(np.trace(M));fs=float(M[0,1]+M[0,2]);s=M.sum();a=M.sum(0);b=M.sum(1);cc=np.trace(M);d=((s*s-a@a)*(s*s-b@b))**.5;m=(cc*s-a@b)/d if d else 0.;rec=np.array([C[k,k] for k in range(3)])
 return pa,float(m),fs,rec
def policies(Z,y):
 out=[]
 for bs in BS:
  for bn in BN:
   out.append((float(bs),float(bn),cm(y,np.argmax(Z+np.array([bs,bn,0.])[None,:],1))))
 out.append((float(B0[0]),float(B0[1]),cm(y,np.argmax(Z+B0[None,:],1))))
 return out
def choose(dom,p,obj,guard):
 bases=[expm(min(D,key=lambda x:abs(x[0]-B0[0])+abs(x[1]-B0[1]))[2],p) for D in dom];best=None
 for j in range(len(dom[0])):
  bs,bn=dom[0][j][:2];st=[expm(D[j][2],p) for D in dom]
  if guard:
   good=True
   for d in range(len(st)):
    # preserve source-domain MCC/false-S and each recall within 5 points; PA may lose <=1 point.
    if st[d][1]+1e-12<bases[d][1] or st[d][2]>bases[d][2]+1e-12 or st[d][0]+.01<bases[d][0] or np.any(st[d][3]+.05<bases[d][3]):good=False
   if not good:continue
  minpa=min(x[0] for x in st);minm=min(x[1] for x in st);maxfs=max(x[2] for x in st);minrec=min(float(np.min(x[3])) for x in st)
  key=(minm,minpa,-maxfs,minrec) if obj=="MCC" else (minpa,minm,-maxfs,minrec)
  if best is None or key>best[0]:best=(key,bs,bn,st)
 return best if best is not None else (None,float(B0[0]),float(B0[1]),bases)
def project(v):
 u=np.sort(v)[::-1];css=np.cumsum(u)-1;idx=np.where(u-css/(np.arange(3)+1)>0)[0];rho=idx[-1];th=css[rho]/(rho+1);return np.maximum(v-th,0)
def bbse(C,hard):
 q=np.bincount(hard,minlength=3)/len(hard);p=P0.copy();step=1/(np.sum(C*C)+1e-12)
 for _ in range(3000):
  n=project(p-step*C.T@(C@p-q))
  if np.max(abs(n-p))<1e-11:break
  p=n
 p=np.maximum(p,1e-9);return p/p.sum()
def alloc(p,n):
 x=p*n;b=np.floor(x).astype(int);left=n-b.sum();o=np.argsort(-(x-b),kind="stable")
 for i in o[:left]:b[i]+=1
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
 Zo,yo=pools[other];Z1,y1=pools["051"];Zt,yt=pools[tgt];dom=[policies(Z1,y1),policies(Zo,yo)]
 # BBSE and shift threshold come from nearest natural source only.
 Co=cm(yo,np.argmax(Zo+B0[None,:],1));byo=[np.where(yo==k)[0] for k in range(3)];null=[]
 for _ in range(NULL):
  ix=samp(byo,P0,N);null.append(np.sum(abs(bbse(Co,np.argmax(Zo[ix]+B0[None,:],1))-P0)))
 tau=float(np.quantile(null,.95));byt=[np.where(yt==k)[0] for k in range(3)]
 print("\nTARGET",tgt,"source",other,"tau",round(tau,3))
 for sn,pt in SCEN.items():
  vals={m:[] for m in ["PG","RPA","RMCC","GRPA","GRMCC"]};tr=0;perr=[]
  for _ in range(REPS):
   ia=samp(byt,pt,N);ie=samp(byt,pt,EVAL);p=bbse(Co,np.argmax(Zt[ia]+B0[None,:],1));perr.append(np.sum(abs(p-pt)));active=np.sum(abs(p-P0))>tau;tr+=active
   ye=yt[ie];ze=Zt[ie];vals["PG"].append(met(ye,np.argmax(ze+B0[None,:],1)))
   for nm,obj,guard in [("RPA","PA",False),("RMCC","MCC",False),("GRPA","PA",True),("GRMCC","MCC",True)]:
    if active:q=choose(dom,p,obj,guard);bs,bn=q[1],q[2]
    else:bs,bn=B0[0],B0[1]
    vals[nm].append(met(ye,np.argmax(ze+np.array([bs,bn,0.])[None,:],1)))
  print(sn,"trigger",round(tr/REPS,3),"pL1",round(float(np.mean(perr)),3))
  for nm,A in vals.items():A=np.array(A);print(" ",nm,*[round(float(x),3) for x in A.mean(0)])
