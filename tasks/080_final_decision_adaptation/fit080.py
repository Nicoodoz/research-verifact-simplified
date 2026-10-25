"""Low-capacity final-output optimization; recipes selected using calibration patients only."""
import itertools,math
from collections import Counter
import numpy as np
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
import common080 as c
from verifact_research.evaluation.metrics import metrics_from_confusions

RECIPES=['BASE','WNLL1','WNLL2','WMCC1','WMCC2']
BOUND=math.log(4)
GRID=[-math.log(4),-math.log(2),0.,math.log(2),math.log(4)]

def counts(rows):return {k:sum(x['GT']==k for x in rows) for k in c.LABELS}
def probs(n):return np.array([n[k]/sum(n.values()) for k in c.LABELS])
def labels(z):
    # Match historical NS > NA > S tie priority exactly.
    order=np.array([1,2,0]);return order[np.argmax(z[:,order],axis=1)]
def scores(rows,arm):return np.log(np.maximum(np.array([[x[arm][k]/100 for k in c.LABELS] for x in rows]),1e-6))
def objective(theta,z,y,w):
    d=len(theta);v=z.copy();v[:,:d]+=theta
    top=v.max(axis=1);e=np.exp(v-top[:,None]);p=e/e.sum(axis=1)[:,None]
    loss=np.dot(w,np.log(e.sum(axis=1))+top-v[np.arange(len(y)),y])+.01*np.mean(theta**2)
    one=np.eye(3)[y];grad=((p-one)*w[:,None]).sum(axis=0)[:d]+.02/d*theta
    return float(loss),grad
def stats(y,pred,ref):
    n=np.bincount(y,minlength=3);assert np.all(n>0)
    weight=probs(ref)[y]/n[y]
    cm=np.zeros((3,3));np.add.at(cm,(y,pred),weight)
    assert np.allclose(cm.sum(axis=1),probs(ref))
    pa,ac1,mcc=metrics_from_confusions(cm)
    den=cm.sum(axis=0)+cm.sum(axis=1)
    mf=float(np.mean(np.divide(2*np.diag(cm),den,out=np.zeros(3),where=den>0)))
    return dict(MCC=float(mcc),PA=float(pa),AC1=float(ac1),macro_F1=mf,falseS_mass=float(cm[1:,0].sum()),confusion=cm.tolist())

def fit(rows,arm,recipe,ref):
    ct=counts(rows);assert all(ct.values())
    anchor=np.log(probs(ref)/probs(ct));z=scores(rows,arm)+anchor
    y=np.array([c.LABELS.index(x['GT']) for x in rows]);w=probs(ref)[y]/np.bincount(y,minlength=3)[y]
    assert abs(w.sum()-1)<1e-12
    delta=np.zeros(2);details={}
    if recipe.startswith('WNLL'):
        d=int(recipe[-1]);x=np.full(d,.17);eps=1e-6
        val,g=objective(x,z,y,w);num=[]
        for i in range(d):
            step=np.zeros(d);step[i]=eps
            num.append((objective(x+step,z,y,w)[0]-objective(x-step,z,y,w)[0])/(2*eps))
        fd=float(np.max(np.abs(np.array(num)-g)));assert fd<1e-6
        res=minimize(lambda t:objective(t,z,y,w),np.zeros(d),method='L-BFGS-B',jac=True,
                     bounds=[(-BOUND,BOUND)]*d,options=dict(ftol=1e-14,gtol=1e-10,maxiter=200))
        assert res.success,res.message
        grad=res.jac.copy()
        for i,t in enumerate(res.x):
            if t<=-BOUND+1e-8:grad[i]=min(grad[i],0)
            if t>=BOUND-1e-8:grad[i]=max(grad[i],0)
        assert np.max(np.abs(grad))<1e-6,(recipe,res.x,res.jac)
        base=objective(np.zeros(d),z,y,w)[0];assert res.fun<=base+1e-10
        delta[:d]=res.x
        details=dict(objective=float(res.fun),base_objective=base,finite_difference_error=fd,projected_gradient=float(np.max(np.abs(grad))),
                     boundary_hit=[i for i,t in enumerate(res.x) if abs(abs(t)-BOUND)<1e-8])
    elif recipe.startswith('WMCC'):
        d=int(recipe[-1]);ranked=[]
        for idx,values in enumerate(itertools.product(GRID,repeat=d)):
            dv=np.zeros(3);dv[:d]=values;s=stats(y,labels(z+dv),ref)
            key=(round(s['MCC'],12),round(s['macro_F1'],12),round(s['PA'],12),-round(float(np.dot(dv,dv)),12),-idx)
            ranked.append((key,values,s))
        _,values,s=max(ranked,key=lambda x:x[0]);delta[:d]=values
        details=dict(training_objective=s,grid_cells=len(ranked),boundary_hit=[i for i,t in enumerate(values) if abs(abs(t)-BOUND)<1e-8])
    else:assert recipe=='BASE'
    return dict(recipe=recipe,arm=arm,delta=delta.tolist(),anchor_log_offsets=anchor.tolist(),reference_counts=ref,calibration_counts=ct,
                training_ids=[x['id'] for x in rows],training_patients=sorted({x['sid'] for x in rows}),details=details)

