from pathlib import Path
import sys,csv,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/055_zero_label_policy_adaptation"))
import source_cv_labelmodel055 as s
ap=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
TRANS=[(a,b) for a in range(3) for b in range(3) if a!=b]
def stats(y,p):
 m=s.met(y,p);return m["PA"],m["MCC"],m["falseS"],*m["rec"]
for target,other in [("052","053"),("053","052")]:
 y1,L1=s.pools["051"];yo,Lo=s.pools[other];yt,Lt=s.pools[target];ys=np.r_[y1,yo];Ls=np.vstack([L1,Lo])
 z=next(r for r in ap if r["target"]==target and r["estimator"]=="BBSE_unlabeled");p=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 base=s.base_counts(ys,Ls);C,pp=s.fitC(base,Lt,p,10,.3,False);lm=s.predict(C,Lt,pp,.3);pg=Lt[:,4]
 pgst=stats(yt,pg);all=[]
 for mask in range(1<<len(TRANS)):
  pr=pg.copy()
  for j,(a,b) in enumerate(TRANS):
   if mask&(1<<j):pr[(pg==a)&(lm==b)]=b
  st=stats(yt,pr);all.append((st,mask,pr))
 print("\nTARGET",target,"PG",tuple(round(float(x),4) for x in pgst),"LM",tuple(round(float(x),4) for x in stats(yt,lm)))
 good=[x for x in all if x[0][0]>=pgst[0] and x[0][1]>=pgst[1] and x[0][2]<=pgst[2] and x[0][3]>=pgst[3] and x[0][4]>=pgst[4] and x[0][5]>=pgst[5]]
 print("strict dominate count",len(good))
 ranked=sorted(all,key=lambda x:(x[0][1],x[0][0],-x[0][2],min(x[0][3:])),reverse=True)[:12]
 for st,mask,_ in ranked:
  acc=[TRANS[j] for j in range(len(TRANS)) if mask&(1<<j)]
  print(tuple(round(float(x),4) for x in st),"accept",acc)
