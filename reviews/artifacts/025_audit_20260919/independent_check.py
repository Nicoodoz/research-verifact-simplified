"""Independent 025 patient folds, nested thresholds and matched-risk envelope checks."""
from pathlib import Path
import sys,json,csv,hashlib,socket,math
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
def blocked(*a,**k):raise RuntimeError('Offline audit')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
root=Path.cwd();out=Path(sys.argv[1]);base=root/'outputs/025_lambda_flip_risk_separability';a=base/'analysis_003'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x]
history={}
for label in ['019_021','022','023','024']:
    history.update(read(root/f'reviews/artifacts/{label}_audit_20260919/audited_files_sha256.json'))
for p,h in history.items():
    with (root/p).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h,p
rows=jl(base/'preparation_001/rows.jsonl');groups={g:[x for x in rows if x['group']==g] for g in ['019','020_R0','020_R1','024_D','024_Q']}
assert len(rows)==4166 and len({x['subject_id'] for x in rows})==16 and len({x['proposition_id'] for x in rows})==1529
dev=set(read(root/'outputs/003_error_analysis/patient_groups.json')['groups']['development'])
assert all(x['subject_id'] in dev for x in rows)
fits=read(a/'fit_audit.json');oof={(x['group'],x['method'],x['proposition_id']):x for x in csvr(a/'candidate_oof.csv')}
plans=read(base/'execution_plan.json')['models'];cache={}
def fit(train,names):
    key=(tuple(names),tuple((x['group'],x['proposition_id']) for x in train))
    if key not in cache:
        xx=np.array([[x['features'][n] for n in names] for x in train]);yy=np.array([x['human_gt']=='Supported' for x in train],dtype=int)
        scaler=StandardScaler().fit(xx);model=None
        if len(set(yy))==2:model=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-8).fit(scaler.transform(xx),yy)
        cache[key]=(scaler,model,(sum(yy)+1)/(len(yy)+2))
    return cache[key]
def probability(model,rr,names):
    scaler,clf,constant=model
    if not rr:return np.array([])
    return clf.predict_proba(scaler.transform([[x['features'][n] for n in names] for x in rr]))[:,1] if clf is not None else np.full(len(rr),constant)
for f in fits:
    g=f['group'];held=f['held_patient'];method=f['method'];names=plans[method.replace('transfer019_','')]
    assert f['features']==names and not {'human_gt','author_type','subject_id'}&set(names)
    source='019' if held=='external_cohort' else ('020_R0' if g=='020_R1' else g)
    assert source==f['train_group']
    train=[x for x in groups[source] if x['candidate'] and x['subject_id']!=held]
    assert [x['proposition_id'] for x in train]==f['training_ids']
    test=[x for x in groups[g] if x['candidate'] and (held=='external_cohort' or x['subject_id']==held)]
    assert {x['subject_id'] for x in train}.isdisjoint(x['subject_id'] for x in test)
    model=fit(train,names)
    np.testing.assert_allclose(model[0].mean_,f['mean'],atol=1e-12,rtol=0)
    np.testing.assert_allclose(model[0].scale_,f['scale'],atol=1e-12,rtol=0)
    if model[1] is not None:
        np.testing.assert_allclose(model[1].coef_[0],f['coef'],atol=1e-12,rtol=0)
        assert abs(model[1].intercept_[0]-f['intercept'])<1e-12
    positives=[]
    for sid in sorted({x['subject_id'] for x in train}):
        inner=[x for x in train if x['subject_id']!=sid];validation=[x for x in train if x['subject_id']==sid]
        pr=probability(fit(inner,names),validation,names) if inner else np.full(len(validation),.5)
        positives.extend(p for p,x in zip(pr,validation) if x['human_gt']=='Supported')
    threshold=sorted(positives,reverse=True)[math.ceil(.8*len(positives))-1] if positives else 0.
    assert abs(threshold-f['threshold'])<1e-12
    preds={x['proposition_id']:x for x in csvr(a/f'predictions_{g}.csv')}
    for x,p in zip(test,probability(model,test,names)):
        expected='Supported' if p>=threshold else ['Supported','Not Supported','Not Addressed'][x['u0']]
        assert preds[x['proposition_id']][method]==expected
        if held!='external_cohort':
            saved=oof[(g,method,x['proposition_id'])]
            assert abs(float(saved['prob'])-p)<1e-12 and abs(float(saved['threshold'])-threshold)<1e-12