def predict(rows,arm,model):
    delta=np.array(model['delta']+[0.])
    return labels(scores(rows,arm)+np.array(model['anchor_log_offsets'])+delta)

def main():
    fr=c.read(c.OUT/'freeze.json');assert fr['status']=='FROZEN_BEFORE_080_FITTING'
    for p,h in fr['source_sha256'].items():assert c.sha(c.ROOT/p)==h,p
    for p,h in fr['artifact_sha256'].items():assert c.sha(c.OUT/p)==h,p
    rows=c.lines(c.OUT/'calibration.jsonl');prior=c.lines(c.OUT/'reference_prior_rows.jsonl');ref=counts(prior)
    patients=sorted({x['sid'] for x in rows});folds=[];oof=[];full={};selection={};diagnostic={}
    for arm in ['B','F4']:
        preds={method:{} for method in RECIPES}
        for sid in patients:
            tr=[x for x in rows if x['sid']!=sid];va=[x for x in rows if x['sid']==sid]
            priortr=[x for x in prior if x['sid']!=sid];foldref=counts(priortr)
            assert not {x['sid'] for x in va}&{x['sid'] for x in tr+priortr}
            for method in RECIPES:
                m=fit(tr,arm,method,foldref);pred=predict(va,arm,m)
                folds.append(dict(heldout_patient=sid,model=m))
                for x,p in zip(va,pred):
                    assert x['id'] not in preds[method]
                    preds[method][x['id']]=int(p)
                    oof.append(dict(id=x['id'],sid=sid,GT=x['GT'],arm=arm,recipe=method,label=c.LABELS[p]))
        y=np.array([c.LABELS.index(x['GT']) for x in rows]);summaries=[]
        for i,method in enumerate(RECIPES):
            assert len(preds[method])==len(rows)
            ss=stats(y,np.array([preds[method][x['id']] for x in rows]),ref)
            ss.update(recipe=method,parameters=0 if method=='BASE' else int(method[-1]),raw_correct=sum(preds[method][x['id']]==yy for x,yy in zip(rows,y)))
            ss['raw_correct']=int(ss['raw_correct']);summaries.append(ss)
        chosen=max(enumerate(summaries),key=lambda t:(round(t[1]['MCC'],12),round(t[1]['macro_F1'],12),-t[1]['parameters'],-t[0]))[1]['recipe']
        selection[arm]=dict(chosen=chosen,OOF=summaries)
        full[arm]={method:fit(rows,arm,method,ref) for method in RECIPES}
        diagnostic[arm]={method:stats(y,predict(rows,arm,full[arm][method]),ref) for method in RECIPES}
        print(c.canon(dict(arm=arm,selection=selection[arm])),flush=True)
    c.jl(c.OUT/'oof_predictions.jsonl',oof);c.put(c.OUT/'fold_models.json',folds)
    c.put(c.OUT/'selection.json',selection)
    c.put(c.OUT/'models_frozen.json',dict(status='FROZEN_BEFORE_080_EVALUATION',created_utc=c.now(),selection=selection,full_models=full,
        calibration_diagnostics=diagnostic,source_freeze_sha256=c.sha(c.OUT/'freeze.json'),training_code_sha256=c.sha(c.TASK/'fit080.py'),
        fitted_parameter_models=120,NLL_optimizer_fits=60,MCC_grid_selections=60,MCC_training_grid_evaluations=900,
        calibration_only_selection=True,evaluation_GT_used=False))
    print('080 calibration selection and models frozen; no evaluation metrics read')

if __name__=='__main__':
    with threadpool_limits(limits=1):main()
