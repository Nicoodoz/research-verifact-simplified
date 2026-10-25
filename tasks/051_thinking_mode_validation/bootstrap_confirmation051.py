"""Fixed-prediction patient-cluster bootstrap for 051 confirmation."""
from pathlib import Path
import csv,json,random,statistics,sys
import numpy as np
from sklearn.metrics import matthews_corrcoef
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/051_thinking_mode_validation"
LABELS=("Supported","Not Supported","Not Addressed")
def quant(xs,q):return float(np.quantile(np.asarray(xs,float),q))
def metrics(rows,cond):
    rr=[r for r in rows if r["condition"]==cond and r["main"]]
    gt=[r["GT"] for r in rr];pr=[r["main"] for r in rr]
    return dict(PA=sum(a==b for a,b in zip(gt,pr))/len(rr),
      MCC=float(matthews_corrcoef(gt,pr)) if len(set(gt))>1 and len(set(pr))>1 else 0.0,
      false_S=sum(a!="Supported" and b=="Supported" for a,b in zip(gt,pr)),n=len(rr))
def main():
    rows=list(csv.DictReader((OUT/"confirmation_predictions.csv").open(encoding="utf-8")))
    patients=sorted({r["sid"] for r in rows});by={p:[r for r in rows if r["sid"]==p] for p in patients}
    rng=random.Random(51051);draws=[]
    pairs=[("T-V","N-S"),("T-V","N-V")]
    for i in range(1000):
        chosen=[rng.choice(patients) for _ in patients]
        sample=[]
        for k,p in enumerate(chosen):
            for r in by[p]:sample.append(dict(r,_boot=f"{k}:{p}"))
        rec={"draw":i}
        for a,b in pairs:
            ma=metrics(sample,a);mb=metrics(sample,b)
            rec[a+"__"+b+"__dPA"]=ma["PA"]-mb["PA"]
            rec[a+"__"+b+"__dMCC"]=ma["MCC"]-mb["MCC"]
            rec[a+"__"+b+"__dFalseS"]=ma["false_S"]-mb["false_S"]
        draws.append(rec)
    summary={}
    for a,b in pairs:
        key=a+"__"+b
        summary[key]={}
        for metric in ("dPA","dMCC","dFalseS"):
            vals=[r[key+"__"+metric] for r in draws]
            summary[key][metric]=dict(mean=float(np.mean(vals)),lo95=quant(vals,.025),hi95=quant(vals,.975))
    (OUT/"confirmation_bootstrap.json").write_text(json.dumps(dict(seed=51051,draws=1000,patients=patients,summary=summary),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
