from pathlib import Path
import importlib.util, json, numpy as np
ROOT=Path(__file__).resolve().parents[2]
P063=ROOT/"tasks/063_minimal_label_reliability/run063.py"
spec=importlib.util.spec_from_file_location("r063",P063)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
LABS=r.LABS
P0=np.array([1108.,100.,170.]);P0/=P0.sum()
CAL=np.array([48.,47.,48.]);CAL/=CAL.sum()
G=.1342909508820116
B0=np.log(P0/CAL);B0-=B0[2]
def data(tag,gt):
    rows=r.load_pool(tag,gt)
    raw=[json.loads(x) for x in
         (ROOT/f"outputs/055_zero_label_policy_adaptation/features_qwen_{tag}.jsonl").read_text().splitlines()
         if x.strip()]
    out=[]
    for a,x in zip(rows,raw):
        ts=np.log(np.maximum(np.array([x["ts_scores"][k]/100 for k in LABS]),1e-6));ts[0]+=G
        q=np.array([x["qwen_scores"][k] for k in LABS],float)
        z=dict(a);z["u2"]=int(np.argmax(ts+np.array([2,0,0])))
        z["q"]=int(np.argmax(q));z["qtop"]=float(q.max());z["qs"]=float(q[0])
        out.append(z)
    return out
def apply(rows,name):
    b=np.array([x["ds"] for x in rows],int);p=b.copy()
    for i,x in enumerate(rows):
        if name=="veto80" and b[i]==0 and x["q"]!=0 and x["qtop"]>=80:p[i]=x["q"]
        elif name=="veto60" and b[i]==0 and x["q"]!=0 and x["qtop"]>=60:p[i]=x["q"]
        elif name=="rescueQ90" and b[i]!=0 and x["q"]==0 and x["qs"]>=90:p[i]=0
        elif name=="rescueQ80" and b[i]!=0 and x["q"]==0 and x["qs"]>=80:p[i]=0
        elif name=="rescueU2" and b[i]!=0 and x["u2"]==0:p[i]=0
        elif name=="u2veto80":
            if b[i]!=0 and x["u2"]==0:p[i]=0
            if p[i]==0 and x["q"]!=0 and x["qtop"]>=80:p[i]=x["q"]
    return p
POL=["veto80","veto60","rescueQ90","rescueQ80","rescueU2","u2veto80"]
for tag in ("052","053"):
    rows=data(tag,False);b=np.array([x["ds"] for x in rows])
    print("\nTARGET_BLIND",tag)
    for z in POL: print(z,"changes",int(np.sum(apply(rows,z)!=b)))
    rows=data(tag,True);b=np.array([x["ds"] for x in rows])
    print("SOURCE_GT",tag,"BASE",r.metrics(rows,b))
    for z in POL:
        m=r.metrics(rows,apply(rows,z))
        print(z,{k:m[k] for k in ("PA","MCC","falseS","S","NS","NA")})