# Independent envelope: every feasible mix of <=2 points (LP with one risk constraint).
def envelope(cost,reward,budget):
    cost=np.asarray(cost,float);reward=np.asarray(reward,float)
    best=max(reward[cost<=budget+1e-12],default=0.)
    lo=np.where(cost<budget)[0];hi=np.where(cost>budget)[0]
    if len(lo) and len(hi):
        x=cost[lo,None];z=cost[None,hi]
        mix=reward[lo,None]+(budget-x)/(z-x)*(reward[None,hi]-reward[lo,None])
        best=max(best,float(mix.max()))
    return best
summary=read(a/'summary.json');allglobal=csvr(a/'global_lambda_curves.csv');labels=['Supported','Not Supported','Not Addressed']
checks=0;ci_checks={}
for group,rr in groups.items():
    subject=sorted({x['subject_id'] for x in rr});sid=np.array([subject.index(x['subject_id']) for x in rr]);gt=np.array([x['human_gt']=='Supported' for x in rr]);u0=np.array([x['u0'] for x in rr])
    zs=np.array([[math.log(max(x['scores'][k]/100,1e-6)) for k in labels] for x in rr]);order=np.array([1,2,0])
    gg=[x for x in allglobal if x['group']==group and x['author']=='all'];globals=[]
    for row in gg:
        zz=zs.copy();zz[:,0]+=float(row['lambda_value']);pp=order[np.argmax(zz[:,order],axis=1)];globals.append(pp)
        changed=(pp==0)&(u0!=0);assert sum(changed&gt)==int(row['R']) and sum(changed&~gt)==int(row['risk'])
    assert all(globals[-1]==0)
    def patient_counts(pred):
        changed=(np.asarray(pred)==0)&(u0[None,:]!=0)
        return np.array([[sum(x&(sid==i)&gt) for i in range(len(subject))] for x in changed]),np.array([[sum(x&(sid==i)&~gt) for i in range(len(subject))] for x in changed])
    gR,gF=patient_counts(globals);saved={x['proposition_id']:x for x in csvr(a/f'predictions_{group}.csv')}
    for method,v in summary[group].items():
        pp=np.array([labels.index(saved[x['proposition_id']][method]) for x in rr]);R,F=patient_counts([pp]);R=R[0];F=F[0]
        assert int(sum(R))==v['R'] and int(sum(F))==v['risk']
        det=max(gR.sum(1)[gF.sum(1)<=sum(F)])
        mix=envelope(gF.sum(1),gR.sum(1),sum(F))
        assert abs(det-v['global_R_at_risk'])<1e-10 and abs(mix-v['global_mixture_R_at_risk'])<1e-10
        for leave in v['leave_one_patient_out']:
            w=np.array([p!=leave['excluded_patient'] for p in subject],dtype=int)
            delta=R@w-envelope(gF@w,gR@w,F@w)
            assert abs(delta-leave['R_gain_vs_mixture'])<1e-10
        checks+=1
        if group=='024_D' and method in ('SE','SD'):
            gains=[];discrete=[]
            for seed in range(1000):
                w=np.bincount(np.random.RandomState(seed).choice(len(subject),len(subject)),minlength=len(subject))
                gr=gR@w;gf=gF@w;res=R@w;risk=F@w
                gains.append(res-envelope(gf,gr,risk));discrete.append(res-max(gr[gf<=risk]))
            ci=np.percentile(gains,[2.5,97.5]).tolist();np.testing.assert_allclose(ci,v['mixture_R_gain_ci95'],atol=1e-10,rtol=0)
            original=read(base/'interpretation_001/operating_uncertainty.json')[group+'/'+method]
            np.testing.assert_allclose(np.percentile(discrete,[2.5,97.5]),original['deterministic_ci95'],atol=1e-10)
            ci_checks[method]=dict(mixture_ci95=ci,deterministic_ci95=original['deterministic_ci95'])
result=dict(status='PASS',history_hashes=len(history),observations=len(rows),patients=16,claims=1529,outer_fits=len(fits),independent_fit_cache_entries=len(cache),nested_thresholds_checked=len(fits),matched_frontiers_and_all_LOO=checks,primary_independent_bootstrap=ci_checks,network_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
