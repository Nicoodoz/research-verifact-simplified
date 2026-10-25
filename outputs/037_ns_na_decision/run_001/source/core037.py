"""037: development-only, support-preserving decision repair. No API clients."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
import csv
import hashlib
import json
import socket
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy.special import expit, logsumexp
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/037_ns_na_decision'
sys.path.insert(0, str(ROOT / 'tasks/022_competition_aware_support_calibration'))
sys.path.insert(0, str(ROOT / 'tasks/035_lambda_boundary_calibration'))
sys.path.insert(0, str(ROOT / 'src'))
import calibration022 as cal
import common as old
from verifact_research.evaluation import evaluate, paired_compare
from verifact_research.evaluation.metrics import metrics_from_confusions

LABELS = ('Supported', 'Not Supported', 'Not Addressed')
METHODS = ('U0', 'U2', 'Std_M', 'Std_V', 'VM_switch', 'Ratio_restore', 'Logistic_restore')
REPAIRS = ('VM_switch', 'Ratio_restore', 'Logistic_restore')
FEATURES = ('raw_NS_minus_NA', 'raw_S_margin', 'V_NS_minus_NA', 'V_NA_M_NS')
PRIMARY_PAIRS = (('Ratio_restore', 'VM_switch'), ('Logistic_restore', 'Ratio_restore'))
READS = set()
def deny(*args, **kwargs):
    raise RuntimeError('037 is strictly offline')
socket.create_connection = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny
def audit_open(event, args):
    if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    p = Path(os.fsdecode(args[0])).resolve()
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        return
    mode = args[1]
    if isinstance(mode, str) and not any(ch in mode for ch in 'wax+'):
        if rel.startswith('outputs/036_final_validation/') and not rel.startswith('outputs/036_final_validation/development_001/'):
            raise RuntimeError('037 forbids reserved/036 result reads: ' + rel)
        if 'withdrawn_reserved' in rel or rel.startswith('data/'):
            raise RuntimeError('037 forbids raw/withdrawn data reads: ' + rel)
        READS.add(rel)
sys.addaudithook(audit_open)

def now():
    return datetime.now(timezone.utc).isoformat()
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readj(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
def writecsv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError('Empty CSV: ' + str(path))
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
def arrays(rows):
    return old.arrays(rows)
def describe(rows):
    return dict(patients=sorted({r['sid'] for r in rows}), ids=[r['id'] for r in rows], n=len(rows))
def split_meta(train, test):
    a, b = describe(train), describe(test)
    assert set(a['patients']).isdisjoint(b['patients']), 'Patient overlap'
    assert set(a['ids']).isdisjoint(b['ids']), 'Claim overlap'
    return dict(train=a, held=b)
def logp(v):
    return v - logsumexp(v, axis=1, keepdims=True)
def cm(y, p):
    return np.bincount(3*np.asarray(y,int)+np.asarray(p,int), minlength=9).reshape(3,3)
def brief(y, p):
    mat = cm(y,p)
    pa, ac1, mcc = metrics_from_confusions(mat)
    return dict(correct=int(np.trace(mat)), PA=float(pa), MCC=float(mcc), AC1=float(ac1),
                NS_tp=int(mat[1,1]), NA_tp=int(mat[2,2]), false_S=int(mat[1:,0].sum()))
def probability_point(y, lp):
    q = np.exp(lp)
    return dict(NLL=float(-lp[np.arange(len(y)),y].mean()),
                Brier=float(np.square(q-np.eye(3)[y]).sum(1).mean()))
def features(z, v, pv, pm):
    return np.column_stack((z[:,1]-z[:,2], z[:,0]-np.max(z[:,1:],axis=1),
                            v[:,1]-v[:,2], ((pv==2)&(pm==1)).astype(float)))
def bundle_scores(rows, base):
    z,_ = arrays(rows)
    v = cal.transform(z,'V',base['V']['theta'])
    m = cal.transform(z,'M',base['M']['theta'])
    pv,pm = cal.labels(v),cal.labels(m)
    return dict(v=pv,m=pm,ratio=expit(v[:,1]-v[:,2]),X=features(z,v,pv,pm),
                V_logprob=logp(v),M_logprob=logp(m))

class Learner:
    def __init__(self):
        self.cache = {}
        self.base_records = {}
    def base(self, rows):
        key = hashlib.sha256(json.dumps(sorted(r['id'] for r in rows)).encode()).hexdigest()[:16]
        if key not in self.cache:
            z,y = arrays(rows)
            value = {k:cal.fit(z,y,k) for k in ('V','M')}
            value['key'] = key
            self.cache[key] = value
            self.base_records[key] = dict(training=describe(rows),models=value)
        return self.cache[key]
    def pipeline(self, train):
        """Fit LR on calibrator OOF features strictly inside this training set."""
        fs = sorted({r['fold'] for r in train})
        assert len(fs)>=2
        n = len(train)
        x = np.full((n,4),np.nan)
        pv = np.full(n,-1,int)
        cross = []
        for f in fs:
            tr = [r for r in train if r['fold']!=f]
            ii = [i for i,r in enumerate(train) if r['fold']==f]
            te = [train[i] for i in ii]
            b = self.base(tr)
            s = bundle_scores(te,b)
            x[ii] = s['X']; pv[ii] = s['v']
            cross.append(dict(fold=int(f),base_key=b['key'],**split_meta(tr,te)))
        assert np.isfinite(x).all() and np.all(pv>=0)
        _,y = arrays(train)
        selected = (pv!=0)&(y!=0)
        fit_rows = [train[i] for i in np.flatnonzero(selected)]
        yy = (y[selected]==1).astype(int)
        meta = dict(training=describe(train),base=self.base(train),crossfit=cross,
                    classifier_training=describe(fit_rows),
                    classifier_indices=np.flatnonzero(selected).tolist(),features=list(FEATURES),
                    true_NS=int(yy.sum()),true_NA=int(len(yy)-yy.sum()),constant=None)
        if len(set(yy.tolist()))<2:
            meta['constant'] = float((yy.sum()+1)/(len(yy)+2))
        else:
            scaler = StandardScaler().fit(x[selected])
            model = LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-8,random_state=37)
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning)
                model.fit(scaler.transform(x[selected]),yy)
            meta.update(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
                        coef=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),
                        n_iter=model.n_iter_.tolist())
        return meta

def infer(rows, pipeline):
    s = bundle_scores(rows,pipeline['base'])
    if pipeline['constant'] is not None:
        s['lr'] = np.full(len(rows),pipeline['constant'])
    else:
        x = (s['X']-np.array(pipeline['mean']))/np.array(pipeline['scale'])
        s['lr'] = expit(x@np.array(pipeline['coef'])+pipeline['intercept'])
    return s

def vm_switch(v,m):
    p=v.copy(); p[(v==2)&(m==1)]=1
    return p

def restore(v,score,threshold):
    p=v.copy(); p[(v==2)&(score>=threshold)]=1
    return p

def select_threshold(y,v,m,score,kind):
    """Match inner VM NS detections, then maximize whole-cohort correctness."""
    target=int(np.sum((y==1)&(vm_switch(v,m)==1)))
    vals=np.unique(score[v==2])
    if kind=='ratio':
        candidates=np.unique(np.r_[0.,.5,vals[(vals>=0)&(vals<=.5)]])
    else:
        candidates=np.unique(np.r_[0.,1.,np.nextafter(1.,np.inf),vals])
    table=[]
    for t in candidates:
        p=restore(v,score,float(t));r=brief(y,p)
        r.update(threshold=float(t),changes=int(np.sum(p!=v)),eligible=bool(r['NS_tp']>=target))
        table.append(r)
    valid=[r for r in table if r['eligible']]
    assert valid,'VM NS target must be reachable without changing S'
    best=min(valid,key=lambda r:(-r['correct'],-r['NA_tp'],-r['MCC'],r['changes'],-r['threshold']))
    return dict(kind=kind,target_NS_tp=target,selected=best,states=table)

def make_outputs(rows,s,ratio_threshold,lr_threshold):
    z,_=arrays(rows);z2=z.copy();z2[:,0]+=2
    pred=dict(U0=cal.labels(z),U2=cal.labels(z2),Std_M=s['m'],Std_V=s['v'],
              VM_switch=vm_switch(s['v'],s['m']),
              Ratio_restore=restore(s['v'],s['ratio'],ratio_threshold),
              Logistic_restore=restore(s['v'],s['lr'],lr_threshold))
    probs=dict(U0=logp(z),U2=logp(z2),Std_M=s['M_logprob'],Std_V=s['V_logprob'])
    for method in REPAIRS:
        assert np.array_equal(pred[method]==0,s['v']==0),'S set changed'
        assert np.all(pred[method][s['v']==1]==1),'Original V NS changed'
        probs[method]=s['V_logprob'].copy()
    return pred,probs
