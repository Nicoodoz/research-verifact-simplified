import csv,json,numpy as np
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
LAB=["Supported","Not Supported","Not Addressed"]; li={x:i for i,x in enumerate(LAB)}
P=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
P=[r for r in P if r["TS_status"]=="valid"]
Q={json.loads(x)["id"]:json.loads(x) for x in (ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
def mcc(y,p):
 M=np.zeros((3,3),float);np.add.at(M,(y,p),1);s=M.sum();c=np.trace(M);a=M.sum(1);b=M.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5
 return (c*s-a@b)/d if d else 0
def met(pred):
 y=np.array([li[r["GT"]] for r in P]);p=np.array([li[x] for x in pred]);M=np.zeros((3,3),int);np.add.at(M,(y,p),1)
 rec=[M[k,k]/M[k].sum() for k in range(3)];fs=int(((y!=0)&(p==0)).sum()); nons=int((y!=0).sum())
 return dict(n=len(y),correct=int((y==p).sum()),PA=float((y==p).mean()),MCC=float(mcc(y,p)),falseS=fs,falseS_rate=fs/nons,S=rec[0],NS=rec[1],NA=rec[2])
preds={}
preds["U2"]=[r["U2"] for r in P]
preds["GateA"]=[r["GateA"] for r in P]
preds["FrozenPriorG"]=[r["TS_PriorG"] for r in P]
r90=[]
for r in P:
 b=r["TS_PriorG"]; q=Q[r["id"]]["qwen_scores"]; qlab=max(LAB,key=lambda k:q[k])
 if b!="Supported" and qlab=="Supported" and q["Supported"]>=90:b="Supported"
 r90.append(b)
preds["064_R90"]=r90
for k,v in preds.items():print(k,met(v))
# active10 future-v2 absolute mean on forward target053
R=list(csv.DictReader(open(ROOT/"outputs/064_safe_policy_selection/future_v2_replicate_results.csv",encoding="utf-8-sig")))
X=[r for r in R if r["source"]=="052" and r["target"]=="053" and r["strategy"]=="active_policy" and r["budget"]=="10"]
for pref in ("policy","base"):
 vals={k:np.mean([float(r[f"{pref}_{k}"]) for r in X]) for k in ("PA","MCC","falseS_rate","S","NS","NA")}
 print("future10_"+pref,vals)
