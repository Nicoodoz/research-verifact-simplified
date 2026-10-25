"""Fixed low-capacity classifiers, nested patient-separated operating threshold."""
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import common025 as c
def matrix(rows,names):return np.asarray([[r['features'][n] for n in names] for r in rows],dtype=float)
def fit(train,names):
    c.require(bool(train),'Empty candidate training set')
    y=np.array([r['human_gt']=='Supported' for r in train],dtype=int);x=matrix(train,names);scaler=StandardScaler().fit(x)
    model=None;constant=(sum(y)+1)/(len(y)+2)
    if len(set(y))==2:
        model=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-8).fit(scaler.transform(x),y);c.require(model.n_iter_[0]<2000,'Nonconvergence')
    def predict(rows):
        if not rows:return np.array([])
        return model.predict_proba(scaler.transform(matrix(rows,names)))[:,1] if model is not None else np.full(len(rows),constant)
    metadata=dict(features=names,training_patients=sorted(set(r['subject_id'] for r in train)),training_ids=[r['proposition_id'] for r in train],n=len(train),R=int(sum(y)),risk=int(len(y)-sum(y)),mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_[0].tolist() if model is not None else [0.]*len(names),intercept=float(model.intercept_[0]) if model is not None else None,constant_fallback=model is None)
    return predict,metadata
def training_threshold(train,names):
    inner=[];subjects=sorted(set(r['subject_id'] for r in train))
    for sid in subjects:
        fitrows=[r for r in train if r['subject_id']!=sid];test=[r for r in train if r['subject_id']==sid]
        c.require(set(r['subject_id'] for r in fitrows).isdisjoint({sid}),'Inner leakage')
        if not fitrows:prob=np.full(len(test),.5)
        else:predict,_=fit(fitrows,names);prob=predict(test)
        inner.extend((r,float(p)) for r,p in zip(test,prob))
    positive=sorted([p for r,p in inner if r['human_gt']=='Supported'],reverse=True)
    threshold=positive[int(np.ceil(.8*len(positive)))-1] if positive else 0.
    return threshold,[dict(held_patient=sid,training_patients=[s for s in subjects if s!=sid]) for sid in subjects]
def oof(trainrows,testrows,names):
    candtrain=[r for r in trainrows if r['candidate']];candtest=[r for r in testrows if r['candidate']]
    output={};audits=[]
    for sid in sorted(set(r['subject_id'] for r in testrows)):
        train=[r for r in candtrain if r['subject_id']!=sid];test=[r for r in candtest if r['subject_id']==sid]
        threshold,inner=training_threshold(train,names);predict,meta=fit(train,names)
        c.require(sid not in meta['training_patients'],'Outer leakage')
        for r,p in zip(test,predict(test)):output[r['proposition_id']]=dict(prob=float(p),threshold=float(threshold),keep=bool(p>=threshold))
        audits.append(dict(held_patient=sid,threshold=float(threshold),inner_folds=inner,**meta))
    return output,audits
def transfer(trainrows,testrows,names):
    c.require(set(r['subject_id'] for r in trainrows).isdisjoint(r['subject_id'] for r in testrows),'Transfer patient leakage')
    train=[r for r in trainrows if r['candidate']];test=[r for r in testrows if r['candidate']]
    threshold,inner=training_threshold(train,names);predict,meta=fit(train,names)
    return {r['proposition_id']:dict(prob=float(p),threshold=float(threshold),keep=bool(p>=threshold)) for r,p in zip(test,predict(test))},[dict(held_patient='external_cohort',threshold=float(threshold),inner_folds=inner,**meta)]
