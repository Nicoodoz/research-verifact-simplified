"""Post-run closeout: verify saved artifacts/models without refitting or APIs."""
import argparse,collections,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from scipy.optimize import linprog
import xgboost as xgb
import common029 as c
import evaluate029 as ev

def run(destination):
    c.offline();out=Path(destination).resolve();c.require(out.is_relative_to(c.OUT) and not out.exists(),'New closeout directory required');out.mkdir(parents=True)
    run=c.OUT/'run_001';c.verify_frozen();checks={};fallbacks=collections.Counter();model_count=0
    def ck(name,value):checks[name]=bool(value);c.require(bool(value),'Closeout check failed: '+name)
    for base in [run,*[run/s/'evaluation' for s in ('patient_OOF','025_to_026','026_to_025')]]:
        for rel,h in c.read(base/'manifest.json')['files'].items():ck('hash '+str(base.relative_to(run))+'/'+rel,c.sha(base/rel)==h)
    state=c.read(run/'execution_status.json');ck('36 completed',state['state']=='completed' and len(state['completed_conditions'])==36 and not state['errors'])
    rows=c.lines(c.PREP/'full_rows.jsonl');features=c.lines(c.PREP/'features.jsonl');byid={r['proposition_id']:r for r in features};subjects=sorted({r['subject_id'] for r in rows});config=c.read(c.PREP/'config.json');methods=ev.conditions(config)
    def predict(meta,ids,name):
        nonlocal model_count
        model_count+=1;training=[byid[p] for p in meta['training_ids']];names=meta['features'];ck(name+' feature order',names in list(c.FEATURES.values()))
        ck(name+' training identity',set(meta['training_patients'])=={r['subject_id'] for r in training});ck(name+' training labels',meta['R']==sum(r['human_gt']=='Supported' for r in training))
        X=np.array([[byid[p]['features'][n] for n in names] for p in ids],float).reshape(len(ids),len(names))
        if meta['estimator']=='Logistic' and training:
            tx=np.array([[r['features'][n] for n in names] for r in training]);mean=tx.mean(axis=0);scale=tx.std(axis=0);scale[scale<1e-12]=1
            ck(name+' train-only scaler',np.allclose(mean,meta['mean'],rtol=0,atol=1e-12) and np.allclose(scale,meta['scale'],rtol=1e-10,atol=1e-12));X=(X-np.array(meta['mean']))/np.array(meta['scale'])
        if meta['fallback']:
            fallbacks[meta['fallback']]+=1;ck(name+' fallback probability',meta['constant_probability']==(meta['R']+1)/(meta['n']+2));return np.full(len(ids),meta['constant_probability'])
        ck(name+' two training classes',0<meta['R']<len(training))
        if meta['estimator']=='Logistic':return expit(X@np.array(meta['coef'])+meta['intercept'])
        booster=xgb.Booster(params={'nthread':1});booster.load_model(bytearray(meta['booster_json'],'utf-8'));ck(name+' 40 trees',len(booster.get_dump())==config['xgboost']['n_estimators'])
        return booster.predict(xgb.DMatrix(X)) if len(ids) else np.array([])
    compact={};trans_summary={};conflict_summary={};patient_summary={};thresholds=[]
    for scope in ('patient_OOF','025_to_026','026_to_025'):
        target=rows if scope=='patient_OOF' else [r for r in rows if r['group']==scope[-3:]];maps={};all_preds=c.csvread(run/scope/'evaluation/full_predictions.csv');pred_lookup={r['proposition_id']:r for r in all_preds};ck(scope+' full coverage',set(pred_lookup)=={r['proposition_id'] for r in target})
        for method in methods:
            record=c.read(run/scope/method/'predictions.json');maps[method]={r['proposition_id']:r for r in record};ck(scope+method+' candidate coverage',set(maps[method])=={r['proposition_id'] for r in target if r['candidate']})
            merged={};paths=sorted((run/scope/method).glob('fold_*.json'));ck(scope+method+' fold count',len(paths)==(16 if scope=='patient_OOF' else 1))
            for path in paths:
                fold=c.read(path);name=scope+'/'+method+'/'+path.stem;excluded=set(fold['excluded_patients']);expected={r['proposition_id'] for r in features if r['subject_id'] not in excluded};meta=fold['final_fit'];ck(name+' exact outer train',set(meta['training_ids'])==expected);ck(name+' exact outer test',set(fold['test_ids'])=={r['proposition_id'] for r in features if r['subject_id'] in excluded})
                ck(name+' feature condition',meta['features']==c.FEATURES[method.split('-')[0]])
                inner={r['proposition_id']:r for r in fold['inner_predictions']};ck(name+' inner OOF coverage',set(inner)==expected)
                for i,im in enumerate(fold['inner_folds']):
                    nm=name+'/inner'+str(i);sid=im['held_patient'];ck(nm+' isolation',set(im['training_ids'])=={p for p in expected if byid[p]['subject_id']!=sid} and set(im['test_ids'])=={p for p in expected if byid[p]['subject_id']==sid});pred=predict(im,im['test_ids'],nm)
                    ck(nm+' replay saved probability',np.allclose(pred,[inner[p]['probability'] for p in im['test_ids']],rtol=0,atol=1e-12))
                    ck(nm+' threshold truth',all(inner[p]['is_R']==(byid[p]['human_gt']=='Supported') for p in im['test_ids']))
                positive=sorted([v['probability'] for v in inner.values() if v['is_R']],reverse=True);t=positive[int(np.ceil(.8*len(positive)))-1] if positive else 0.;ck(name+' exact threshold',t==fold['threshold'])
                pred=predict(meta,fold['test_ids'],name+'/final');local={r['proposition_id']:r for r in fold['predictions']};ck(name+' final predictions',all(abs(float(v)-local[p]['probability'])<1e-12 and local[p]['keep']==(v>=t) and local[p]['threshold']==t for p,v in zip(fold['test_ids'],pred)))
                merged.update(local);thresholds.append(dict(scope=scope,method=method,fold=path.stem,threshold=t,training_patients=meta['training_patients'],held_patients=sorted(excluded)))
            ck(scope+method+' merged predictions',merged==maps[method])
            for r in target:
                p=0 if r['candidate'] and maps[method][r['proposition_id']]['keep'] else r['u0'];ck(scope+method+' mapping '+r['proposition_id'],pred_lookup[r['proposition_id']][method]==c.LABELS[p])
        metrics=c.read(run/scope/'evaluation/metrics.json');matched=c.read(run/scope/'evaluation/matched_risk.json');boot=c.read(run/scope/'evaluation/matched_bootstrap.json');compact[scope]={}
        for key,m in metrics.items():
            group,author,method=key.split('/');ss=[r for r in target if (group=='pooled' or r['group']==group) and (author=='all' or r['author_type']==author)];p=[c.LABELS.index(pred_lookup[r['proposition_id']][method]) for r in ss];gt=[c.LABELS.index(r['human_gt']) for r in ss];cm=[[sum(g==i and v==j for g,v in zip(gt,p)) for j in range(3)] for i in range(3)];ck(scope+key+' independent CM',m['confusion_matrix']==cm and m['correct']==sum(cm[i][i] for i in range(3)))
            R=sum(v==0 and r['u0']!=0 and g==0 for r,v,g in zip(ss,p,gt));H=sum(v==0 and r['u0']==g and g!=0 for r,v,g in zip(ss,p,gt));W=sum(v==0 and r['u0'] not in (0,g) and g!=0 for r,v,g in zip(ss,p,gt));ck(scope+key+' independent RHW',(R,H,W)==(m['R'],m['H'],m['W']))
            actual=c.old.evaluate(ss,c.old.prediction(ss,p),profile='none');ck(scope+key+' 002 metrics',all(abs(m[k]-actual[a])<1e-12 for k,a in [('PA','percent_agreement'),('MCC','mcc'),('AC1','gwet_ac1')]))
            if group=='pooled' and author=='all':compact[scope][method]=dict(metrics=m,matched=matched.get(f'pooled/{method}'),ci=boot.get(f'pooled/{method}'))
        curve=c.csvread(run/scope/'evaluation/curves.csv')
        for key,refs in matched.items():
            group,method=key.split('/');m=metrics[group+'/all/'+method]
            for reference,values in refs.items():
                cs=[r for r in curve if r['group']==group and r['reference']==reference];rr=np.array([float(r['R']) for r in cs]);ff=np.array([float(r['risk']) for r in cs]);lp=linprog(-rr,A_ub=ff[None,:],b_ub=[m['risk']],A_eq=np.ones((1,len(rr))),b_eq=[1],bounds=(0,None),method='highs');ck(scope+key+reference+' independent LP',lp.success and abs(m['R']+lp.fun-values['R_gain_vs_mixture'])<1e-8)
        trs=c.csvread(run/scope/'evaluation/transitions.csv');trans_summary[scope]={k:{flag:sum(r[flag]=='True' for r in trs if r['comparison']==k) for flag in ('blocked_falseS','lost_R','recovered_R','new_falseS','wrong_to_correct','correct_to_wrong')} for k in sorted({r['comparison'] for r in trs})}
        cs=c.csvread(run/scope/'evaluation/conflicts.csv');conflict_summary[scope]={g:{n:{k:sum(int(r[k]) for r in cs if r['method']==n and (g=='pooled' or r['group']==g)) for k in ('n','binary_errors','R','risk')} for n in methods+['SD','repeat','trace']} for g in ['pooled',*sorted({r['group'] for r in cs})]}
        pats=c.csvread(run/scope/'evaluation/patients.csv');patmap={(r['subject_id'],r['method']):r for r in pats if r['group']=='pooled'};summ={}
        for base,new in ev.comparisons(config):
            ds=[dict(subject_id=s,delta_correct=int(patmap[s,new]['correct'])-int(patmap[s,base]['correct']),delta_R=int(patmap[s,new]['R'])-int(patmap[s,base]['R']),delta_risk=int(patmap[s,new]['risk'])-int(patmap[s,base]['risk'])) for s in sorted({r['subject_id'] for r in target})];summ[new+'-minus-'+base]=dict(patients=ds,positive=sum(r['delta_correct']>0 for r in ds),negative=sum(r['delta_correct']<0 for r in ds),ties=sum(r['delta_correct']==0 for r in ds))
        patient_summary[scope]=summ
    ck('history unchanged',not subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).strip())
    c.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=len(checks),checks=checks,models_replayed_without_fit=model_count,fallback_counts=dict(fallbacks),new_model_fits=0,API_calls=0))
    c.put(out/'summary.json',compact);c.put(out/'transitions.json',trans_summary);c.put(out/'conflicts.json',conflict_summary);c.put(out/'patient_comparisons.json',patient_summary);c.csvwrite(out/'thresholds.csv',thresholds)
    c.put(out/'manifest.json',dict(created_utc=c.now(),inputs={str((c.TASK/'close029.py').relative_to(c.ROOT)):c.sha(c.TASK/'close029.py'),str((run/'manifest.json').relative_to(c.ROOT)):c.sha(run/'manifest.json')},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('029 closeout checks passed',len(checks),'saved models replayed',model_count,'new fits 0',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
