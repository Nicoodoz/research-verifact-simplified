"""002 metrics, fixed-prediction patient uncertainty, and full risk references."""
import itertools
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
import common029 as c

def conditions(config):return [f'{a}-{e}' for a in config['inputs'] for e in config['estimators']]
def comparisons(config):
    pairs=[]
    for e in config['estimators']:
        pairs.extend((f'{base}-{e}',f'{new}-{e}') for base,new in [('A','B'),('A','C'),('B','D'),('C','D'),('C_no_quality','C'),('D_no_quality','D')])
    pairs.extend((f'{a}-Logistic',f'{a}-XGBoost') for a in ('A','B','C','D'))
    return pairs
def point(rows,pred):
    m=c.old.point(rows,pred);total=sum(r['candidate'] and r['human_gt']=='Supported' for r in rows)
    return dict(m,rescue_retention=m['R']/total if total else None,R_available=total,delta_correct_vs_U0=m['net'])
def pred_for(rows,mapping):return np.array([0 if r['candidate'] and mapping[r['proposition_id']]['keep'] else r['u0'] for r in rows])
def states(rows,mapping):
    ps=[mapping[r['proposition_id']]['probability'] for r in rows if r['candidate']]
    ts=[float(np.nextafter(max(ps),np.inf)),*sorted(set(ps),reverse=True)] if ps else [1.]
    pp=[pred_for(rows,mapping)]
    pp.extend(np.array([0 if r['candidate'] and mapping[r['proposition_id']]['probability']>=t else r['u0'] for r in rows]) for t in ts)
    return [None,*ts],np.array(pp)
def reference_names(method,available):
    a,e=method.split('-',1);names={'global_lambda','SD','repeat',f'A-{e}'}
    if a.startswith('D'):names.add(f'B-{e}')
    if a in ('C','D'):names.add(f'{a}_no_quality-{e}')
    if e=='XGBoost' and a in ('A','B','C','D'):names.add(f'{a}-Logistic')
    return sorted(n for n in names if n!=method and n in available)
def transition(rows,bpred,cpred):
    ledger=[]
    for r,b,p in zip(rows,bpred,cpred):
        if not r['candidate']:continue
        gt=c.LABELS.index(r['human_gt']);ledger.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],group=r['group'],author_type=r['author_type'],GT=r['human_gt'],baseline=c.LABELS[b],candidate=c.LABELS[p],blocked_falseS=bool(b==0 and p!=0 and gt!=0),lost_R=bool(b==0 and p!=0 and gt==0),recovered_R=bool(b!=0 and p==0 and gt==0),new_falseS=bool(b!=0 and p==0 and gt!=0),wrong_to_correct=bool(b!=gt and p==gt),correct_to_wrong=bool(b==gt and p!=gt)))
    return ledger
def ranking(rows,mapping,weights=None):
    cand=[(i,r) for i,r in enumerate(rows) if r['candidate']];w=np.ones(len(cand)) if weights is None else np.array([weights[i] for i,r in cand]);y=np.array([r['human_gt']=='Supported' for i,r in cand],int);p=np.array([mapping[r['proposition_id']]['probability'] for i,r in cand])
    mask=w>0;y=y[mask];p=p[mask];w=w[mask]
    if not len(y) or len(set(y))<2:return dict(AUROC=None,AP=None,R_prevalence=float(np.average(y,weights=w)) if len(y) else None)
    return dict(AUROC=float(roc_auc_score(y,p,sample_weight=w)),AP=float(average_precision_score(y,p,sample_weight=w)),R_prevalence=float(np.average(y,weights=w)))
def interval(v):
    x=[z for z in v if z is not None and np.isfinite(z)]
    return dict(ci95=np.percentile(x,[2.5,97.5]).tolist() if x else None,valid_draws=len(x),undefined_draws=len(v)-len(x))

