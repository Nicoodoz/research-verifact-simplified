from pathlib import Path
import sys,csv,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/055_zero_label_policy_adaptation"))
import source_cv_labelmodel055 as s
ap=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
TRANS=[(a,b) for a in range(3) for b in range(3) if a!=b]
goods={}
for target,other in [("052","053"),("053","052")]:
 y1,L1=s.pools["051"];yo,Lo=s.pools[other];yt,Lt=s.pools[target];ys=np.r_[y1,yo];Ls=np.vstack([L1,Lo])
 z=next(r for r in ap if r["target"]==target and r["estimator"]=="BBSE_unlabeled");p=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 base=s.base_counts(ys,Ls);C,pp=s.fitC(base,Lt,p,10,.3,False);lm=s.predict(C,Lt,pp,.3);pg=Lt[:,4];b=s.met(yt,pg)
 good=[]
 for mask in range(64):
  pr=pg.copy()
  for j,(a,bb) in enumerate(TRANS):
   if mask&(1<<j):pr[(pg==a)&(lm==bb)]=bb
  m=s.met(yt,pr)
  if m["PA"]+1e-12>=b["PA"] and m["MCC"]+1e-12>=b["MCC"] and m["falseS"]<=b["falseS"]+1e-12 and np.all(m["rec"]+1e-12>=b["rec"]):
   good.append((mask,m))
 goods[target]=good
 print("TARGET",target,"base",b,"good",len(good))
 for mask,m in good:
  print(mask,[TRANS[j] for j in range(6) if mask&(1<<j)],m)
common=set(x[0] for x in goods["052"])&set(x[0] for x in goods["053"])
print("COMMON",sorted(common))
for mask in sorted(common):print(mask,[TRANS[j] for j in range(6) if mask&(1<<j)])
