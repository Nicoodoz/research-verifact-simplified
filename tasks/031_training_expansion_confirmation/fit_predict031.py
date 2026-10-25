"""Build shared training features and eight confirmation predictions BEFORE its GT."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import numpy as np
from scipy.special import expit
import common031 as c
import api031 as a

def scoped_gt(ids):
    import duckdb,pandas as pd
    con=duckdb.connect();con.register('permitted',pd.DataFrame({'proposition_id':sorted(ids)}));path=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    rs=con.execute('SELECT t.proposition_id,t.human_gt FROM read_csv(?,all_varchar=true) t JOIN permitted p USING(proposition_id)',[str(path)]).fetchall();con.close();c.require(len(rs)==len(ids),'GT alignment');return dict(rs)
def infer(model,f):
    meta=model['final_fit']
    if meta['fallback']:p=meta['constant_probability']
    else:p=float(expit(((np.array([f[k] for k in meta['features']])-np.array(meta['mean']))/np.array(meta['scale']))@np.array(meta['coef'])+meta['intercept']))
    return dict(probability=p,threshold=model['threshold'],keep=bool(p>=model['threshold']))
def build():
    out=c.OUT/'features_001';c.require(not out.exists(),'Features already frozen');materials=c.lines(c.OUT/'judge_inputs_001/materials.jsonl');cand={r['proposition_id']:r for r in c.lines(c.OUT/'candidate_freeze_001/candidates.jsonl')};attempts,term,_=a.state();jobs=c.lines(c.OUT/'candidate_freeze_001/jobs.jsonl');counts={}
    for r in attempts:counts[r['request_id']]=counts.get(r['request_id'],0)+1
    c.require(all(j['request_id'] in term or counts.get(j['request_id'],0)>=3 for j in jobs),'Auxiliary stage incomplete; do not treat unattempted as missing')
    records=[]
    for r in materials:
        pid=r['proposition_id'];d=term.get('031_score_'+pid,{}).get('parsed',dict(status='missing'));status={role:term.get('031_'+role+'_'+pid,{}).get('parsed',dict(status='not_required' if not cand[pid]['candidate'] else 'missing')) for role in ('peer','repeat','trace')};features={m:None for m in ('A','B','C','D')};errors={m:[] for m in features}
        if cand[pid]['candidate']:
            q=status['peer'];repeat=status['repeat'];trace=status['trace'];ok={role:p['status'] in a.api.VALID for role,p in status.items()}
            if ok['peer']:
                af=c.base.score_features(d['scores'],q['scores']);features['A']=af
                if ok['repeat']:
                    rf={k:float(repeat['verdict']==label) for k,label in zip(c.base.REPEAT,c.LABELS)};features['B']=dict(af,**rf)
                if ok['trace']:
                    # Reuse exact029 extraction; a dummy repeat is used only to compute
                    # trace fields, discarded by whitelist, never an imputed scientific feature.
                    tf=c.base.new_features(dict(status='valid',verdict='Supported'),trace);features['C']=dict(af,**{k:tf[k] for k in c.base.SEMANTIC+c.base.QUALITY})
                    if ok['repeat']:features['D']=dict(features['C'],**rf)
            for m,needed in {'A':['peer'],'B':['peer','repeat'],'C':['peer','trace'],'D':['peer','repeat','trace']}.items():errors[m]=[role for role in needed if not ok[role]]
        records.append(dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],group=r['role'],scores=d.get('scores'),u0=cand[pid]['u0'],u2=cand[pid]['u2'],candidate=cand[pid]['candidate'],features=features,missing_required_roles=errors,role_status=dict(score=d['status'],**{k:v['status'] for k,v in status.items()})))
    out.mkdir();c.jsonl(out/'rows.jsonl',records);c.put(out/'manifest.json',dict(created_utc=c.now(),no_confirmation_GT=True,rows_sha256=c.sha(out/'rows.jsonl'),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.OUT/'candidate_freeze_001/candidates.jsonl',c.OUT/'judge_inputs_001/materials.jsonl']}));print('GT-blind features frozen',len(records),flush=True)
def fit_predict():
    out=c.OUT/'inference_001';c.require(not out.exists(),'Inference already frozen');rows=c.lines(c.OUT/'features_001/rows.jsonl');split=c.read(c.OUT/'planning_001/split.json');exp=[r for r in rows if r['group']=='expansion'];test=[r for r in rows if r['group']=='confirmation'];train=c.lines(c.base.PREP/'features.jsonl');gt=scoped_gt({r['proposition_id'] for r in exp});excluded=[]
    for r in exp:
        if not r['candidate']:continue
        if r['features']['D'] is None:excluded.append(dict(proposition_id=r['proposition_id'],reason=r['missing_required_roles']['D']));continue
        train.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],human_gt=gt[r['proposition_id']],features=r['features']['D']))
    c.require(set(r['subject_id'] for r in train).isdisjoint(split['confirmation12']),'Confirmation training leakage');models={};config=c.read(c.base.PREP/'config.json')
    for method in ('A','B','C','D'):
        models['before_'+method]=c.read(c.OUT/'before_models'/f'{method}.json');path=c.OUT/'after_models'/f'{method}.json'
        if path.exists():model=c.read(path);c.require(model['final_fit']['training_ids']==[r['proposition_id'] for r in train],'Training resume identity')
        else:model=c.learning.fold(train,[],c.base.FEATURES[method],'Logistic',config,split['confirmation12']);c.put(path,model)
        models['after_'+method]=model
    predictions=[]
    for r in test:
        result={}
        for name,model in models.items():
            m=name.split('_')[1]
            if r['u0'] is None:result[name]=dict(prediction=None,status='missing_main_score')
            elif not r['candidate']:result[name]=dict(prediction=r['u0'],status='noncandidate_U0')
            elif r['features'][m] is None:result[name]=dict(prediction=r['u0'],status='fallback_U0_missing_aux',missing_roles=r['missing_required_roles'][m])
            else:v=infer(model,r['features'][m]);result[name]=dict(**v,prediction=0 if v['keep'] else r['u0'],status='gate')
        predictions.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],scores=r['scores'],u0=r['u0'],u2=r['u2'],candidate=r['candidate'],methods=result))
    out.mkdir();c.jsonl(out/'confirmation_predictions_blind.jsonl',predictions);c.jsonl(out/'shared_training_features.jsonl',train);c.put(out/'excluded_training_candidates.json',excluded);c.put(out/'manifest.json',dict(created_utc=c.now(),confirmation_GT_connected=False,predictions_sha256=c.sha(out/'confirmation_predictions_blind.jsonl'),training_sha256=c.sha(out/'shared_training_features.jsonl'),model_sha256={str(p.relative_to(c.ROOT)):c.sha(p) for folder in ('before_models','after_models') for p in (c.OUT/folder).glob('[ABCD].json')},confirmation_patients=split['confirmation12'],actual_training_patients=sorted({r['subject_id'] for r in train}),permitted_training_patients=sorted(split['original16']+split['expansion12'])));print('Eight models and confirmation predictions frozen BEFORE confirmation GT',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('features','fit_predict'));args=p.parse_args();build() if args.stage=='features' else fit_predict()
