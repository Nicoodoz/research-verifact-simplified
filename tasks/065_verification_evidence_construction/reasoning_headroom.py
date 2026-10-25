import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
LAB=["Supported","Not Supported","Not Addressed"]
P=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
Q={json.loads(x)["id"]:json.loads(x) for x in (ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
P=[r for r in P if r["id"] in Q and r["TS_status"]=="valid"]
def qlab(i):
 q=Q[i]["qwen_scores"];return max(LAB,key=lambda k:q[k])
methods={
 "NS_U0":[r["NS_U0"] for r in P],
 "TS_raw":[r["TS_raw"] for r in P],
 "Qwen_U0":[qlab(r["id"]) for r in P],
 "PriorG":[r["TS_PriorG"] for r in P]
}
gt=[r["GT"] for r in P]
print("N",len(P))
for k,v in methods.items():
 ok=sum(a==b for a,b in zip(gt,v));print(k,ok,ok/len(gt))
for names in [("NS_U0","TS_raw"),("NS_U0","Qwen_U0"),("TS_raw","Qwen_U0"),("NS_U0","TS_raw","Qwen_U0"),("PriorG","Qwen_U0"),("PriorG","NS_U0","TS_raw","Qwen_U0")]:
 good=[any(methods[n][i]==gt[i] for n in names) for i in range(len(gt))]
 print("ORACLE",names,sum(good),sum(good)/len(good),"remaining",len(good)-sum(good))

import numpy as np
li={x:i for i,x in enumerate(LAB)}
def metrics(pred):
 y=np.array([li[x] for x in gt]);p=np.array([li[x] for x in pred])
 M=np.zeros((3,3),float);np.add.at(M,(y,p),1);s=M.sum();cc=np.trace(M);a=M.sum(1);b=M.sum(0)
 den=((s*s-a@a)*(s*s-b@b))**.5;m=(cc*s-a@b)/den if den else 0
 rec=[M[k,k]/M[k].sum() for k in range(3)]
 fs=int(((y!=0)&(p==0)).sum())
 return dict(PA=float((y==p).mean()),MCC=float(m),falseS=fs,S=float(rec[0]),NS=float(rec[1]),NA=float(rec[2]))
for names in [("NS_U0","TS_raw","Qwen_U0"),("PriorG","NS_U0","TS_raw","Qwen_U0")]:
 pred=[]
 for i in range(len(gt)):
  if any(methods[n][i]==gt[i] for n in names): pred.append(gt[i])
  else: pred.append(methods["PriorG"][i])
 print("ORACLE_METRICS",names,metrics(pred))

from collections import Counter
names=("PriorG","NS_U0","TS_raw","Qwen_U0")
bad=[i for i in range(len(gt)) if not any(methods[n][i]==gt[i] for n in names)]
print("ALL_WRONG_GT",Counter(gt[i] for i in bad))
print("ALL_WRONG_PRIORG_PRED",Counter(methods["PriorG"][i] for i in bad))
