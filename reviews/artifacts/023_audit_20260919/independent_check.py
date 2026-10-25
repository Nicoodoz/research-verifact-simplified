"""Independent 023 checks; no 023 implementation imported; no network."""
from pathlib import Path
import sys,json,csv,math,hashlib,socket
import numpy as np
def blocked(*a,**k):raise RuntimeError('Offline audit')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
r=Path.cwd();out=Path(sys.argv[1]);base=r/'outputs/023_lambda_boundary_response_analysis'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x]
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
history={}
for p in ['reviews/artifacts/019_021_audit_20260919/audited_files_sha256.json','reviews/artifacts/022_audit_20260919/audited_files_sha256.json']:history.update(read(r/p))
bad=[]
for p,h in history.items():
    with (r/p).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=h:bad.append(p)
assert not bad,bad
rows=jl(base/'preparation_001/scores.jsonl');old=jl(r/'outputs/022_competition_aware_support_calibration/preparation_001/rows.jsonl')
assert len(rows)==2408 and all(all(o[k]==v for k,v in n.items()) for n,o in zip(rows,old))
labels=['Supported','Not Supported','Not Addressed'];order=[1,2,0]
z=np.array([[math.log(max(x['scores'][k]/100,1e-6)) for k in labels] for x in rows])
gt=np.array([labels.index(x['human_gt']) for x in rows]);B=np.array([labels.index(x['B']) for x in rows])
groups={'019':[i for i,x in enumerate(rows) if x['source']=='019'],'020_R0':[i for i,x in enumerate(rows) if x['source']=='020' and x['repeat']==0],'020_R1':[i for i,x in enumerate(rows) if x['repeat']==1],'pooled_R0':[i for i,x in enumerate(rows) if x['repeat']==0]}
dev=set(read(r/'outputs/003_error_analysis/patient_groups.json')['groups']['development'])
assert all(str(x['subject_id']) in dev for x in rows)
def predict(lam):
    p=z.copy();p[:,0]+=lam
    return np.array(order)[p[:,order].argmax(axis=1)]
p0=predict(0);p2=predict(2)
switch=jl(base/'analysis_001/switches.jsonl')
for x,t,zz in zip(rows,switch,z):
    assert x['proposition_id']==t['proposition_id'] and x['repeat']==t['repeat']
    threshold=max(zz[1:])-zz[0];assert threshold==t['theoretical_threshold']
    if t['status']=='switch_in_0_4':
        first=t['first_S_lambda'];prev=t['previous_nonS_lambda']
        assert math.nextafter(first,-math.inf)==prev
        assert zz[0]+prev<=max(zz[1:]) and zz[0]+first>max(zz[1:])
    elif t['status']=='already_S_at_0':assert zz[0]>max(zz[1:])
    else:assert zz[0]+4<=max(zz[1:])
# Independently reconstruct all aggregate, exact, patient and leave-one-out metrics.
checked={}
for name in ['dense_grid','exact_states','patient_curves','leave_one_out_curves','local_sensitivity','patient_local_sensitivity']:
    table=csvr(base/'analysis_001'/(name+'.csv'));cache={}
    for v in table:
        lam=float(v['lambda_value'])
        if lam not in cache:cache[lam]=predict(lam)
        ix=groups[v['group']]
        if v.get('author','all')!='all':ix=[i for i in ix if rows[i]['author_type']==v['author']]
        if 'subject_id' in v:ix=[i for i in ix if rows[i]['subject_id']==v['subject_id']]
        if 'excluded_patient' in v:ix=[i for i in ix if rows[i]['subject_id']!=v['excluded_patient']]
        pp=cache[lam][ix];y=gt[ix];n=len(ix);cm=np.bincount(y*3+pp,minlength=9).reshape(3,3).astype(np.int64)
        correct=int(np.trace(cm));false=int(sum(cm[1:,0]));act=cm.sum(axis=1);pre=cm.sum(axis=0)
        denom=math.sqrt((n*n-int(act@act))*(n*n-int(pre@pre)))
        mcc=(n*correct-int(act@pre))/denom if denom else 0.
        pbar=(act+pre)/(2*n);pe=float(sum(pbar*(1-pbar))/2);ac1=(correct/n-pe)/(1-pe)
        for key,val in [('n',n),('correct',correct),('false_S',false)]:assert int(v[key])==val,(name,key)
        for key,val in [('PA',correct/n),('MCC',mcc),('AC1',ac1)]:assert abs(float(v[key])-val)<1e-12,(name,key)
        changes=pp!=p0[ix]
        R=int(sum(changes&(y==0)));H=int(sum(changes&(y!=0)&(p0[ix]==y)));W=int(sum(changes&(y!=0)&(p0[ix]!=y)))
        assert (R,H,W)==tuple(int(v[k]) for k in ['rescue','harm','wrong_to_falseS'])
        assert int(v['delta_correct_B'])==correct-int(sum(B[ix]==y))
        if 'label_changes_vs2' in v:assert int(v['label_changes_vs2'])==sum(pp!=p2[ix]) and int(v['delta_correct_vs2'])==correct-int(sum(p2[ix]==y))
    checked[name]=len(table)
