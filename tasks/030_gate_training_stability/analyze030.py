"""Fixed operating points versus diagnostic curves; no fitting or selection."""
import itertools
import numpy as np
from scipy.stats import spearmanr
from scipy.optimize import linprog
import common030 as c
from verifact_research.evaluation.metrics import patient_bootstrap,METRICS

def evaluate_sweep(out,spec,rows,mappings):
    out.mkdir(parents=True);methods=('A','B','D');pred={m:c.evaluation.pred_for(rows,mappings[m]) for m in methods};pred.update(U0=np.array([r['u0'] for r in rows]),U2=np.array([r['u2'] for r in rows]));metrics={};matched={};rank={};patients=[];curves=[];loo=[];transitions=[]
    for group in ('pooled','025','026'):
        ii=np.array([i for i,r in enumerate(rows) if group=='pooled' or r['group']==group]);rr=[rows[i] for i in ii];times,gp=c.frontier.global_states(rr);refs={'global_lambda':gp};params={'global_lambda':times}
        for m in methods:params[m],refs[m]=c.evaluation.states(rr,mappings[m]);rank[group+'/'+m]=c.evaluation.ranking(rr,mappings[m])
        for ref,pp in refs.items():
            R,F=c.frontier.counts(rr,pp)
            for i,(r,f) in enumerate(zip(R,F)):curves.append(dict(group=group,reference=ref,index=i,parameter=params[ref][i],R=float(r),risk=float(f),formal_workpoint=ref in methods and i==0))
        for author in ('all','human','llm'):
            ix=[i for i in ii if author=='all' or rows[i]['author_type']==author];ss=[rows[i] for i in ix]
            for m,p in pred.items():metrics[f'{group}/{author}/{m}']=c.point(ss,p[ix])
        dR,dF=c.frontier.counts(rr,pred['D'][ii])
        for ref in ('A','B','global_lambda'):
            R,F=c.frontier.counts(rr,refs[ref]);val=c.frontier.matched(F,R,float(dF[0]),float(dR[0]));matched[group+'/'+ref]=val
            lp=linprog(-R,A_ub=F[None,:],b_ub=[dF[0]],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');c.require(lp.success and abs(dR[0]+lp.fun-val['R_gain_vs_mixture'])<1e-8,'Matched LP check')
            for sid in sorted({r['subject_id'] for r in rr}):
                w=np.array([r['subject_id']!=sid for r in rr],float);tr,tf=c.frontier.counts(rr,pred['D'][ii],w);R,F=c.frontier.counts(rr,refs[ref],w);loo.append(dict(group=group,reference=ref,excluded_patient=sid,**c.frontier.matched(F,R,float(tf[0]),float(tr[0]))))
    for sid in sorted({r['subject_id'] for r in rows}):
        ii=[i for i,r in enumerate(rows) if r['subject_id']==sid];ss=[rows[i] for i in ii]
        for m,p in pred.items():patients.append(dict(subject_id=sid,method=m,**c.point(ss,p[ii])))
    for base in ('A','B'):transitions.extend(dict(comparison='D-minus-'+base,**r) for r in c.evaluation.transition(rows,pred[base],pred['D']))
    c.put(out/'metrics.json',metrics);c.put(out/'matched.json',matched);c.put(out/'ranking.json',rank);c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'curves.csv',curves);c.csvwrite(out/'leave_one_test_patient.csv',loo);c.csvwrite(out/'transitions.csv',transitions)
    c.csvwrite(out/'full_predictions.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],group=r['group'],author_type=r['author_type'],GT=r['human_gt'],candidate=r['candidate'],**{m:c.LABELS[int(p[i])] for m,p in pred.items()}) for i,r in enumerate(rows)])
    c.put(out/'result.json',dict(spec=spec,metrics=metrics,matched=matched,ranking=rank,formal_threshold_source='training-only inner LOPO; no test tuning'))

def bootstrap_sweep(rows,maps,iterations):
    subjects=sorted({r['subject_id'] for r in rows});sindex=np.array([subjects.index(r['subject_id']) for r in rows]);gt=np.array([c.LABELS.index(r['human_gt']) for r in rows]);u0=np.array([r['u0'] for r in rows]);pred={m:c.evaluation.pred_for(rows,maps[m]) for m in ('A','B','D')}
    draws={m:patient_bootstrap(3*gt+p,[r['subject_id'] for r in rows],iterations) for m,p in pred.items()};weights=np.array([np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects)) for seed in range(iterations)],float)
    _,gp=c.frontier.global_states(rows);refs={'global_lambda':gp}
    for m in ('A','B'):_,refs[m]=c.evaluation.states(rows,maps[m])
    all_counts={}
    for ref,pp in refs.items():
        change=(pp==0)&(u0[None,:]!=0);r=np.array([change[:,sindex==s]@(gt[sindex==s]==0).astype(float) for s in range(len(subjects))]);f=np.array([change[:,sindex==s]@(gt[sindex==s]!=0).astype(float) for s in range(len(subjects))]);all_counts[ref]=(weights@r,weights@f)
    changed=(pred['D']==0)&(u0!=0);pr=np.array([sum(changed[sindex==s]&(gt[sindex==s]==0)) for s in range(len(subjects))]);pf=np.array([sum(changed[sindex==s]&(gt[sindex==s]!=0)) for s in range(len(subjects))]);tr=weights@pr;tf=weights@pf;match={}
    for ref,(R,F) in all_counts.items():match[ref]=[c.frontier.matched(F[i],R[i],tf[i],tr[i])['R_gain_vs_mixture'] for i in range(iterations)]
    return dict(metric_differences={base:(draws['D']-draws[base]).tolist() for base in ('A','B')},matched_gain=match,iterations=iterations,refit_inside_bootstrap=False)

