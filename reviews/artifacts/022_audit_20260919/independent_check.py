"""022 independent audit: no task implementation imported; no API or clinical text reads."""
from pathlib import Path
import csv,hashlib,json,socket,sys
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp,softmax
def blocked(*a,**k):raise RuntimeError('Audit network disabled')
socket.create_connection=blocked
socket.socket.connect=blocked
socket.socket.connect_ex=blocked
root=Path.cwd()
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
base=root/'outputs/022_competition_aware_support_calibration'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s]
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
old=read(root/'reviews/artifacts/019_021_audit_20260919/audited_files_sha256.json')
old_bad=[p for p,h in old.items() if sha(root/p)!=h]
assert not old_bad,old_bad
rows=jl(base/'preparation_001/rows.jsonl')
preds=jl(base/'stageA_002/oof_predictions.jsonl')
fits=read(base/'stageA_002/fitted_parameters.json')
labels=['Supported','Not Supported','Not Addressed']
groups=read(root/'outputs/003_error_analysis/patient_groups.json')['groups']
patients={str(r['subject_id']) for r in rows}
assert len(patients)==16 and patients<=set(map(str,groups['development']))
folds={p:i%4 for i,p in enumerate(sorted(patients,key=lambda p:hashlib.sha256(('022/fold/v1:'+p).encode()).hexdigest()))}
assert all(r['fold']==folds[str(r['subject_id'])] for r in rows)
assert all(sum(v==f for v in folds.values())==4 for f in range(4))
assert len({r['proposition_id'] for r in rows})==1529 and sum(r['repeat']==1 for r in rows)==879
by={(r['proposition_id'],r['repeat'],r['method']):r for r in preds}
assert len(by)==len(preds)==24080
z=np.log(np.maximum([[r['scores'][k]/100 for k in labels] for r in rows],1e-6))
y=np.array([labels.index(r['human_gt']) for r in rows])
def logits(z,t,m):
    v=z.copy()
    if m=='G':v[:,0]+=t[0]
    elif m=='C':
        ratio=np.exp(z[:,1])/(np.exp(z[:,1])+np.exp(z[:,2]))
        v[:,0]+=ratio*t[0]+(1-ratio)*t[1]
    elif m=='M':v[:,:2]+=t
    elif m=='V':v=z*t[:3];v[:,:2]+=t[3:]
    elif m=='T':v=z*t[0]
    return v
def penalty(t,m):
    if m=='G':return .01*t[0]**2
    if m=='C':return .005*sum(t*t)+.01*(t[0]-t[1])**2
    if m=='M':return .005*sum(t*t)
    if m=='V':return .01*np.mean((t[:3]-1)**2)+.005*sum(t[3:]*t[3:])
    return .01*(t[0]-1)**2
order=np.array([1,2,0])
fit_checks=[]
for f in fits:
    m=f['method'];fold=f['fold']
    tr=np.array([i for i,r in enumerate(rows) if r['repeat']==0 and r['fold']!=fold])
    te=np.array([i for i,r in enumerate(rows) if r['fold']==fold])
    assert f['train_scoring_ids']==[rows[i]['scoring_request_id'] for i in tr]
    assert not ({rows[i]['subject_id'] for i in tr}&{rows[i]['subject_id'] for i in te})
    assert len(tr)==len({rows[i]['proposition_id'] for i in tr})
    def obj(t):
        v=logits(z[tr],t,m)
        return float(np.mean(logsumexp(v,axis=1)-v[np.arange(len(tr)),y[tr]])+penalty(t,m))
    theta=np.array(f['theta'])
    assert abs(obj(theta)-f['objective'])<1e-12
    center=np.zeros(len(theta));bounds=[(-6,6)]*len(theta)
    if m=='V':center[:3]=1;bounds=[(.05,5)]*3+[(-6,6)]*2
    if m=='T':center[:]=1;bounds=[(.05,5)]
    result=minimize(obj,center,method='L-BFGS-B',jac='3-point',bounds=bounds,options={'maxiter':2000,'ftol':1e-12,'gtol':1e-8})
    assert result.success
    assert abs(result.fun-f['objective'])<1e-9
    decoded=order[np.argmax(logits(z[te],result.x,m)[:,order],axis=1)]
    for i,p in zip(te,decoded):
        row=by[(rows[i]['proposition_id'],rows[i]['repeat'],m)]
        assert row['verdict']==labels[p]
        assert np.max(abs(softmax(logits(z[[i]],theta,m),axis=1)[0]-row['probabilities']))<1e-12
    fit_checks.append(dict(fold=fold,method=m,objective_delta=float(result.fun-f['objective']),max_parameter_delta=float(max(abs(result.x-theta))),labels_equal=True))
