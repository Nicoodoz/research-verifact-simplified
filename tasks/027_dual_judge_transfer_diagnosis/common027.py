"""027 pure offline diagnostics. No client, secret, or model imports."""
import sys,json,hashlib,math,socket
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/027_dual_judge_transfer_diagnosis'
sys.path.insert(0,str(ROOT/'tasks/025_lambda_flip_risk_separability'))
import common025 as c
import frontier025_numeric as frontier
LABELS=c.LABELS
def blocked(*args,**kwargs):raise RuntimeError('027 network/training prohibited')
def offline():
    socket.socket.connect=blocked;socket.create_connection=blocked
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    LogisticRegression.fit=blocked;StandardScaler.fit=blocked
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def features(ds,qs):
    d0=int(c.decode(c.logs(ds),0));q0=int(c.decode(c.logs(qs),0));q2=int(c.decode(c.logs(qs),2))
    return dict(**c.score_features(ds),**dict(zip(c.D_NAMES,[qs[LABELS[0]]/100,c.logs(qs)[0]-max(c.logs(qs)[1:]),float(q0==0),float(q2==0),float(q0==d0)])))
def probability(gate,f):
    terms=[(f[k]-m)/s*b for k,m,s,b in zip(gate['features'],gate['mean'],gate['scale'],gate['coef'])];z=gate['intercept']+sum(terms)
    return 1/(1+math.exp(-z)),terms
def ranking_states(scores):
    scores=np.asarray(scores,dtype=float);ts=[float(np.nextafter(max(scores),np.inf)),*sorted(set(scores),reverse=True)]
    return ts,np.array([scores>=t for t in ts])
def first_target(rescue,risk,target):
    indices=np.flatnonzero(rescue>=target-1e-10)
    if not len(indices):return None
    i=min(indices,key=lambda i:(risk[i],rescue[i],i));return int(i)
def patient_auc(y,s,w,ids):
    numerator=denominator=0.
    for sid in set(ids):
        ix=np.array([v==sid for v in ids]);p=np.flatnonzero(ix&(y==1));n=np.flatnonzero(ix&(y==0))
        for i in p:
            for j in n:
                weight=w[i]*w[j];numerator+=weight*((s[i]>s[j])+.5*(s[i]==s[j]));denominator+=weight
    return numerator/denominator if denominator else None
