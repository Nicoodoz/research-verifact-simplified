"""Fixed-capacity estimators and strictly patient-nested threshold fitting."""
import math,warnings
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from xgboost import XGBClassifier
import common029 as c

def matrix(rows,names):return np.asarray([[r['features'][k] for k in names] for r in rows],dtype=float).reshape(len(rows),len(names))
def fit(train,names,estimator,config):
    x=matrix(train,names);y=np.array([r['human_gt']=='Supported' for r in train],dtype=int);scaler=None;model=None
    meta=dict(features=names,estimator=estimator,training_ids=[r['proposition_id'] for r in train],training_patients=sorted({r['subject_id'] for r in train}),n=len(train),R=int(y.sum()),fallback=None)
    if len(train) and estimator=='Logistic':scaler=StandardScaler().fit(x);x=scaler.transform(x);meta.update(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist())
    if len(set(y))<2:
        probability=(float(y.sum())+1)/(len(y)+2) if len(y) else config['fallback']['empty_training_probability'];meta.update(fallback='empty' if not len(y) else 'single_class',constant_probability=probability)
    else:
        model=LogisticRegression(**config['logistic']) if estimator=='Logistic' else XGBClassifier(**config['xgboost'])
        with warnings.catch_warnings():warnings.simplefilter('error',ConvergenceWarning);model.fit(x,y)
        if estimator=='Logistic':meta.update(coef=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),n_iter=model.n_iter_.tolist())
        else:meta['booster_json']=model.get_booster().save_raw(raw_format='json').decode('utf-8')
    def predict(test):
        if not test:return np.array([],dtype=float)
        if model is None:return np.full(len(test),probability)
        z=matrix(test,names);z=scaler.transform(z) if scaler is not None else z;p=model.predict_proba(z)[:,1].astype(float);c.require(np.isfinite(p).all(),'Nonfinite model prediction');return p
    return predict,meta

def select_threshold(inner,target=.8):
    positive=sorted((r['probability'] for r in inner if r['is_R']),reverse=True)
    return float(positive[math.ceil(target*len(positive))-1]) if positive else 0.

def fold(train,test,names,estimator,config,excluded_patients):
    train_s={r['subject_id'] for r in train};test_s={r['subject_id'] for r in test};excluded=set(excluded_patients)
    c.require(train_s.isdisjoint(excluded|test_s),'Outer patient leakage')
    inner=[];audits=[]
    for sid in sorted(train_s):
        tr=[r for r in train if r['subject_id']!=sid];te=[r for r in train if r['subject_id']==sid]
        c.require({r['subject_id'] for r in tr}.isdisjoint(excluded|{sid}),'Inner patient leakage')
        predict,meta=fit(tr,names,estimator,config);prob=predict(te)
        audits.append(dict(held_patient=sid,test_ids=[r['proposition_id'] for r in te],**meta))
        inner.extend(dict(proposition_id=r['proposition_id'],subject_id=sid,is_R=r['human_gt']=='Supported',probability=float(p)) for r,p in zip(te,prob))
    c.require({r['proposition_id'] for r in inner}=={r['proposition_id'] for r in train},'Incomplete inner OOF')
    threshold=select_threshold(inner,config['training_rescue_target']);predict,meta=fit(train,names,estimator,config)
    # Test GT is never passed to fitting, scaling, threshold selection, or predict features.
    predictions=[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],probability=float(p),threshold=threshold,keep=bool(p>=threshold)) for r,p in zip(test,predict(test))]
    pos=[r for r in inner if r['is_R']];retention=sum(r['probability']>=threshold for r in pos)/len(pos) if pos else None
    c.require(retention is None or retention>=config['training_rescue_target'],'Training threshold target failed')
    return dict(predictions=predictions,threshold=threshold,training_R_retention=retention,threshold_fallback='no_R_threshold_zero' if not pos else None,excluded_patients=sorted(excluded),test_ids=[r['proposition_id'] for r in test],inner_predictions=inner,inner_folds=audits,final_fit=meta)