def evaluate(run,scope,rows,mappings,config,features,progress):
    out=run/scope/'evaluation';out.mkdir(parents=True,exist_ok=False)
    methods=conditions(config);preds={n:pred_for(rows,mappings[n]) for n in methods}
    preds.update(U0=np.array([r['u0'] for r in rows]),U2=np.array([r['u2'] for r in rows]),SD=np.array([r['SD'] for r in rows]),repeat=np.array([r['repeat'] for r in rows]),trace=np.array([r['trace'] for r in rows]))
    c.csvwrite(out/'full_predictions.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],group=r['group'],author_type=r['author_type'],GT=r['human_gt'],candidate=r['candidate'],**{n:c.LABELS[int(p[i])] for n,p in preds.items()}) for i,r in enumerate(rows)])
    metrics={};metric_rows=[];patients=[];paired={};transitions=[];curves=[];matched={};boot={};leave_one=[];ranking_results={};ci_draws={};checks=[]
    groups=['pooled']+sorted({r['group'] for r in rows})
    pairs=comparisons(config)
    for group in groups:
        ix=np.array([i for i,r in enumerate(rows) if group=='pooled' or r['group']==group]);rr=[rows[i] for i in ix];pred={n:p[ix] for n,p in preds.items()};subjects=sorted({r['subject_id'] for r in rr});si=np.array([subjects.index(r['subject_id']) for r in rr]);times,gp=c.frontier.global_states(rr);refs={'global_lambda':gp,'SD':np.array([pred['U0'],pred['SD'],pred['U2']]),'repeat':np.array([pred['U0'],pred['repeat'],pred['U2']])};params={'global_lambda':times,'SD':['U0','historical_SD','U2'],'repeat':['U0','repeat','U2']}
        if all('SD_probability' in r for r in rr if r['candidate']):
            smap={r['proposition_id']:dict(probability=r['SD_probability'],keep=r['SD']==0) for r in rr if r['candidate']};params['SD'],refs['SD']=states(rr,smap)
        for n in methods:params[n],refs[n]=states(rr,mappings[n])
        for n,pp in refs.items():
            R,F=c.frontier.counts(rr,pp)
            for k,(r,f) in enumerate(zip(R,F)):curves.append(dict(group=group,reference=n,index=k,parameter=params[n][k],R=float(r),risk=float(f),formal_point=k==0 and n in methods))
        for author in ('all','human','llm'):
            ai=np.array([i for i,r in enumerate(rr) if author=='all' or r['author_type']==author]);ss=[rr[i] for i in ai]
            if not ss:continue
            for n,p in pred.items():
                key=f'{group}/{author}/{n}';m=point(ss,p[ai]);metrics[key]=m;metric_rows.append(dict(group=group,author=author,method=n,**m))
                checks.append(m['correct']-sum(c.LABELS[r['u0']]==r['human_gt'] for r in ss)==m['R']-m['H'])
            for base,new in pairs:
                key=f'{group}/{author}/{new}-minus-{base}';paired[key]=c.old.paired_compare(ss,c.old.prediction(ss,pred[base][ai]),c.old.prediction(ss,pred[new][ai]),iterations=config['bootstrap_iterations'])
        for sid in subjects:
            ii=np.array([i for i,r in enumerate(rr) if r['subject_id']==sid]);ss=[rr[i] for i in ii]
            for n,p in pred.items():patients.append(dict(group=group,subject_id=sid,method=n,**point(ss,p[ii])))
        for base,new in pairs+[('SD',n) for n in methods]+[('U2',n) for n in methods]:
            transitions.extend(dict(comparison=f'{new}-minus-{base}',**r) for r in transition(rr,pred[base],pred[new]) if group=='pooled')
        # All bootstrap resampling holds predictions fixed, matching 002 patient draw seeds.
        weights=np.array([np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects)) for seed in range(config['bootstrap_iterations'])],float)
        c.put(out/f'bootstrap_patients_{group}.json',dict(subjects=subjects,multiplicities=weights,seeds=f"0..{config['bootstrap_iterations']-1}",retrain=False))
        targets={n:c.frontier.counts(rr,pred[n]) for n in methods};bootstrap_draw={n:{ref:[] for ref in reference_names(n,refs)} for n in methods};rank_draw={n:{k:[] for k in ('AUROC','AP')} for n in methods}
        for n in methods:
            ranking_results[f'{group}/{n}']=ranking(rr,mappings[n]);matched[f'{group}/{n}']={}
            for ref in reference_names(n,refs):
                R,F=c.frontier.counts(rr,refs[ref]);tr,tf=targets[n];matched[f'{group}/{n}'][ref]=c.frontier.matched(F,R,float(tf[0]),float(tr[0]))
        for seed,multiplicity in enumerate(weights):
            w=multiplicity[si];counts={ref:c.frontier.counts(rr,pp,w) for ref,pp in refs.items()}
            for n in methods:
                tr,tf=c.frontier.counts(rr,pred[n],w)
                for ref in reference_names(n,refs):
                    R,F=counts[ref];v=c.frontier.matched(F,R,float(tf[0]),float(tr[0]));bootstrap_draw[n][ref].append({k:v[k] for k in ('R_gain_vs_global','R_gain_vs_mixture','risk_saved_vs_mixture')})
                z=ranking(rr,mappings[n],w)
                for k in rank_draw[n]:rank_draw[n][k].append(z[k])
        for n in methods:
            boot[f'{group}/{n}']={ref:{k:interval([v[k] for v in vv]) for k in ('R_gain_vs_global','R_gain_vs_mixture','risk_saved_vs_mixture')} for ref,vv in bootstrap_draw[n].items()}
            ranking_results[f'{group}/{n}']['bootstrap']={k:interval(v) for k,v in rank_draw[n].items()}
        ci_draws[group]=dict(matched=bootstrap_draw,ranking=rank_draw)
        for excluded in subjects:
            w=np.array([r['subject_id']!=excluded for r in rr],float)
            for n in methods:
                tr,tf=c.frontier.counts(rr,pred[n],w)
                for ref in reference_names(n,refs):
                    R,F=c.frontier.counts(rr,refs[ref],w);leave_one.append(dict(group=group,method=n,reference=ref,excluded_patient=excluded,**c.frontier.matched(F,R,float(tf[0]),float(tr[0]))))
        c.put(out/'metrics.json',metrics);c.put(out/'paired_bootstrap.json',paired);c.put(out/'matched_risk.json',matched);c.put(out/'matched_bootstrap.json',boot)
        progress(scope+' evaluation '+group+' saved')
    # Fixed 027 conflict sets, never used for fitting/selection.
    conflict_source=c.read(c.PREP/'conflicts.json');lookup={r['proposition_id']:i for i,r in enumerate(rows)};fs={r['proposition_id']:r['features'] for r in features};conflict=[];conflict_pairs=[]
    for group in ('025','026'):
        for gi,g in enumerate(conflict_source[group]['mixed_groups']):
            ids=[p for p in g['ids'] if p in lookup]
            if not ids:continue
            ii=[lookup[p] for p in ids];truth=[rows[i]['human_gt']=='Supported' for i in ii]
            for n,pred in preds.items():
                names=c.FEATURES[n.split('-')[0]] if n in methods else c.SCORE
                sig={tuple(fs[p][f] for f in names) for p in ids};conflict.append(dict(group=group,conflict_group=gi,method=n,n=len(ids),distinct_feature_vectors=len(sig),binary_errors=sum(bool(pred[i]==0)!=y for i,y in zip(ii,truth)),R=sum(pred[i]==0 and y for i,y in zip(ii,truth)),risk=sum(pred[i]==0 and not y for i,y in zip(ii,truth))))
                for ri in ii:
                    if rows[ri]['human_gt']!='Supported':continue
                    for fi in ii:
                        if rows[fi]['human_gt']=='Supported' or rows[fi]['subject_id']==rows[ri]['subject_id']:continue
                        conflict_pairs.append(dict(group=group,conflict_group=gi,method=n,R_id=rows[ri]['proposition_id'],risk_id=rows[fi]['proposition_id'],correctly_separated=bool(pred[ri]==0 and pred[fi]!=0),reverse_error=bool(pred[ri]!=0 and pred[fi]==0)))
    # Scalar conservation and independent LP spot checks of every formal global point.
    from scipy.optimize import linprog
    for group in groups:
        rr=[r for r in rows if group=='pooled' or r['group']==group];_,gp=c.frontier.global_states(rr);gr,gf=c.frontier.counts(rr,gp)
        for n in methods:
            tr,tf=c.frontier.counts(rr,pred_for(rr,mappings[n]));lp=linprog(-gr,A_ub=gf[None,:],b_ub=[tf[0]],A_eq=np.ones((1,len(gr))),b_eq=[1],bounds=(0,None),method='highs')
            c.require(lp.success and abs(float(tr[0]+lp.fun)-matched[f'{group}/{n}']['global_lambda']['R_gain_vs_mixture'])<1e-8,'Independent LP mismatch')
    c.require(all(checks),'Net R-H conservation failed')
    c.csvwrite(out/'metrics.csv',metric_rows);c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'transitions.csv',transitions);c.csvwrite(out/'curves.csv',curves);c.csvwrite(out/'leave_one_patient.csv',leave_one)
    c.put(out/'ranking.json',ranking_results);c.put(out/'bootstrap_draws.json',ci_draws);c.csvwrite(out/'conflicts.csv',conflict);c.csvwrite(out/'conflict_pairs.csv',conflict_pairs)
    c.put(out/'metadata.json',dict(scope=scope,bootstrap_retrains=False,bootstrap_meaning='已生成的OOF/迁移预测按患者cluster重抽；未重复训练，不包含完整训练不确定性',AUROC='R为正类时，随机R概率排在随机risk之前的概率，ties半分',AP='R为正类的平均精确率，应与R基率一起读',global_reference='同次D score全部非负λ状态直到全S；GT知情描述包络，不是可部署阈值',gate_curves='OOF概率全阈值仅作描述；正式工作点各折用训练侧阈值',historical_SD='025历史OOF+026冻结迁移，非029新比较基线',conflict_pairs_independent=False,all_conservation_checks=True,global_LP_verified=True,API_calls=0))
    flags={}
    for n in methods:
        a,e=n.split('-',1);refs=[f'A-{e}']+([f'B-{e}'] if a=='D' else [])
        refs=[r for r in refs if r!=n]
        if not refs:continue
        flags[n]=dict(rescue80=metrics[f'pooled/all/{n}']['rescue_retention']>=.8,matched_gain3=all(matched[f'pooled/{n}'][r]['R_gain_vs_mixture']>=3 for r in refs),CI_positive=all(boot[f'pooled/{n}'][r]['R_gain_vs_mixture']['ci95'][0]>0 for r in refs),cohort_directions={g:{r:matched[f'{g}/{n}'][r]['R_gain_vs_mixture'] for r in refs} for g in sorted({r['group'] for r in rows})},LOO_positive_counts={r:sum(z['R_gain_vs_mixture']>0 for z in leave_one if z['group']=='pooled' and z['method']==n and z['reference']==r) for r in refs})
    c.put(out/'interpretation_flags.json',dict(flags=flags,no_winner_selected=True,requires_later_scientific_review=True))
    c.put(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(out).as_posix():c.sha(p) for p in out.iterdir() if p.is_file()}))
