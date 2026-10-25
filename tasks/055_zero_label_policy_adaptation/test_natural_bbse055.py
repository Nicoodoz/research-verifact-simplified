from pathlib import Path
import json,csv,numpy as np,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
sys.path.insert(0,str(ROOT/"tasks/055_zero_label_policy_adaptation"))
import source_cv_labelmodel055 as s
# Natural-source-only BBSE estimates already computed in 054.
ap=list(csv.DictReader((ROOT/"outputs/054_unlabeled_prior_shift/actual_prior_estimates.csv").open(encoding="utf-8")))
cfgs={"052":(5,.25,False,"raw"),"053":(10,.3,True,"raw")}
for target,other in [("052","053"),("053","052")]:
 y1,L1=s.pools["051"];yo,Lo=s.pools[other];yt,Lt=s.pools[target]
 ys=np.r_[y1,yo];Ls=np.vstack([L1,Lo]);base=s.base_counts(ys,Ls)
 z=next(r for r in ap if r["target"]==target and r["estimator"]=="BBSE_unlabeled")
 p=np.array([float(z["p_Supported"]),float(z["p_Not Supported"]),float(z["p_Not Addressed"])])
 st,t,u,mode=cfgs[target];C,pp=s.fitC(base,Lt,p,st,t,u);pr=s.predict(C,Lt,pp,t)
 if mode=="PGS":pr=np.where((pr==0)&(Lt[:,4]!=0),Lt[:,4],pr)
 print(target,"prior",np.round(p,3),"adapt",s.met(yt,pr),"PG",s.met(yt,Lt[:,4]))
