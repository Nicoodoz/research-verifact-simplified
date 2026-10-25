"""026 frozen-gate inference and audited024 API contracts, new task-owned artifacts."""
from pathlib import Path
import sys,json,math
import numpy as np
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/026_frozen_sd_patient_transfer'
sys.path.insert(0,str(ROOT/'tasks/025_lambda_flip_risk_separability'))
import common025 as risk
import learning025 as learning
import frontier025_numeric as frontier
sys.path.insert(0,str(ROOT/'tasks/024_lambda2_transfer_validation'))
import core024 as api
from transport_direct024 import DirectClient
LABELS=risk.LABELS;MODELS=api.MODELS;CAP=80.;VALID=api.VALID
read=api.read;lines=api.lines;csvread=api.csvread;csvwrite=api.csvwrite;put=api.put;now=api.now;require=api.require;sha=api.file_hash;canonical=api.canonical;fingerprint=api.fingerprint
bound=api.bound;charge=api.charge;parse=api.parse;Config=api.Config;load_config=api.load_config
def features(ds,q):
    d0=int(risk.decode(risk.logs(ds),0));q0=int(risk.decode(risk.logs(q),0));q2=int(risk.decode(risk.logs(q),2))
    return dict(**risk.score_features(ds),**dict(zip(risk.D_NAMES,[q[LABELS[0]]/100,risk.logs(q)[0]-max(risk.logs(q)[1:]),float(q0==0),float(q2==0),float(q0==d0)])))
def infer(gate,ds,q):
    require(gate['features']==risk.METHODS['SD'],'Frozen feature order differs')
    f=features(ds,q);x=np.array([f[k] for k in gate['features']]);z=((x-np.array(gate['mean']))/np.array(gate['scale']))@np.array(gate['coef'])+gate['intercept'];p=float(expit(z))
    return dict(prob=p,threshold=gate['threshold'],keep=p>=gate['threshold'])
def verify_inputs():
    for name in ('gate_freeze/manifest.json','preparation_001/manifest.json'):
        for p,h in read(OUT/name)['sha256'].items():require(sha(ROOT/p)==h,'Frozen file changed: '+p)
    return lines(OUT/'preparation_001/jobs_all.jsonl')
def load_attempts(jobs):
    byid={j['request_id']:j for j in jobs};attempts=[];terminal={}
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        r=read(p);j=byid[r['request_id']];require(r['body']==j['body'] and r['body_sha256']==fingerprint(j['body']),'Request mismatch')
        require(r['reservation_cny']==bound(j),'Reservation mismatch')
        a=dict(request_id=j['request_id'],model_key=j['model_key'],arm=j['arm'],attempt_dir=p.parent.relative_to(OUT).as_posix(),charge_cny=bound(j),charge_basis='unresolved_attempt_reservation',http_status=None)
        rp=p.parent/'receipt.json'
        if rp.exists():
            rec=read(rp);require(rec['request_sha256']==sha(p),'Receipt binding mismatch');tr=rec['transport'];cost,basis=charge(j,tr);a.update(charge_cny=cost,charge_basis=basis,http_status=tr['http_status'])
            if tr['http_status']==200:
                require(j['request_id'] not in terminal,'Repeated HTTP200')
                v=parse(tr,j['arm']=='S')
                if v.get('model_returned')!=j['body']['model']:v.update(status='invalid_core_fields',errors=v['errors']+['unexpected_model'])
                terminal[j['request_id']]=v
        attempts.append(a)
    return attempts,terminal
def eligible(jobs,stage):
    if stage=='deepseek':return [j for j in jobs if j['model_key']=='deepseek']
    require(stage=='qwen','Invalid stage');p=OUT/'candidate_freeze/manifest.json'
    require(p.exists(),'Candidate stage not frozen')
    for name,h in read(p)['sha256'].items():require(sha(ROOT/name)==h,'Candidate source changed')
    ids=set(read(OUT/'candidate_freeze/candidates.json')['candidate_ids'])
    return [j for j in jobs if j['model_key']=='qwen' and j['proposition_id'] in ids]
