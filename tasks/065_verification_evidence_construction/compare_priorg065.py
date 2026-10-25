from pathlib import Path
import sys,json,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as c
import run065
LABELS=("Supported","Not Supported","Not Addressed")
P0=np.array([1108.,100.,170.]);P0/=P0.sum()
CAL=np.array([48.,47.,48.]);CAL/=CAL.sum()
G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
def pg(scores):
    a=np.log(np.maximum(np.array([float(scores[k])/100 for k in LABELS]),1e-6))
    a[0]+=G
    return LABELS[int(np.argmax(a+B0))]
def mcc(y,p):
    M=np.zeros((3,3),float);li={x:i for i,x in enumerate(LABELS)}
    for a,b in zip(y,p):M[li[a],li[b]]+=1
    s=M.sum();cc=np.trace(M);aa=M.sum(1);bb=M.sum(0)
    den=((s*s-aa@aa)*(s*s-bb@bb))**.5
    return float((cc*s-aa@bb)/den) if den else 0.
def met(rows,key):
    y=[r["GT"] for r in rows];p=[r[key] for r in rows]
    fs=sum(a!="Supported" and b=="Supported" for a,b in zip(y,p))
    nons=sum(a!="Supported" for a in y)
    out=dict(n=len(y),correct=sum(a==b for a,b in zip(y,p)),PA=sum(a==b for a,b in zip(y,p))/len(y),MCC=mcc(y,p),falseS=fs,falseS_rate=fs/nons)
    for lab,short in zip(LABELS,("S","NS","NA")):
        den=sum(a==lab for a in y)
        out[short]=sum(a==lab and b==lab for a,b in zip(y,p))/den if den else None
    return out
blind={x["id"]:x for x in c.lines(c.OUT/"screen_cases_blind.jsonl")}
src={x["id"]:x for x in c.lines(c.R044/"planning_001/eval_cases.jsonl")}
mapping={(x["id"],x["condition"]):x for x in c.lines(c.OUT/"final_mapping.jsonl")}
attempts,term=run065.state()
rows=[]
for pid,x in blind.items():
    h=c.stable("",pid)[:24]
    rr={"id":pid,"GT":src[pid]["GT"],"sid":x["sid"],"type":x["type"],"author":x["author"]}
    ok=True
    for arm in ("A","B","C"):
        rid="065_A_"+h if arm=="A" else mapping[(pid,arm)].get("judge_request_id")
        if not rid or rid not in term:ok=False;break
        q=term[rid]["parsed"]
        good=q.get("status") in ("valid","valid_with_format_anomaly") and q.get("verdict") in LABELS and q.get("scores")
        if not good:ok=False;break
        rr[arm]=q["verdict"];rr[arm+"_PG"]=pg(q["scores"])
    if ok:rows.append(rr)
print("common",len(rows))
for arm in ("A","B","C"):
    print(arm+"_raw",json.dumps(met(rows,arm),ensure_ascii=False))
    print(arm+"_PG",json.dumps(met(rows,arm+"_PG"),ensure_ascii=False))
for arm in ("A","B","C"):
    base=met(rows,arm);new=met(rows,arm+"_PG")
    print("delta",arm,{k:round(new[k]-base[k],6) for k in ("PA","MCC","falseS_rate","S","NS","NA")})
