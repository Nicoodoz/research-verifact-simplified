import csv,numpy as np
from pathlib import Path
P=Path(r"D:\Research-VeriFact\outputs\065_verification_evidence_construction\results.csv")
R=list(csv.DictReader(open(P,encoding="utf-8-sig")))
R=[r for r in R if r["A_valid"]=="True" and r["B_valid"]=="True" and r["C_valid"]=="True"]
LAB=["Supported","Not Supported","Not Addressed"];li={x:i for i,x in enumerate(LAB)}
def met(pred):
 y=np.array([li[r["GT"]] for r in R]);p=np.array([li[x] for x in pred]);M=np.zeros((3,3),float);np.add.at(M,(y,p),1)
 s=M.sum();cc=np.trace(M);a=M.sum(1);b=M.sum(0);den=((s*s-a@a)*(s*s-b@b))**.5
 return dict(PA=float((y==p).mean()),MCC=float((cc*s-a@b)/den if den else 0),correct=int((y==p).sum()))
for arms in [("A","B"),("A","C"),("A","B","C")]:
 p=[]
 for r in R:
  if any(r[a]==r["GT"] for a in arms):p.append(r["GT"])
  else:p.append(r["A"])
 print(arms,met(p),"oracle_correctable",sum(any(r[a]==r["GT"] for a in arms) for r in R))
