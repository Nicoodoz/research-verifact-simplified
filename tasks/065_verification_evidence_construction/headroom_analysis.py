import csv, json, numpy as np
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
LAB=["Supported","Not Supported","Not Addressed"]
li={x:i for i,x in enumerate(LAB)}
P=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
def mcc(y,p):
 M=np.zeros((3,3),float);np.add.at(M,(y,p),1)
 s=M.sum();c=np.trace(M);a=M.sum(1);b=M.sum(0);d=((s*s-a@a)*(s*s-b@b))**.5
 return (c*s-a@b)/d if d else 0
y=np.array([li[r["GT"]] for r in P]); p=np.array([li[r["TS_PriorG"]] for r in P])
M=np.zeros((3,3),int);np.add.at(M,(y,p),1)
print("053 TS_PriorG confusion rowsGT colsPred S,NS,NA")
print(M)
print("correct",int((y==p).sum()),"errors",int((y!=p).sum()),"MCC",mcc(y,p))
print("errors_by_gt",[(LAB[k],int(((y==k)&(p!=k)).sum())) for k in range(3)])
print("errors_pred",[(LAB[k],int(((p==k)&(y!=k)).sum())) for k in range(3)])
# hypothetical oracle correction of subsets: correct k S-errors first, then nonS errors.
def metric(pp):
 M=np.zeros((3,3),int);np.add.at(M,(y,pp),1)
 rec=[M[k,k]/M[k].sum() for k in range(3)]
 fs=int(((y!=0)&(pp==0)).sum())
 return ((pp==y).mean(),mcc(y,pp),fs,*rec)
err=np.where(y!=p)[0]
# random-free scenario: exact k errors corrected, prioritized S FNs (preprocessing likely) then all others
order=list(np.where((y==0)&(p!=0))[0])+list(np.where((y!=0)&(p==0))[0])+list(np.where((y!=0)&(p!=0)&(p!=0))[0])
for k in [3,5,8,10,12,15,20,25,30,39]:
 pp=p.copy()
 for i in order[:min(k,len(order))]:pp[i]=y[i]
 print("fix",k,metric(pp))