with (base/'stageA_002/core_results.csv').open(encoding='utf-8',newline='') as f:core=list(csv.DictReader(f))
with (base/'stageA_002/probability.csv').open(encoding='utf-8',newline='') as f:prob=list(csv.DictReader(f))
def selected(scope,author):
    return [r for r in rows if ((scope=='R0' and r['repeat']==0) or (scope=='R1' and r['repeat']==1) or (scope=='R0_020' and r['repeat']==0 and r['source']=='020')) and (author=='all' or r['author_type']==author)]
for v in core:
    rr=selected(v['scope'],v['author']);m=v['method'];yp=np.array([labels.index(by[(r['proposition_id'],r['repeat'],m)]['verdict']) for r in rr]);gt=np.array([labels.index(r['human_gt']) for r in rr])
    cm=np.zeros((3,3),dtype=int)
    np.add.at(cm,(gt,yp),1)
    n=len(rr);correct=int(np.trace(cm));false=int(sum(cm[1:,0]))
    assert n==int(v['n']) and correct==int(v['correct']) and false==int(v['false_S'])
    actual=cm.sum(axis=1);predicted=cm.sum(axis=0);denom=np.sqrt(float((n*n-int(sum(actual*actual)))*(n*n-int(sum(predicted*predicted)))))
    mcc=(correct*n-sum(actual*predicted))/denom if denom else 0.
    assert abs(mcc-float(v['MCC']))<1e-12 and abs(correct/n-float(v['PA']))<1e-12
for v in prob:
    rr=selected(v['scope'],v['author']);m=v['method']
    pp=np.array([by[(r['proposition_id'],r['repeat'],m)]['probabilities'] for r in rr])
    gt=np.array([labels.index(r['human_gt']) for r in rr])
    nll=float(np.mean(-np.log(pp[np.arange(len(rr)),gt])));brier=float(np.mean(np.sum((pp-np.eye(3)[gt])**2,axis=1)))
    yp=order[np.argmax(pp[:,order],axis=1)];conf=pp.max(axis=1);bins=np.minimum((conf*10).astype(int),9)
    ece=sum(abs(float(np.mean(yp[bins==i]==gt[bins==i]))-float(np.mean(conf[bins==i])))*sum(bins==i)/len(rr) for i in range(10) if any(bins==i))
    assert max(abs(nll-float(v['NLL'])),abs(brier-float(v['Brier'])),abs(ece-float(v['ECE'])))<1e-12
summary={}
for rep in [0,1]:
    rr=[r for r in rows if r['repeat']==rep]
    rescue=harm=removed=new=0
    for r in rr:
        u=by[(r['proposition_id'],rep,'U2')]['verdict'];c=by[(r['proposition_id'],rep,'C')]['verdict'];g=by[(r['proposition_id'],rep,'G')]['verdict']
        assert c==g
        rescue+=u!=r['human_gt'] and c==r['human_gt'];harm+=u==r['human_gt'] and c!=r['human_gt']
        removed+=r['human_gt']!='Supported' and u=='Supported' and c!='Supported'
        new+=r['human_gt']!='Supported' and u!='Supported' and c=='Supported'
    summary['R'+str(rep)]=dict(n=len(rr),rescue=int(rescue),harm=int(harm),removed_false_S=int(removed),new_false_S=int(new))
assert summary['R0']==dict(n=1529,rescue=10,harm=38,removed_false_S=21,new_false_S=0)
assert summary['R1']==dict(n=879,rescue=6,harm=19,removed_false_S=19,new_false_S=0)
assert not read(base/'stageA_002/decision.json')['pass_to_stageB']
summary.update(status='PASS',historical_hashes=len(old),historical_mismatches=old_bad,patient_fold_check=True,fit_checks=fit_checks,core_metric_rows=len(core),probability_rows=len(prob),C_G_equal_labels=2408,network_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='fit_checks'},indent=2))
