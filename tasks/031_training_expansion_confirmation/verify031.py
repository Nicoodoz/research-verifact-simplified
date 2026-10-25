"""Read-only executor self-check of031 data, eight models, prediction gate and costs."""
import argparse,math,json
from pathlib import Path
from collections import Counter
from decimal import Decimal
import numpy as np
from scipy.special import expit
from scipy.optimize import linprog
import common031 as c
import api031 as a

def run(destination):
    out=c.OUT/destination;c.require(not out.exists(),'New verification directory required');checks={}
    def ck(name,v):checks[name]=bool(v);c.require(bool(v),'031 check failed: '+name)
    split=c.read(c.OUT/'planning_001/split.json');original=set(split['original16']);expand=set(split['expansion12']);confirm=set(split['confirmation12']);ck('patient isolation',len(original)==16 and len(expand)==len(confirm)==12 and len(original|expand|confirm)==40)
    remaining=sorted(expand|confirm,key=c.rank);ck('hash split',remaining[:12]==split['expansion12'] and remaining[12:]==split['confirmation12'])
    attempts,terminal,_=a.state();fee=Decimal(0);first_call=None;raw200=Counter()
    for r in attempts:
        path=c.ROOT/r['path'];request=c.read(path);job=request['job'];ck('budget '+path.parent.name,request['prior_task_used_or_reserved_cny']+request['reservation_cny']<=80+1e-12);fee+=Decimal(str(r['charge_cny']));first_call=min(first_call,request['created_utc']) if first_call else request['created_utc']
        if r['http_status']==200:raw200[job['request_id']]+=1
        if job['kind']=='chat':ck('payload '+path.parent.name,set(json.loads(job['body']['messages'][1]['content']))=={'proposition','reference'})
    ck('no successful answer rerun',all(n==1 for n in raw200.values()));ck('before models predateAPI',c.read(c.OUT/'before_models/manifest.json')['created_utc']<first_call);ck('task total80',fee<=80)
    rows=c.lines(c.OUT/'features_001/rows.jsonl');blind=c.lines(c.OUT/'inference_001/confirmation_predictions_blind.jsonl');train=c.lines(c.OUT/'inference_001/shared_training_features.jsonl');original_features=c.lines(c.base.PREP/'features.jsonl');training={r['proposition_id']:r for r in train};ck('training only permitted patients',set(r['subject_id'] for r in train)<=original|expand and not set(r['subject_id'] for r in train)&confirm)
    for row in rows:
        pid=row['proposition_id'];score=terminal.get('031_score_'+pid,{}).get('parsed',{})
        if score.get('status') in a.api.VALID:
            u0=int(c.base.old.decode(c.base.old.logs(score['scores']),0));u2=int(c.base.old.decode(c.base.old.logs(score['scores']),2));ck(pid+' main score/candidate',row['scores']==score['scores'] and (row['u0'],row['u2'],row['candidate'])==(u0,u2,u0!=0 and u2==0))
        if row['features']['D'] is not None:
            q=terminal['031_peer_'+pid]['parsed'];rp=terminal['031_repeat_'+pid]['parsed'];tr=terminal['031_trace_'+pid]['parsed'];f=c.base.score_features(score['scores'],q['scores']);f.update(c.base.new_features(rp,tr))
            for m in 'ABCD':ck(pid+m+' exact029 features',all(f[k]==row['features'][m][k] for k in c.base.FEATURES[m]))
    ck('confirmation full IDs',{r['proposition_id'] for r in blind}=={r['proposition_id'] for r in rows if r['group']=='confirmation'})
    models={};states=0
    def probability(meta,ids,pool,name):
        nonlocal states
        states+=1;rr=[pool[p] for p in meta['training_ids']];names=meta['features'];x=np.asarray([[pool[p]['features'][k] for k in names] for p in ids],float).reshape(len(ids),len(names));ck(name+' target count',meta['R']==sum(r['human_gt']=='Supported' for r in rr))
        if rr:
            tx=np.asarray([[r['features'][k] for k in names] for r in rr]);sd=tx.std(axis=0);sd[sd<1e-12]=1;ck(name+' scaler',np.allclose(tx.mean(axis=0),meta['mean'],atol=1e-12) and np.allclose(sd,meta['scale'],atol=1e-12))
        if meta['fallback']:return np.full(len(ids),meta['constant_probability'])
        return expit(((x-np.asarray(meta['mean']))/np.asarray(meta['scale']))@np.asarray(meta['coef'])+meta['intercept'])
    for era in ('before','after'):
        pool={r['proposition_id']:r for r in (original_features if era=='before' else train)}
        for m in 'ABCD':
            model=c.read(c.OUT/(era+'_models')/(m+'.json'));name=era+'_'+m;models[name]=model;meta=model['final_fit'];ck(name+' training IDs',set(meta['training_ids'])==set(pool));ck(name+' schema',meta['features']==c.base.FEATURES[m]);ck(name+' no confirm',not set(meta['training_patients'])&confirm)
            inner={r['proposition_id']:r for r in model['inner_predictions']};ck(name+' inner coverage',set(inner)==set(pool))
            for i,im in enumerate(model['inner_folds']):
                held=im['held_patient'];nm=name+str(i);ck(nm+' inner exclusion',set(im['training_ids'])=={p for p,r in pool.items() if r['subject_id']!=held});p=probability(im,im['test_ids'],pool,nm);ck(nm+' inner probability',np.allclose(p,[inner[q]['probability'] for q in im['test_ids']],rtol=0,atol=1e-12));ck(nm+' threshold target labels',all(inner[q]['is_R']==(pool[q]['human_gt']=='Supported') for q in im['test_ids']))
            positives=sorted([v['probability'] for v in inner.values() if v['is_R']],reverse=True);t=positives[math.ceil(.8*len(positives))-1] if positives else 0;ck(name+' threshold',t==model['threshold']);probability(meta,[],pool,name+'final')
    index={r['proposition_id']:r for r in rows};materials={r['proposition_id']:r for r in c.lines(c.OUT/'judge_inputs_001/materials.jsonl')}
    b=a.api.old.baseline;passages={r['passage_id']:r for r in c.lines(c.OUT/'materials_001/corpus.jsonl')};sourceinputs={r['proposition_id']:r for r in c.lines(c.OUT/'materials_001/inputs.jsonl')}
    for record in c.lines(c.OUT/'retrieval_001/candidates.jsonl'):
        pid=record['proposition_id'];pools=record['candidate_ids'];ck(pid+' original candidates',all(pools[m+'48']==b.candidates(record['rankings'],m) for m in ('A','B','C')));union=sorted({x for pool in pools.values() for x in pool});scores={}
        if union:
            native=json.loads(terminal['031_rerank_'+pid]['transport']['body_text']);scores={union[r['index']]:float(r['relevance_score']) for r in native['results']};ck(pid+' rerank documents',terminal['031_rerank_'+pid]['job']['body']['documents']==[passages[p]['search_text'] for p in union])
        packed=b.core.select_evidence(pools['C48'],scores,passages,sourceinputs[pid]['admission']);ck(pid+' C48 packing',packed['reference']==materials[pid]['reference'])
    for r in blind:
        row=index[r['proposition_id']]
        for name,record in r['methods'].items():
            m=name.split('_')[1]
            if row['u0'] is None:expected=None
            elif not row['candidate'] or row['features'][m] is None:expected=row['u0']
            else:
                meta=models[name]['final_fit'];x=np.array([row['features'][m][k] for k in meta['features']]);p=float(expit(((x-np.array(meta['mean']))/np.array(meta['scale']))@np.array(meta['coef'])+meta['intercept']));ck(r['proposition_id']+name+' probability',abs(p-record['probability'])<1e-12);expected=0 if p>=models[name]['threshold'] else row['u0']
            ck(r['proposition_id']+name+' action',record['prediction']==expected)
    # Complete scientific outputs cannot be altered after GT connection.
    inf=c.read(c.OUT/'inference_001/manifest.json');connection=c.read(c.OUT/'analysis_001/GT_connection.json');ck('GT after all frozen predictions',inf['created_utc']<connection['connected_utc'] and connection['prediction_sha256']==inf['predictions_sha256'])
    for p,h in inf['model_sha256'].items():ck('model fingerprint '+p,c.sha(c.ROOT/p)==h)
    analysis=c.OUT/'analysis_001';pred=c.csvread(analysis/'predictions.csv');metrics=c.read(analysis/'metrics.json');known=[r for r in pred if r['U0']];counts={}
    for key,value in metrics.items():
        author,method=key.split('/');rr=[r for r in known if author=='all' or r['author_type']==author];cm=[[sum(r['GT']==g and r[method]==p for r in rr) for p in c.LABELS] for g in c.LABELS];ck(key+' independent confusion',cm==value['confusion_matrix'] and sum(cm[i][i] for i in range(3))==value['correct']);R=sum(r['U0']!='Supported' and r[method]=='Supported' and r['GT']=='Supported' for r in rr);H=sum(r[method]=='Supported' and r['GT']!='Supported' and r['U0']==r['GT'] for r in rr);W=sum(r[method]=='Supported' and r['GT']!='Supported' and r['U0'] not in ('Supported',r['GT']) for r in rr);ck(key+' RHW',(R,H,W)==(value['R'],value['H'],value['W']))
        cohort=[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],human_gt=r['GT']) for r in rr];pr=[dict(proposition_id=r['proposition_id'],verdict=r[method]) for r in rr];m=c.base.old.evaluate(cohort,pr,profile='none');ck(key+'002',all(abs(value[k]-m[z])<1e-12 for k,z in [('PA','percent_agreement'),('AC1','gwet_ac1'),('MCC','mcc')]))
    curves=c.csvread(analysis/'curves.csv')
    for key,value in c.read(analysis/'matched.json').items():
        target,ref=key.split('-vs-');rr=[r for r in curves if r['reference']==ref];R=np.array([float(r['R']) for r in rr]);F=np.array([float(r['risk']) for r in rr]);m=metrics['all/'+target];lp=linprog(-R,A_ub=F[None,:],b_ub=[m['risk']],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');ck(key+' LP',lp.success and abs(m['R']+lp.fun-value['R_gain_vs_mixture'])<1e-8)
    for folder in ('analysis_001','costs_001'):
        for rel,h in c.read(c.OUT/folder/'manifest.json')['outputs'].items():ck(folder+rel+' hash',c.sha(c.OUT/folder/rel)==h)
    out.mkdir();c.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=len(checks),saved_states_checked=states,API_cost_decimal=str(fee),checks=checks));c.put(out/'manifest.json',dict(created_utc=c.now(),inputs={str((c.TASK/'verify031.py').relative_to(c.ROOT)):c.sha(c.TASK/'verify031.py')},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('031 self-check passed',len(checks),'cost',fee,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='verification_001');run(p.parse_args().output)
