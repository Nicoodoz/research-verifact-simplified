"""Executor read-only checks: historical replay, patient isolation, fits, metrics and LP."""
import math
from collections import Counter
import numpy as np
from scipy.special import expit
from scipy.optimize import linprog
import common033 as s

def main(destination='verification_001'):
    s.require(destination.startswith('verification_') and '/' not in destination and '\\' not in destination,'Use a new verification_* child name');out=s.OUT/destination;s.require(not out.exists(),'Verification exists');checks={}
    def ck(key,value):s.require(bool(value),'Check failed: '+key);checks[key]=True
    prep=s.read(s.PREP/'manifest.json')
    for p,h in prep['sources'].items():ck('frozen source '+p,s.sha(s.ROOT/p)==h)
    for p,h in prep['files'].items():ck('prepared '+p,s.sha(s.PREP/p)==h)
    freeze=s.read(s.OUT/'search_001/selection_freeze.json')
    for p,h in freeze['code'].items():ck('selection code '+p,s.sha(s.TASK/p)==h)
    rows=s.lines(s.OUT/'evaluation_001/full_rows.jsonl');lookup={r['proposition_id']:r for r in rows};orig=[r for r in rows if r['partition']=='original16'];origf=s.candidate_rows(orig);search=[r for r in rows if r['partition']=='expansion'];sf=s.candidate_rows(search);rank=s.read(s.OUT/'historical_001/ranking.json');rankby={r['model_id']:r for r in rank};mids=s.read(s.OUT/'historical_001/model_ids.json');prob=np.load(s.OUT/'historical_001/search_probability.npy');op=np.load(s.OUT/'historical_001/original_complement_probability.npy');mi={m:i for i,m in enumerate(mids)};trainsets=set();oldmodels={};oldindex=s.read(s.HIST/'model_index.json')
    for i,mid in enumerate(mids):
        model=s.read(s.HIST/'models'/f'{mid}.json');meta=model['final_fit'];oldmodels[mid]=dict(meta=meta,threshold=model['threshold']);trainsets.add(tuple(meta['training_patients']));p=s.fit_probability(model,sf);ck(mid+' reused search probability',np.allclose(prob[i],p,rtol=0,atol=1e-12));pr=s.pred(search,p,model['threshold']);gt=np.array([s.LABELS.index(r['human_gt']) for r in search]);cm=np.bincount(3*gt+pr,minlength=9).reshape(3,3).tolist();ck(mid+' confusion',cm==rankby[mid]['confusion_matrix']);ck(mid+' training summary',rankby[mid]['train_candidates']==meta['n'] and rankby[mid]['train_R']==meta['R']);mask=np.array([r['subject_id'] not in meta['training_patients'] for r in origf]);ck(mid+' no in-training test cells',np.isnan(op[i,~mask]).all() and np.isfinite(op[i,mask]).all())
    ck('all historical models/sets',len(mids)==4356 and len(trainsets)==1452)
    for i,r in enumerate(s.csvread(s.HIST/'unit_metrics.csv')):
        mid=r['model_id'];sid=r['held_patient'];rr=[x for x in orig if x['subject_id']==sid];ff=s.candidate_rows(rr);model=oldmodels[mid];p=s.old.model_probability(model['meta'],ff);pr=s.pred(rr,p,model['threshold']);gt=np.array([s.LABELS.index(x['human_gt']) for x in rr]);ck('original observed unit '+str(i),int(sum(pr==gt))==int(r['correct']))
    # Reconstruct every newly fitted inner/final scaler/probability/threshold from saved values.
    states=0
    for path in sorted((s.OUT/'models').glob('*.json')):
        model=s.read(path);inner={r['proposition_id']:r for r in model['inner_predictions']}
        for j,meta in enumerate([*model['inner_folds'],model['final_fit']]):
            states+=1;rr=[lookup[q] for q in meta['training_ids']];names=meta['features'];x=np.array([[r['features'][n] for n in names] for r in rr]);mean=x.mean(axis=0);sd=x.std(axis=0);sd[sd<1e-12]=1;ck(path.stem+str(j)+' scaler',np.allclose(mean,meta['mean'],atol=1e-12) and np.allclose(sd,meta['scale'],atol=1e-12));ck(path.stem+str(j)+' R',meta['R']==sum(r['human_gt']=='Supported' for r in rr))
            if 'held_patient' in meta:
                ck(path.stem+str(j)+' inner held',meta['held_patient'] not in meta['training_patients']);te=[lookup[q] for q in meta['test_ids']];pr=s.old.model_probability(meta,te);ck(path.stem+str(j)+' inner predictions',np.allclose(pr,[inner[r['proposition_id']]['probability'] for r in te],rtol=0,atol=1e-12))
        positive=sorted([r['probability'] for r in inner.values() if r['is_R']],reverse=True);ck(path.stem+' threshold',model['threshold']==positive[math.ceil(.8*len(positive))-1] if positive else model['threshold']==0)
    bank=s.read(s.OUT/'evaluation_001/model_usage.json');config=s.read(s.OUT/'evaluation_001/configurations.json');mappings=s.read(s.OUT/'evaluation_001/candidate_predictions.json');cache={}
    for mid,entry in bank['used_models'].items():
        p=s.ROOT/entry['path'];ck(mid+' hash',s.sha(p)==entry['sha256']);cache[mid]=s.read(p)
    for binding in s.read(s.OUT/'evaluation_001/OOF_model_bindings.json'):
        if binding['model_id'] is None:continue
        name=binding['configuration'];sid=binding['held_patient'];model=cache[binding['model_id']];expected={r['proposition_id'] for r in rows if r['candidate'] and r['subject_id'] in config[name]['train_patients'] and r['subject_id']!=sid};ck(name+sid+' exact training',set(model['final_fit']['training_ids'])==expected);rr=[r for r in rows if r['subject_id']==sid and r['candidate']];p=s.fit_probability(model,rr)
        for r,v in zip(rr,p):z=mappings[name][r['proposition_id']];ck(name+r['proposition_id']+' OOF action',abs(z['probability']-v)<1e-12 and z['keep']==(v>=model['threshold']))
    predictions=s.csvread(s.OUT/'evaluation_001/full_predictions.csv');metrics=s.read(s.OUT/'evaluation_001/metrics.json')
    for key,record in metrics.items():
        scope,author,method=key.split('/');rr=[r for r in predictions if (scope=='all40' or r['partition']==scope) and (author=='all' or r['author_type']==author)];cm=[[sum(r['GT']==g and r[method]==p for r in rr) for p in s.LABELS] for g in s.LABELS];ck(key+' confusion',cm==record['confusion_matrix']);R=sum(r['U0']!='Supported' and r[method]=='Supported' and r['GT']=='Supported' for r in rr);H=sum(r['U0']==r['GT'] and r['GT']!='Supported' and r[method]=='Supported' for r in rr);W=sum(r['U0'] not in ('Supported',r['GT']) and r['GT']!='Supported' and r[method]=='Supported' for r in rr);ck(key+' RHW',(R,H,W)==(record['R'],record['H'],record['W']));pr=[dict(proposition_id=r['proposition_id'],verdict=r[method]) for r in rr];cohort=[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],human_gt=r['GT']) for r in rr];m=s.old.old.evaluate(cohort,pr,profile='none');ck(key+'002',all(abs(m[k]-record[f])<1e-12 for k,f in [('percent_agreement','PA'),('mcc','MCC'),('gwet_ac1','AC1')]))
    curve=s.csvread(s.OUT/'evaluation_001/curves.csv')
    for key,value in s.read(s.OUT/'evaluation_001/matched.json').items():
        scope,pair=key.split('/');target,ref=pair.split('-vs-');rr=[r for r in curve if r['scope']==scope and r['reference']==ref];R=np.array([float(r['R']) for r in rr]);F=np.array([float(r['risk']) for r in rr]);m=metrics[scope+'/all/'+target];lp=linprog(-R,A_ub=F[None,:],b_ub=[m['risk']],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');ck(key+' LP',lp.success and abs(m['R']+lp.fun-value['R_gain_vs_mixture'])<1e-8)
    previous=s.read(s.P31/'analysis_001/metrics.json')
    for method in ('A','D'):ck('031 fixed28 anchor '+method,metrics['confirmation/all/'+method+'_historical28']==previous['all/after_'+method] or all(metrics['confirmation/all/'+method+'_historical28'][k]==previous['all/after_'+method][k] for k in ('correct','PA','MCC','AC1','R','H','W','false_S','confusion_matrix')))
    conn=s.read(s.OUT/'evaluation_001/label_connection.json');ck('selection before checking labels',freeze['created_utc']<conn['created_utc']);ck('small directed search',s.read(s.OUT/'search_001/model_usage.json')['new_final_fits']<=48);ck('total finalfit cap',bank['new_final_fits']<=350)
    for folder in ('historical_001','association_001','search_001','evaluation_001','supplement_001'):
        for p,h in s.read(s.OUT/folder/'manifest.json')['files'].items():ck(folder+'/'+p+' output',s.sha(s.OUT/folder/p)==h)
    out.mkdir();s.put(out/'checks.json',dict(created_utc=s.now(),passed=len(checks),checks=checks,new_model_states_checked=states,historical_models_replayed=4356,independent_audit=False,API_calls=0,refits=0));s.status('executor selfcheck passed',checks=len(checks),new_states=states)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default='verification_001');main(p.parse_args().output)
