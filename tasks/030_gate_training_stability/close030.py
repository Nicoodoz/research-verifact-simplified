"""Post-run verification and descriptive closeout; no refitting or new method."""
import argparse,collections,math,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import linprog
import common030 as c

def run(destination):
    c.offline();out=Path(destination).resolve();c.require(out.is_relative_to(c.OUT) and not out.exists(),'Use new task-owned verification directory');out.mkdir(parents=True);c.verify();run=c.OUT/'run_001';checks={};fallbacks=[];n_models=0
    def ck(name,value):checks[name]=bool(value);c.require(bool(value),'Self-check failed: '+name)
    for rel,h in c.read(run/'manifest.json')['files'].items():ck('hash '+rel,c.sha(run/rel)==h)
    state=c.read(run/'execution_status.json');ck('execution complete',state['state']=='completed' and not state['errors'])
    config=c.read(c.PREP/'config.json');rows=c.lines(c.PREP/'full_rows.jsonl');features=c.lines(c.PREP/'features.jsonl');fmap={r['proposition_id']:r for r in features};byid={r['proposition_id']:r for r in rows};subjects={r['subject_id'] for r in rows};sweeps=c.read(c.PREP/'sweeps.json');units=c.lines(c.PREP/'units.jsonl');ul={u['unit_id']:u for u in units}
    regenerated,generated_units=c.schedule({r['subject_id']:r['group'] for r in features},config);ck('GT blind schedules unchanged',regenerated==sweeps and all(all(u[k]==v for k,v in generated.items()) for u,generated in zip(units,generated_units)))
    model_meta={};coefs=[]
    def predict(meta,ids,name):
        nonlocal n_models
        n_models+=1;train=[fmap[p] for p in meta['training_ids']];names=meta['features'];ck(name+' feature whitelist',names in [c.v.FEATURES[m] for m in ('A','B','D')]);ck(name+' class count',meta['R']==sum(r['human_gt']=='Supported' for r in train))
        tx=np.array([[r['features'][n] for n in names] for r in train]);x=np.array([[fmap[p]['features'][n] for n in names] for p in ids]).reshape(len(ids),len(names))
        if len(train):
            scale=tx.std(axis=0);scale[scale<1e-12]=1;ck(name+' train scaler',np.allclose(tx.mean(axis=0),meta['mean'],rtol=0,atol=1e-12) and np.allclose(scale,meta['scale'],rtol=1e-10,atol=1e-12))
        if meta['fallback']:
            ck(name+' fallback',meta['constant_probability']==(meta['R']+1)/(meta['n']+2));fallbacks.append(dict(model=name,fallback=meta['fallback'],n=meta['n'],R=meta['R']));return np.full(len(ids),meta['constant_probability'])
        ck(name+' two classes',0<meta['R']<len(train));return expit(((x-np.array(meta['mean']))/np.array(meta['scale']))@np.array(meta['coef'])+meta['intercept'])
    for path in sorted((run/'models').glob('*.json')):
        model=c.read(path);name=path.stem;meta=model['final_fit'];trset=set(meta['training_ids']);trpatients=set(meta['training_patients']);ck(name+' exact full training IDs',trset=={r['proposition_id'] for r in features if r['subject_id'] in trpatients});ck(name+' excluded',set(model['excluded_patients'])==subjects-trpatients);ck(name+' schema',meta['features']==c.v.FEATURES[model['method']])
        inner={r['proposition_id']:r for r in model['inner_predictions']};ck(name+' inner coverage',set(inner)==trset)
        for i,im in enumerate(model['inner_folds']):
            held=im['held_patient'];nm=name+'/inner'+str(i);ck(nm+' patient isolation',set(im['training_ids'])=={p for p in trset if fmap[p]['subject_id']!=held} and set(im['test_ids'])=={p for p in trset if fmap[p]['subject_id']==held});p=predict(im,im['test_ids'],nm);ck(nm+' probabilities',np.allclose(p,[inner[q]['probability'] for q in im['test_ids']],rtol=0,atol=1e-12));ck(nm+' target',all(inner[q]['is_R']==(fmap[q]['human_gt']=='Supported') for q in im['test_ids']))
        positive=sorted([r['probability'] for r in inner.values() if r['is_R']],reverse=True);threshold=positive[math.ceil(.8*len(positive))-1] if positive else 0.;ck(name+' threshold',threshold==model['threshold']);testids=[r['proposition_id'] for r in features if r['subject_id'] not in trpatients];p=predict(meta,testids,name+'/final');model_meta[name]=dict(model=model,predictions=dict(zip(testids,p)))
        coefs.extend(dict(model_id=name,method=model['method'],k=len(trpatients),feature=n,scaled_coefficient=b,unscaled_coefficient=b/s,threshold=threshold) for n,b,s in zip(meta['features'],meta.get('coef',[0.]*len(meta['features'])),meta.get('scale',[1.]*len(meta['features']))))
    ck('4356 outer models',len(model_meta)==4356);ck('32688 inner and outer states',n_models==32688);ck('12 recorded fallbacks',len(fallbacks)==len(c.read(run/'fallbacks.json'))==12)
    patient_rows=[];loo_rows=[];ranking_rows=[]
    for spec in sweeps:
        sid=spec['sweep_id'];base=run/'sweeps'/sid
        if sid!=spec['canonical_sweep']:ck(sid+' alias',c.read(base/'alias.json')['canonical_sweep']==spec['canonical_sweep']);continue
        maps=c.read(base/'candidate_predictions.json');pred=c.csvread(base/'evaluation/full_predictions.csv');pl={r['proposition_id']:r for r in pred};ck(sid+' complete test cohort',set(pl)==set(byid))
        for uid in spec['units']:
            u=ul[uid];held=u['held_patient']
            for m in ('A','B','D'):
                z=c.read(base/'units'/f'{held}_{m}.json');mid=c.model_id(m,u['train_patients']);saved=model_meta[mid];meta=saved['model']['final_fit'];ck(uid+m+' exact model',z['model_id']==mid and meta['training_patients']==u['train_patients']);ck(uid+m+' held out',held not in meta['training_patients'])
                ck(uid+m+' probabilities/actions',set(z['candidate_predictions'])==set(u['test_candidate_ids']) and all(abs(v['probability']-saved['predictions'][p])<1e-12 and v['threshold']==saved['model']['threshold'] and v['keep']==(v['probability']>=v['threshold']) and maps[m][p]==v for p,v in z['candidate_predictions'].items()))
        for m in ('A','B','D'):
            ck(sid+m+' cohort mapping',all(pl[r['proposition_id']][m]==c.LABELS[0 if r['candidate'] and maps[m][r['proposition_id']]['keep'] else r['u0']] for r in rows))
        metrics=c.read(base/'evaluation/metrics.json')
        for key,value in metrics.items():
            group,author,m=key.split('/');rs=[r for r in rows if (group=='pooled' or r['group']==group) and (author=='all' or r['author_type']==author)];pp=[c.LABELS.index(pl[r['proposition_id']][m]) for r in rs];gt=[c.LABELS.index(r['human_gt']) for r in rs];cm=[[sum(g==i and p==j for g,p in zip(gt,pp)) for j in range(3)] for i in range(3)];ck(sid+key+' confusion/correct',cm==value['confusion_matrix'] and sum(cm[i][i] for i in range(3))==value['correct']);R=sum(p==0 and r['u0']!=0 and g==0 for r,p,g in zip(rs,pp,gt));H=sum(p==0 and r['u0']==g and g!=0 for r,p,g in zip(rs,pp,gt));W=sum(p==0 and r['u0'] not in (0,g) and g!=0 for r,p,g in zip(rs,pp,gt));ck(sid+key+' RHW',(R,H,W)==(value['R'],value['H'],value['W']));actual=c.old.evaluate(rs,c.old.prediction(rs,pp),profile='none');ck(sid+key+' 002 metrics',all(abs(value[k]-actual[q])<1e-12 for k,q in [('PA','percent_agreement'),('MCC','mcc'),('AC1','gwet_ac1')]))
        curves=c.csvread(base/'evaluation/curves.csv')
        for key,result in c.read(base/'evaluation/matched.json').items():
            group,ref=key.split('/');cc=[r for r in curves if r['group']==group and r['reference']==ref];R=np.array([float(r['R']) for r in cc]);F=np.array([float(r['risk']) for r in cc]);target=metrics[group+'/all/D'];lp=linprog(-R,A_ub=F[None,:],b_ub=[target['risk']],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');ck(sid+key+' LP',lp.success and abs(target['R']+lp.fun-result['R_gain_vs_mixture'])<1e-8)
        patient_rows.extend(dict(bin=spec['bin'],rep=spec['rep'],**r) for r in c.csvread(base/'evaluation/patients.csv'));loo_rows.extend(dict(bin=spec['bin'],rep=spec['rep'],**r) for r in c.csvread(base/'evaluation/leave_one_test_patient.csv'))
        ranking_rows.extend(dict(bin=spec['bin'],rep=spec['rep'],group=k.split('/')[0],method=k.split('/')[1],**v) for k,v in c.read(base/'evaluation/ranking.json').items())
    # Reconstruct composition-stability summaries from candidate decisions, independently.
    ar=run/'analysis';pred=c.csvread(ar/'all_candidate_predictions.csv');lookup=collections.defaultdict(list)
    for r in pred:lookup[r['bin'],r['method'],r['proposition_id']].append(r)
    raw_stability=[]
    for row in c.csvread(ar/'candidate_stability.csv'):
        key=row['bin'],row['method'],row['proposition_id'];rr=lookup[key];uniq=list({r['model_id']:r for r in rr}.values());n=len(uniq);accept=sum(r['keep']=='True' for r in uniq);expected=2*accept*(n-accept)/(n*(n-1)) if n>1 else None;ck('stability '+str(key),int(row['unique_training_sets'])==n and abs(float(row['accept_fraction'])-accept/n)<1e-12 and (row['pairwise_action_disagreement']=='' if expected is None else abs(float(row['pairwise_action_disagreement'])-expected)<1e-12));nr=len(rr);a=sum(r['keep']=='True' for r in rr);raw_stability.append(dict(bin=key[0],method=key[1],proposition_id=key[2],distinct_sweep_occurrences=nr,unique_training_sets=n,occurrence_weighted_disagreement=2*a*(nr-a)/(nr*(nr-1)) if nr>1 else None,deduplicated_disagreement=expected))
    pat=pd.DataFrame(patient_rows);lo=pd.DataFrame(loo_rows);rk=pd.DataFrame(ranking_rows)
    for col in ('correct','R','risk','MCC','PA'):pat[col]=pd.to_numeric(pat[col])
    pp=pat.pivot(index=['bin','rep','subject_id'],columns='method',values=['correct','R','risk']);delta=[]
    for (binname,rep,sid),r in pp.iterrows():
        for base in ('A','B'):delta.append(dict(bin=binname,rep=int(rep),subject_id=sid,comparison='D-minus-'+base,delta_correct=r['correct']['D']-r['correct'][base],delta_R=r['R']['D']-r['R'][base],delta_risk=r['risk']['D']-r['risk'][base]))
    dp=pd.DataFrame(delta);c.csvwrite(out/'patient_mean_directions.csv',dp.groupby(['bin','subject_id','comparison'])[['delta_correct','delta_R','delta_risk']].mean().reset_index().to_dict('records'))
    lo['R_gain_vs_mixture']=pd.to_numeric(lo['R_gain_vs_mixture']);c.csvwrite(out/'leave_one_test_patient_means.csv',lo.groupby(['bin','group','reference','excluded_patient']).R_gain_vs_mixture.agg(['mean','min','max']).reset_index().to_dict('records'))
    c.csvwrite(out/'ranking_summary.csv',rk.groupby(['bin','group','method'])[['AUROC','AP']].agg(['mean','min','max']).reset_index().pipe(lambda df:df.set_axis(['_'.join(x).rstrip('_') if isinstance(x,tuple) else x for x in df.columns],axis=1)).to_dict('records'))
    c.csvwrite(out/'coefficient_ledger.csv',coefs);c.csvwrite(out/'occurrence_and_unique_stability.csv',raw_stability)
    # Bootstrap summary is the paired mean of saved draws, not resampling sweeps.
    result=c.read(ar/'conditional_patient_bootstrap.json')['results']
    for binname,v in result.items():
        ss=[s for s in sweeps if s['bin']==binname and s['sweep_id']==s['canonical_sweep']];boots=[c.read(run/'sweeps'/s['sweep_id']/'evaluation/bootstrap.json') for s in ss]
        for ref in ('A','B','global_lambda'):
            mean=np.mean([b['matched_gain'][ref] for b in boots],axis=0);ck(binname+ref+' mean bootstrap',np.allclose(mean,v['matched_mean_draws'][ref],rtol=0,atol=1e-12) and np.allclose(np.percentile(mean,[2.5,97.5]),v['matched_mean_ci95'][ref]))
    ck('history unchanged',set(subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines())<={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'})
    c.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=len(checks),saved_models_recomputed=n_models,new_fits=0,API_calls=0,fallbacks=fallbacks,checks=checks));c.put(out/'manifest.json',dict(created_utc=c.now(),inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [Path(__file__),run/'manifest.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('030 closeout passed',len(checks),'checks;',n_models,'saved model states; 0 new fits',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