summary=read(base/'analysis_001/summary.json');plateaus={}
for g,ix in groups.items():
    times=[switch[i]['first_S_lambda'] for i in ix if switch[i]['first_S_lambda'] is not None]
    lo=max(t for t in times if t<=2);hi=min(t for t in times if t>2)
    q=summary[g]['authors']['all'];assert (lo,hi)==(q['exact_label_plateau']['start'],q['exact_label_plateau']['end'])
    assert lo==1.9459101490553132 and hi==2.079441541679836
    table=[v for v in csvr(base/'analysis_001/dense_grid.csv') if v['group']==g and v['author']=='all']
    two=table[200];flags=[float(v['PA'])>=float(two['PA'])-.01-1e-12 and float(v['MCC'])>=float(two['MCC'])-.02-1e-12 for v in table]
    left=right=200
    while left>0 and flags[left-1]:left-=1
    while right<400 and flags[right+1]:right+=1
    assert q['near_U2_grid_region']==[left/100,right/100]
    plateaus[g]=dict(exact=[lo,hi],near_U2=[left/100,right/100])
# Anchor labels and frozen metric summaries, without running the original prepare generator.
sys.path.insert(0,str(r/'src'))
from verifact_research.evaluation import evaluate
anchors=0
for g in ['019','020_R0','020_R1']:
    folder=r/'outputs'/('019_support_boundary_screen/selection/analysis_001' if g=='019' else '020_lambda2_patient_validation/analysis_001')
    rep=1 if g=='020_R1' else 0;historical={v['proposition_id']:v for v in csvr(folder/f'predictions_r{rep}.csv')};metrics=read(folder/'metrics.json')
    for lam in ([0,.5,1,1.5,2,3,4] if g=='019' else [0,2]):
        arm='U0' if lam==0 else (f'U_lambda_{lam:g}' if g=='019' else 'U2');p=predict(lam)
        assert all(historical[rows[i]['proposition_id']][arm]==labels[p[i]] for i in groups[g])
        for author in ['all','human','llm']:
            ix=[i for i in groups[g] if author=='all' or rows[i]['author_type']==author]
            m=evaluate([rows[i] for i in ix],[dict(proposition_id=rows[i]['proposition_id'],verdict=labels[p[i]]) for i in ix],profile='none',missing='error')
            h=metrics[f'r{rep}/{author}/{arm}']
            assert all(m[k]==h[k] for k in ['n','confusion_matrix','percent_agreement','mcc','gwet_ac1','per_class'])
            anchors+=1
oldpp={(v['proposition_id'],v['repeat'],v['method']):v['verdict'] for v in jl(r/'outputs/022_competition_aware_support_calibration/stageA_002/oof_predictions.jsonl')}
p=predict(1.75)
assert all(oldpp[(x['proposition_id'],x['repeat'],'G')]==oldpp[(x['proposition_id'],x['repeat'],'C')]==labels[p[i]] for i,x in enumerate(rows))
result=dict(status='PASS',history_files=len(history),history_mismatches=bad,score_observations=len(rows),switch_checks=len(switch),metric_rows=checked,anchor_groups=anchors,plateaus=plateaus,connection022_labels=2408,network_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
