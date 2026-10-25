from pathlib import Path
import importlib.util, json, numpy as np
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"tasks/063_minimal_label_reliability/run063.py"
s=importlib.util.spec_from_file_location("r",P);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
LABS=r.LABS
def rows(tag,gt):
    a=r.load_pool(tag,gt)
    raw=[json.loads(x) for x in (ROOT/f"outputs/055_zero_label_policy_adaptation/features_qwen_{tag}.jsonl").read_text().splitlines() if x.strip()]
    out=[]
    for z,x in zip(a,raw):
        q=np.array([x["qwen_scores"][k] for k in LABS],float)
        y=dict(z);y["q"]=int(np.argmax(q));y["qt"]=float(q.max());y["qs"]=float(q[0]);out.append(y)
    return out
POL=("BASE","V80","V60","R90","C80","C60")
def preds(x):
    b=x["ds"];q=x["q"];qt=x["qt"];qs=x["qs"]
    v80=q if b==0 and q!=0 and qt>=80 else b
    v60=q if b==0 and q!=0 and qt>=60 else b
    r90=0 if b!=0 and q==0 and qs>=90 else b
    c80=q if r90==0 and q!=0 and qt>=80 else r90
    c60=q if r90==0 and q!=0 and qt>=60 else r90
    return (b,v80,v60,r90,c80,c60)
for tag in ("052","053"):
    blind=rows(tag,False)
    sig={}
    for x in blind:sig[preds(x)]=sig.get(preds(x),0)+1
    print("\nBLIND",tag,"signatures",len(sig))
    for k,v in sorted(sig.items(),key=lambda z:-z[1]):print(v,k)
    gt=rows(tag,True);S={}
    for x in gt:
        k=preds(x)
        if k not in S:S[k]=np.zeros(3,int)
        S[k][x["y"]]+=1
    print("SOURCE GT")
    for k,v in sorted(S.items(),key=lambda z:-z[1].sum()):print(v.sum(),k,v.tolist())
