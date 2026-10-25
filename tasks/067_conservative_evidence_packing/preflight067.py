import json,csv,re,numpy as np
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
LAB=["Supported","Not Supported","Not Addressed"];LI={x:i for i,x in enumerate(LAB)}
F=[json.loads(x) for x in (ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
C={x["id"]:x for x in (json.loads(l) for l in open(ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl",encoding="utf-8-sig") if l.strip())}
P0=np.array([1108.,100.,170.]);P0/=P0.sum();CAL=np.array([48.,47.,48.]);CAL/=CAL.sum();G=.1342909508820116;B=np.log(P0/CAL);B-=B[2]
def pg(s):
 a=np.log(np.maximum(np.array([float(s[k])/100 for k in LAB]),1e-6));a[0]+=G
 return LAB[int(np.argmax(a+B))]
def mcc(y,p):
 M=np.zeros((3,3),float);np.add.at(M,(y,p),1);s=M.sum();cc=np.trace(M);aa=M.sum(1);bb=M.sum(0);den=((s*s-aa@aa)*(s*s-bb@bb))**.5
 return (cc*s-aa@bb)/den if den else 0
y=np.array([LI[x["GT"]] for x in F]);p=np.array([LI[pg(x["ts_scores"])] for x in F])
M=np.zeros((3,3),int);np.add.at(M,(y,p),1)
print("N",len(F),"patients",len(set(x["sid"] for x in F)),"missing cases",sum(x["id"] not in C for x in F))
print("correct",int((y==p).sum()),"PA",float((y==p).mean()),"MCC",mcc(y,p),"falseS",int(((y!=0)&(p==0)).sum()))
print(M)
