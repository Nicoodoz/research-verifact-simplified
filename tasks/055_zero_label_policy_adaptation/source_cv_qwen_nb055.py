from pathlib import Path
import json,csv,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed");LI={k:i for i,k in enumerate(LABS)}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B0=np.log(P0/CAL);B0-=B0[2]
SUBS=[(4,5),(4,6),(1,4,5),(1,4,6),(0,1,4,5),(0,1,4,6),(1,3,4,5),(1,3,4,6),(0,1,2,3,4,5,6)]
ALPHA=(.1,.5,1,2,5,10)
def load(pool):
 rr=[json.loads(s) for s in (OUT/f"features_qwen_{pool}.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()];Y=[];L=[];S=[]
 for r in rr:
  def z(sc,g=0):a=np.log(np.maximum(np.array([sc[k]/100 for k in LABS],float),1e-6));a[0]+=g;return a
  ns=z(r["ns_scores"]);ts=z(r["ts_scores"],G);q=z(r["qwen_scores"])
  L.append([np.argmax(ns),np.argmax(ns+[2,0,0]),np.argmax(ts),np.argmax(ts+[2,0,0]),np.argmax(ts+B0),np.argmax(q),np.argmax(q+[2,0,0])]);Y.append(LI[r["GT"]]);S.append(r["sid"])
 return np.array(Y),np.array(L),np.array(S)
def fit(y,L,idx,a):
 C=np.full((len(idx),3,3),a,float)
 for i,m in enumerate(idx):
  for yy,ll in zip(y,L[:,m]):C[i,yy,ll]+=1
 C/=C.sum(2,keepdims=True);return C
def ll(C,L,idx):
 A=np.zeros((len(L),3))
 for i,m in enumerate(idx):
  for y in range(3):A[:,y]+=np.log(np.maximum(C[i,y,L[:,m]],1e-12))
 return A
def em(A):
 p=P0.copy()
 for _ in range(1000):
  X=A+np.log(np.maximum(p,1e-12))[None,:];X-=X.max(1,keepdims=True);R=np.exp(X);R/=R.sum(1,keepdims=True);n=R.mean(0)
  if np.max(abs(n-p))<1e-10:return n
  p=n
 return p
def pred(C,L,idx):
 A=ll(C,L,idx);p=em(A);return np.argmax(A+np.log(np.maximum(p,1e-12))[None,:],1),p
def mcc(y,p):
 M=np.zeros((3,3),float);np.add.at(M,(y,p),1);s=M.sum();c=np.trace(M);a=M.sum(1);b=M.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5;return (c*s-a@b)/d if d else 0.
def met(y,p):
 M=np.zeros((3,3),int);np.add.at(M,(y,p),1);return dict(PA=float((y==p).mean()),MCC=float(mcc(y,p)),falseS=int(((y!=0)&(p==0)).sum()),rec=np.array([M[k,k]/M[k].sum() for k in range(3)]),correct=int((y==p).sum()))
def cv(data,idx,a):
 y,L,s=data;fold=np.array([int(hashlib.sha256(x.encode()).hexdigest()[:8],16)%5 for x in s]);out=np.full(len(y),-1,int)
 for f in range(5):
  tr=fold!=f;va=fold==f
  if not np.any(va):continue
  C=fit(y[tr],L[tr],idx,a);out[va]=pred(C,L[va],idx)[0]
 return met(y,out)
pools={k:load(k) for k in ("052","053")};rows=[]
for source,target in [("052","053"),("053","052")]:
 y,L,s=pools[source];yt,Lt,_=pools[target];base=met(y,L[:,4]);cands=[]
 for idx in SUBS:
  for a in ALPHA:
   mm=cv(pools[source],idx,a)
   strict=mm["PA"]>=base["PA"]-1e-12 and mm["MCC"]>=base["MCC"]-1e-12 and mm["falseS"]<=base["falseS"] and np.all(mm["rec"]>=base["rec"]-1e-12)
   safe=mm["MCC"]>=base["MCC"]-1e-12 and mm["falseS"]<=base["falseS"] and np.all(mm["rec"]>=base["rec"]-.02)
   key=(int(strict),int(safe),mm["PA"],mm["MCC"],-mm["falseS"],float(np.min(mm["rec"])))
   cands.append((key,idx,a,mm,strict,safe))
 best=max(cands,key=lambda x:x[0]);key,idx,a,cvmm,strict,safe=best
 if strict or safe:
  C=fit(y,L,idx,a);tp,p=pred(C,Lt,idx);used="NB"
 else:
  tp=Lt[:,4];p=P0;used="FrozenPriorG"
 tm=met(yt,tp);pg=met(yt,Lt[:,4])
 print("\n",source,"->",target,"source PG",base,"selected",idx,a,"strict",strict,"safe",safe,"CV",cvmm,"deploy",used,"p",np.round(p,3))
 print("target",tm,"PG",pg)
 rows.append(dict(source=source,target=target,used=used,idx=str(idx),alpha=a,strict=strict,safe=safe,source_cv_PA=cvmm["PA"],source_cv_MCC=cvmm["MCC"],source_cv_falseS=cvmm["falseS"],target_PA=tm["PA"],target_MCC=tm["MCC"],target_falseS=tm["falseS"],target_S=tm["rec"][0],target_NS=tm["rec"][1],target_NA=tm["rec"][2],PG_PA=pg["PA"],PG_MCC=pg["MCC"],PG_falseS=pg["falseS"],PG_S=pg["rec"][0],PG_NS=pg["rec"][1],PG_NA=pg["rec"][2]))
with (OUT/"source_cv_qwen_nb_actual.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
