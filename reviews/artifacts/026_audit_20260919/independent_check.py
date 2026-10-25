"""Independent 026 raw receipts, freeze ordering, final model and risk reference audit."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import sys,json,csv,hashlib,math,socket
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
def blocked(*a,**k):raise RuntimeError('Audit offline')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
root=Path.cwd();out=Path(sys.argv[1]);base=root/'outputs/026_frozen_sd_patient_transfer';a=base/'analysis_001'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x]
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
history={}
for label in ['019_021','022','023','024','025']:history.update(read(root/f'reviews/artifacts/{label}_audit_20260919/audited_files_sha256.json'))
assert all(sha(root/p)==h for p,h in history.items())
gate=read(base/'gate_freeze/gate.json');names=gate['features']
train=[x for x in jl(root/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if x['group']=='024_D' and x['candidate']]
cohort=csvr(base/'preparation_001/cohort.csv')
assert len(train)==103 and [x['proposition_id'] for x in train]==gate['training_ids']
assert {x['subject_id'] for x in train}.isdisjoint(x['subject_id'] for x in cohort)
def fit(rr):
    xx=np.array([[x['features'][n] for n in names] for x in rr]);yy=np.array([x['human_gt']=='Supported' for x in rr],int)
    scaler=StandardScaler().fit(xx);model=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-8).fit(scaler.transform(xx),yy)
    return scaler,model
scaler,model=fit(train)
for k,v in [('mean',scaler.mean_),('scale',scaler.scale_),('coef',model.coef_[0])]:np.testing.assert_array_equal(gate[k],v)
assert gate['intercept']==model.intercept_[0]
positive=[]
for sid in sorted({x['subject_id'] for x in train}):
    rr=[x for x in train if x['subject_id']!=sid];test=[x for x in train if x['subject_id']==sid];ss,mm=fit(rr)
    pp=mm.predict_proba(ss.transform([[x['features'][n] for n in names] for x in test]))[:,1]
    positive.extend(p for x,p in zip(test,pp) if x['human_gt']=='Supported')
threshold=sorted(positive,reverse=True)[math.ceil(.8*len(positive))-1];assert threshold==gate['threshold']
labels=['Supported','Not Supported','Not Addressed']
def scores(sc,lam):
    z=[math.log(max(sc[k]/100,1e-6)) for k in labels]
    return max((1,2,0),key=lambda k:z[k]+(lam if k==0 else 0))
def feature(d,q):
    p=np.array([d[k]/100 for k in labels]);z=[math.log(max(d[k]/100,1e-6)) for k in labels];qz=[math.log(max(q[k]/100,1e-6)) for k in labels]
    return [*p,z[0]-max(z[1:]),abs(z[1]-z[2]),-sum(p*np.log(np.maximum(p,1e-6))),float(scores(d,0)==1),q['Supported']/100,qz[0]-max(qz[1:]),float(scores(q,0)==0),float(scores(q,2)==0),float(scores(q,0)==scores(d,0))]
class Pairs(list):pass
def collapse(v):
    if isinstance(v,Pairs):
        d={}
        for k,x in v:
            x=collapse(x);assert k not in d or canonical(d[k])==canonical(x)
            d[k]=x
        return d
    if isinstance(v,list):return [collapse(x) for x in v]
    return v
def core(obj,k):
    vv=[collapse(v) for n,v in obj if n==k];assert vv and all(canonical(x)==canonical(vv[0]) for x in vv);return vv[0]
jobs=jl(base/'preparation_001/jobs_all.jsonl');by={j['request_id']:j for j in jobs};norm={x['request_id']:x for x in jl(a/'normalized.jsonl')}
assert len(jobs)==1950==len(by)
reg=read(base/'preparation_001/registry.json');cand=read(base/'candidate_freeze/candidates.json');frozen_time=cand['created_utc']
terminal={};times=[];events=[];costs=defaultdict(Decimal);counter=Counter();statuses=Counter()
for p in sorted((base/'attempts').glob('*/request.json')):
    req=read(p);rid=req['request_id'];j=by[rid];receipt=read(p.parent/'receipt.json');tr=receipt['transport']
    assert rid not in terminal and req['attempt']==1 and tr['http_status']==200
    assert req['body']==j['body'] and req['endpoint']==reg['endpoint']
    assert req['body_sha256']==hashlib.sha256(canonical(j['body']).encode()).hexdigest() and receipt['request_sha256']==sha(p)
    ip,op=(3,9) if j['model_key']=='deepseek' else (3,12)
    reserve=Decimal((len(canonical(j['body']).encode())+2000)*ip+j['body']['max_tokens']*op)/1000000
    assert abs(float(reserve)-req['reservation_cny'])<1e-12 and req['prior_task_used_or_reserved_cny']+float(reserve)<=80
    native=json.loads(tr['body_text']);assert native['model']==j['body']['model'];u=native['usage']
    assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
    cost=Decimal(u['prompt_tokens']*ip+u['completion_tokens']*op)/1000000
    costs[j['model_key']+'_'+j['arm']]+=cost
    obj=json.loads(native['choices'][0]['message']['content'],object_pairs_hook=Pairs)
    verdict=core(obj,'verdict');assert verdict in labels
    sc=core(obj,'label_scores') if j['arm']=='S' else None
    if sc is not None:assert set(sc)==set(labels) and all(type(x) is int and 0<=x<=100 for x in sc.values()) and sum(sc.values())==100
    assert verdict==norm[rid]['verdict'] and sc==norm[rid]['scores'] and norm[rid]['status'] in ('valid','valid_with_format_anomaly')
    terminal[rid]=dict(verdict=verdict,scores=sc);counter[j['model_key']+'_'+j['arm']]+=1;statuses[norm[rid]['status']]+=1
    assert req['created_utc']<=tr['started_utc']<=tr['ended_utc']
    times.append((j['model_key'],req['created_utc'],tr['ended_utc']))
    events.extend([(req['created_utc'],1,reserve),(tr['ended_utc'],0,cost-reserve)])
assert counter==Counter(deepseek_B=650,deepseek_S=650,qwen_S=52)
first=min(x[1] for x in times)
assert read(base/'gate_freeze/manifest.json')['created_utc']<first and read(base/'preparation_001/manifest.json')['created_utc']<first
assert max(x[2] for x in times if x[0]=='deepseek')<frozen_time<min(x[1] for x in times if x[0]=='qwen')
candidate_dependencies=read(base/'candidate_freeze/manifest.json')['sha256']
assert sum(p.endswith('/receipt.json') for p in candidate_dependencies)==1300
balance=peak=Decimal(0)
for _,_,v in sorted(events):balance+=v;peak=max(peak,balance)
assert balance==sum(costs.values())==Decimal('16.782714') and peak<=80
lookup={(j['proposition_id'],j['model_key'],j['arm']):terminal[j['request_id']] for j in jobs if j['request_id'] in terminal}
saved={x['proposition_id']:x for x in csvr(a/'predictions.csv')};rows=[];candidates=[];qids=[]
for rr in cohort:
    pid=rr['proposition_id'];d=lookup[pid,'deepseek','S']['scores'];u0=scores(d,0);u2=scores(d,2);sd=peer=u0
    if u0!=0 and u2==0:
        candidates.append(pid);q=lookup[pid,'qwen','S']['scores']
        x=np.array(feature(d,q));prob=1/(1+math.exp(-float(((x-scaler.mean_)/scaler.scale_)@model.coef_[0]+model.intercept_[0])))
        sd=0 if prob>=threshold else u0;peer=0 if scores(q,2)==0 else u0
    b=labels.index(lookup[pid,'deepseek','B']['verdict'])
    for name,v in [('U0',u0),('U2',u2),('SD',sd),('peer_U2',peer),('B',b)]:assert saved[pid][name]==labels[v]
    rows.append(dict(rr,u0=u0,scores=d,SD=sd,peer_U2=peer))
assert set(candidates)==set(cand['candidate_ids'])=={j['proposition_id'] for j in jobs if j['model_key']=='qwen' and j['request_id'] in terminal}
summary=read(a/'summary.json');gg=[x for x in csvr(a/'global_frontier.csv') if x['scope']=='primary_common' and x['author']=='all']
subjects=sorted({x['subject_id'] for x in rows});sid=np.array([subjects.index(x['subject_id']) for x in rows]);gt=np.array([x['human_gt']=='Supported' for x in rows]);u0=np.array([x['u0'] for x in rows])
gp=np.array([[scores(x['scores'],float(g['lambda_value'])) for x in rows] for g in gg]);assert all(gp[-1]==0)
def per_patient(pred):
    changed=(np.atleast_2d(pred)==0)&(u0[None,:]!=0)
    return np.array([[sum(x&(sid==i)&gt) for i in range(6)] for x in changed]),np.array([[sum(x&(sid==i)&~gt) for i in range(6)] for x in changed])
gR,gF=per_patient(gp)
for i,g in enumerate(gg):assert sum(gR[i])==int(g['R']) and sum(gF[i])==int(g['risk'])
def envelope(x,y,budget):
    x=np.asarray(x,float);y=np.asarray(y,float);best=max(y[x<=budget+1e-12],default=0.)
    lo=np.where(x<budget)[0];hi=np.where(x>budget)[0]
    if len(lo) and len(hi):
        mix=y[lo,None]+(budget-x[lo,None])/(x[None,hi]-x[lo,None])*(y[None,hi]-y[lo,None]);best=max(best,float(mix.max()))
    return best
numeric={}
for method,v in summary.items():
    R,F=per_patient([x[method] for x in rows]);R,F=R[0],F[0]
    assert sum(R)==v['R'] and sum(F)==v['risk']
    gain=sum(R)-envelope(gF.sum(1),gR.sum(1),sum(F));assert abs(gain-v['R_gain_vs_mixture'])<1e-10
    for leave in v['leave_one_patient_out']:
        w=np.array([p!=leave['excluded_patient'] for p in subjects],int)
        assert abs(R@w-envelope(gF@w,gR@w,F@w)-leave['R_gain_vs_mixture'])<1e-10
    draws=[]
    for seed in range(1000):
        w=np.bincount(np.random.RandomState(seed).choice(6,6),minlength=6)
        draws.append(R@w-envelope(gF@w,gR@w,F@w))
    ci=np.percentile(draws,[2.5,97.5]);np.testing.assert_allclose(ci,v['mixture_gain_ci95'],atol=1e-10,rtol=0)
    numeric[method]=dict(R=int(sum(R)),risk=int(sum(F)),gain=gain,ci95=ci.tolist(),loo_positive=sum(x['R_gain_vs_mixture']>0 for x in v['leave_one_patient_out']))
result=dict(status='PASS',history_hashes=len(history),templates=1950,requests=1352,counts=dict(counter),parse_statuses=dict(statuses),training_patients=10,validation_patients=6,freeze_order_pass=True,threshold=float(threshold),costs={k:str(v) for k,v in costs.items()},total_cny=str(balance),peak_reserved_cny=str(peak),reference_check=numeric,network_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
