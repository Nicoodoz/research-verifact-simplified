"""Fit 022-equivalent G/M objectives on 051 patients only with closed-form 1D/2D Newton."""
from pathlib import Path
from collections import Counter
import sys,math,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import run051,common051 as c51

def z_from_scores(scores):
    return np.log(np.maximum(np.asarray([[s[k]/100 for k in c.LABELS] for s in scores],float),1e-6))

def obj_grad_hess(theta,z,y,kind):
    t0=float(theta[0]);t1=float(theta[1]) if kind=="M" else 0.0
    loss=g0=g1=h00=h11=h01=0.0;n=len(y)
    for i in range(n):
        v=[float(z[i,0])+t0,float(z[i,1])+t1,float(z[i,2])]
        m=max(v);e=[math.exp(q-m) for q in v];den=sum(e);p=[q/den for q in e]
        loss+=math.log(den)+m-v[int(y[i])]
        y0=1.0 if int(y[i])==0 else 0.0;y1=1.0 if int(y[i])==1 else 0.0
        g0+=p[0]-y0;h00+=p[0]*(1-p[0])
        if kind=="M":
            g1+=p[1]-y1;h11+=p[1]*(1-p[1]);h01+=-p[0]*p[1]
    loss/=n;g0/=n;h00/=n
    if kind=="G":
        loss+=.01*t0*t0;g0+=.02*t0;h00+=.02
        return loss,np.array([g0]),np.array([[h00]])
    loss+=(.005*t0*t0+.005*t1*t1);g0+=.01*t0;g1=g1/n+.01*t1
    h00+=.01;h11=h11/n+.01;h01/=n
    return loss,np.array([g0,g1]),np.array([[h00,h01],[h01,h11]])

def fit(z,y,kind):
    theta=np.zeros(1 if kind=="G" else 2);history=[]
    for it in range(100):
        loss,g,h=obj_grad_hess(theta,z,y,kind);history.append(loss)
        if max(abs(float(q)) for q in g)<1e-10:break
        if kind=="G":step=np.array([g[0]/h[0,0]])
        else:
            a,b,d=float(h[0,0]),float(h[0,1]),float(h[1,1]);det=a*d-b*b
            c.require(det>0,"nonpositive Hessian")
            step=np.array([(d*g[0]-b*g[1])/det,(-b*g[0]+a*g[1])/det])
        alpha=1.0
        while alpha>1e-10:
            cand=np.clip(theta-alpha*step,-6,6);nl,_,_=obj_grad_hess(cand,z,y,kind)
            if nl<loss:theta=cand;break
            alpha*=.5
        else:break
    loss,g,h=obj_grad_hess(theta,z,y,kind)
    return dict(theta=theta.tolist(),objective=loss,gradient_max=max(abs(float(q)) for q in g),
      iterations=len(history),success=max(abs(float(q)) for q in g)<1e-7,
      message="closed_form_newton_1d2d",boundary_hit=[i for i,v in enumerate(theta) if min(v+6,6-v)<1e-7],
      objective_monotone=all(history[i+1]<=history[i]+1e-12 for i in range(len(history)-1)))

def finite_diff(z,y,kind):
    theta=np.full(1 if kind=="G" else 2,.17);_,g,_=obj_grad_hess(theta,z,y,kind);eps=1e-6;num=[]
    for i in range(len(theta)):
        a=theta.copy();b=theta.copy();a[i]+=eps;b[i]-=eps
        la,_,_=obj_grad_hess(a,z,y,kind);lb,_,_=obj_grad_hess(b,z,y,kind);num.append((la-lb)/(2*eps))
    return max(abs(float(a-b)) for a,b in zip(g,num))

def main():
    eval_patients=set(c.read(c.OUT/"sample_freeze.json")["evaluation_patients"])
    cases=[(x,"screen") for x in c51.lines(c51.OUT/"screen_cases.jsonl")]+[(x,"confirmation") for x in c51.lines(c51.OUT/"confirmation_cases_frozen.jsonl")]
    train_patients={x["sid"] for x,_ in cases}
    c.require(len(train_patients)==16 and train_patients.isdisjoint(eval_patients),"calibration patient leakage")
    _,term=run051.state();models={};training={};checks={}
    for cond in ("N-S","T-S"):
        rows=[]
        for x,stage in cases:
            h=c51.stable("",x["id"])[:24]
            rid=("051_"+cond.replace("-","_")+"_"+h) if stage=="screen" else ("051_conf_"+cond.replace("-","_")+"_"+h)
            p=term[rid]["parsed"]
            if p.get("status") not in c51.VALID or p.get("scores") is None:continue
            rows.append(dict(id=x["id"],sid=x["sid"],GT=x["GT"],scores=p["scores"]))
        z=z_from_scores([r["scores"] for r in rows]);y=np.array([c.LABELS.index(r["GT"]) for r in rows],int)
        models[cond]={};checks[cond]={}
        for kind in ("G","M"):
            fd=finite_diff(z,y,kind);m=fit(z,y,kind)
            c.require(fd<1e-6 and m["success"] and m["objective_monotone"],"calibration check "+cond+kind)
            models[cond][kind]=m;checks[cond][kind]=dict(finite_difference_max_abs=fd)
        training[cond]=dict(n=len(rows),patients=sorted({r["sid"] for r in rows}),GT_counts=dict(Counter(r["GT"] for r in rows)),ids=[r["id"] for r in rows])
    c.put(c.OUT/"calibration_models.json",dict(created_utc=c.now(),
      objective_recipe="022 G/M parameterization, NLL, L2, bounds; closed-form Newton implementation amendment001",
      source_task="051",evaluation_patients=sorted(eval_patients),models=models,training=training,checks=checks,
      source_sha256={"051_screen":c.sha(c51.OUT/"screen_cases.jsonl"),"051_confirmation":c.sha(c51.OUT/"confirmation_cases_frozen.jsonl"),
                     "amendment":c.sha(c.OUT/"implementation_amendment_001.json")}))
    print("052 CALIBRATION",models,flush=True)
if __name__=="__main__":main()