def aggregate(run,sweeps,units,rows,features,progress,iterations):
    out=run/'analysis';out.mkdir();canonical=[s for s in sweeps if s['sweep_id']==s['canonical_sweep']];unitlookup={u['unit_id']:u for u in units};all_results={s['sweep_id']:c.read(run/'sweeps'/s['sweep_id']/'evaluation/result.json') for s in canonical};plan={s['sweep_id']:s for s in sweeps};learning=[];matchrows=[];trainstats=[];allpred=[];bootstrap={}
    for spec in canonical:
        sid=spec['sweep_id'];base=run/'sweeps'/sid;maps=c.read(base/'candidate_predictions.json');data=all_results[sid]
        for key,m in data['metrics'].items():
            group,author,method=key.split('/');learning.append(dict(bin=spec['bin'],kind=spec['kind'],k=spec['k'],rep=spec['rep'],sweep_id=sid,group=group,author=author,method=method,**m))
        for key,v in data['matched'].items():group,ref=key.split('/');matchrows.append(dict(bin=spec['bin'],k=spec['k'],rep=spec['rep'],sweep_id=sid,group=group,reference=ref,**v))
        for uid in spec['units']:trainstats.append({k:v for k,v in unitlookup[uid].items() if not k.endswith('_ids')})
        for method,mapping in maps.items():
            for pid,p in mapping.items():allpred.append(dict(bin=spec['bin'],kind=spec['kind'],k=spec['k'],rep=spec['rep'],sweep_id=sid,method=method,proposition_id=pid,**p))
        boot=bootstrap_sweep(rows,maps,iterations);c.put(base/'evaluation/bootstrap.json',boot);bootstrap[sid]=boot;progress('bootstrap '+sid)
    c.csvwrite(out/'learning_curves.csv',learning);c.csvwrite(out/'source_comparison.csv',[r for r in learning if r['kind']=='source']);c.csvwrite(out/'matched_risk.csv',matchrows);c.csvwrite(out/'training_composition.csv',trainstats);c.csvwrite(out/'all_candidate_predictions.csv',allpred)
    bins=sorted({s['bin'] for s in sweeps});summaries={};bin_boot={}
    for binname in bins:
        ids=[s['sweep_id'] for s in canonical if s['bin']==binname];ss={}
        for group in ('pooled','025','026'):
            for method in ('A','B','D'):
                rr=[r for r in learning if r['bin']==binname and r['group']==group and r['author']=='all' and r['method']==method];ss[group+'/'+method]={k:c.summary([r[k] for r in rr]) for k in ('R','H','W','risk','rescue_retention','correct','PA','MCC','S_recall','NS_recall','NA_recall','false_S')}
            for ref in ('A','B','global_lambda'):
                rr=[r['R_gain_vs_mixture'] for r in matchrows if r['bin']==binname and r['group']==group and r['reference']==ref];ss[group+'/matched_'+ref]=dict(**c.summary(rr),positive=sum(x>1e-9 for x in rr),zero=sum(abs(x)<=1e-9 for x in rr),negative=sum(x<-1e-9 for x in rr))
        summaries[binname]=dict(unique_sweeps=len(ids),scheduled_sweeps=sum(s['bin']==binname for s in sweeps),empirical_ranges_are_not_CIs=True,summary=ss)
        meanmatch={ref:np.mean([bootstrap[s]['matched_gain'][ref] for s in ids],axis=0) for ref in ('A','B','global_lambda')};meandelta={ref:np.mean([bootstrap[s]['metric_differences'][ref] for s in ids],axis=0) for ref in ('A','B')}
        bin_boot[binname]=dict(unique_sweeps=len(ids),matched_mean_ci95={k:np.percentile(v,[2.5,97.5]).tolist() for k,v in meanmatch.items()},metric_mean_delta_ci95={k:{name:np.percentile(v[:,i],[2.5,97.5]).tolist() for i,name in enumerate(METRICS)} for k,v in meandelta.items()},matched_mean_draws=meanmatch,metric_mean_draws=meandelta)
    c.put(out/'size_source_summary.json',summaries);c.put(out/'conditional_patient_bootstrap.json',dict(results=bin_boot,interpretation='相同患者重抽权重下跨预设唯一训练轮次平均；固定预测，不在bootstrap内重新训练；实际重训变异另见stability',iterations=iterations))
    stability=[];source_contrasts=[];influence=[];ranking_correlations=[];fmap={r['proposition_id']:r for r in features}
    for binname in bins:
        for method in ('A','B','D'):
            rr=[r for r in allpred if r['bin']==binname and r['method']==method]
            for pid in sorted({r['proposition_id'] for r in rr}):
                vv=[r for r in rr if r['proposition_id']==pid];unique=list({r['model_id']:r for r in vv}.values());n=len(unique);a=sum(r['keep'] for r in unique);vals=lambda key:[r[key] for r in unique]
                stability.append(dict(bin=binname,method=method,proposition_id=pid,subject_id=fmap[pid]['subject_id'],group=fmap[pid]['group'],GT=fmap[pid]['human_gt'],observed_sweeps=len(vv),unique_training_sets=n,composition_variability_estimable=n>=2,accept_fraction=a/n,ever_flipped=n>=2 and 0<a<n,pairwise_action_disagreement=2*a*(n-a)/(n*(n-1)) if n>=2 else None,probability_std=float(np.std(vals('probability'))),threshold_std=float(np.std(vals('threshold'))),decision_margin_std=float(np.std([r['probability']-r['threshold'] for r in unique])),probability_min=min(vals('probability')),probability_max=max(vals('probability')),threshold_min=min(vals('threshold')),threshold_max=max(vals('threshold'))))
                for train_patient in sorted({p for r in unique for p in r['train_patients']}):
                    yes=[r for r in unique if train_patient in r['train_patients']];no=[r for r in unique if train_patient not in r['train_patients']]
                    if yes and no:influence.append(dict(bin=binname,method=method,proposition_id=pid,held_patient=fmap[pid]['subject_id'],training_patient=train_patient,n_in=len(yes),n_out=len(no),accept_difference=float(np.mean([r['keep'] for r in yes])-np.mean([r['keep'] for r in no])),probability_difference=float(np.mean([r['probability'] for r in yes])-np.mean([r['probability'] for r in no])),causal=False))
            ids=sorted({r['sweep_id'] for r in rr});lookup={(r['sweep_id'],r['proposition_id']):r['probability'] for r in rr};pids=sorted(fmap)
            for a,b in itertools.combinations(ids,2):
                x=np.array([lookup[a,p] for p in pids]);y=np.array([lookup[b,p] for p in pids]);rho=float(spearmanr(x,y).statistic) if np.std(x)>0 and np.std(y)>0 else None;ranking_correlations.append(dict(bin=binname,method=method,sweep_a=a,sweep_b=b,spearman=rho))
    # Same r/held/claim, fixed k=5, changed source quota only.
    source_rows=[r for r in allpred if r['kind']=='source'];lookup={(r['bin'],r['rep'],r['method'],r['proposition_id']):r for r in source_rows}
    for rep in sorted({s['rep'] for s in sweeps if s['kind']=='source'}):
        for method in ('A','B','D'):
            for pid in sorted(fmap):
                for a,b in itertools.combinations(sorted({r['bin'] for r in source_rows}),2):
                    ar=plan[plan[f'{a}_r{rep:02}']['canonical_sweep']]['rep'];br=plan[plan[f'{b}_r{rep:02}']['canonical_sweep']]['rep'];x=lookup[a,ar,method,pid];y=lookup[b,br,method,pid];source_contrasts.append(dict(rep=rep,method=method,proposition_id=pid,held_patient=fmap[pid]['subject_id'],source_a=a,source_b=b,action_changed=x['keep']!=y['keep'],probability_delta=y['probability']-x['probability'],threshold_delta=y['threshold']-x['threshold']))
    c.csvwrite(out/'candidate_stability.csv',stability);c.csvwrite(out/'source_paired_contrasts.csv',source_contrasts);c.csvwrite(out/'training_patient_inclusion.csv',influence);c.csvwrite(out/'ranking_correlations.csv',ranking_correlations)
    c.put(out/'stability_summary.json',{binname:{method:dict(candidates=len(ss),estimable=sum(r['composition_variability_estimable'] for r in ss),ever_flipped=sum(r['ever_flipped'] for r in ss),mean_pairwise_disagreement=c.summary([r['pairwise_action_disagreement'] for r in ss]),probability_std=c.summary([r['probability_std'] for r in ss]),threshold_std=c.summary([r['threshold_std'] for r in ss])) for method in ('A','B','D') for ss in [[r for r in stability if r['bin']==binname and r['method']==method]]} for binname in bins})
    c.put(out/'interpretation_limits.json',dict(no_winner_selected=True,no_scientific_conclusion_automated=True,repeated_splits_are_not_independent=True,max_size14_has_no_composition_variability=True,source_is_development_batch_not_external_domain=True,test_bootstrap_refits=False,training_combinations_really_refitted=True,no_new_features_or_threshold_tuning=True))
