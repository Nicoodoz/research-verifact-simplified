"""Patient OOF separability and fixed operating point vs each model's full frontier."""
import argparse,socket
from collections import Counter
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
import common025 as c
import learning025 as learn
import frontier025 as f
def bootstrap(rows,globalpred,gatepred,prob):
    subjects=sorted(set(r['subject_id'] for r in rows));patient=np.array([subjects.index(r['subject_id']) for r in rows]);candidate=np.array([r['candidate'] for r in rows]);y=np.array([r['human_gt']=='Supported' for r in rows])[candidate]
    gains=[];auc=[]
    for seed in range(1000):
        pp=np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True);w=np.bincount(pp,minlength=len(subjects))[patient]
        gr,gf=f.counts(rows,globalpred,w);rr,ff=f.counts(rows,gatepred,w)
        v=f.matched(gf,gr,float(ff[0]),float(rr[0]));gains.append(v['R_gain_vs_mixture'])
        if prob is not None and len(set(y[w[candidate]>0]))==2:auc.append(roc_auc_score(y,prob,sample_weight=w[candidate]))
    return dict(mixture_R_gain_ci95=np.percentile(gains,[2.5,97.5]).tolist(),auc_ci95=np.percentile(auc,[2.5,97.5]).tolist() if auc else None,auc_valid_bootstrap_draws=len(auc),iterations=1000,conditional_on_fixed_OOF_predictions=True)
def compare_gate_curves(rows,gatepred,otherpred):
    r,fp=f.counts(rows,gatepred);orr,ofp=f.counts(rows,otherpred)
    point=f.matched(ofp,orr,float(fp[0]),float(r[0]));subjects=sorted(set(x['subject_id'] for x in rows));sid=np.array([subjects.index(x['subject_id']) for x in rows]);draws=[]
    for seed in range(1000):
        w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[sid]
        r,fp=f.counts(rows,gatepred,w);orr,ofp=f.counts(rows,otherpred,w);draws.append(f.matched(ofp,orr,float(fp[0]),float(r[0]))['R_gain_vs_mixture'])
    return dict(**point,mixture_gain_ci95=np.percentile(draws,[2.5,97.5]).tolist())
def run(out):
    c.require(not out.exists(),'Output exists')
    for path,h in c.read(c.OUT/'preparation_001/manifest.json')['sha256'].items():c.require(c.sha(c.ROOT/path)==h,'Frozen preparation changed')
    rr=c.jl(c.OUT/'preparation_001/rows.jsonl');groups={g:[r for r in rr if r['group']==g] for g in ('019','020_R0','020_R1','024_D','024_Q')}
    out.mkdir(parents=True);metrics=[];curves=[];globalcurves=[];summary={};paired={};audits=[];predrows=[];pats=[];feature_increment={}
    for group,rows in groups.items():
        z=np.array([c.logs(r['scores']) for r in rows]);u0=c.decode(z,0);u2=c.decode(z,2);c.require(all(r['u0']==u0[i] and r['u2']==u2[i] for i,r in enumerate(rows)),'U0/U2 mismatch')
        times,gpred=f.global_states(rows);gr,gf=f.counts(rows,gpred);candidate=np.array([r['candidate'] for r in rows]);y=np.array([r['human_gt']=='Supported' for r in rows])[candidate]
        variants={};gatecurves={};probabilities={};summary[group]={}
        train=groups['020_R0'] if group=='020_R1' else rows
        methods=('S','SE','SD','SED') if group.startswith('024') else ('S','SE')
        for method in methods:
            output,folds=learn.oof(train,rows,c.METHODS[method]);prob=np.array([output[r['proposition_id']]['prob'] for r in rows if r['candidate']]);pred=u0.copy()
            for i,r in enumerate(rows):
                if r['candidate'] and output[r['proposition_id']]['keep']:pred[i]=0
            variants[method]=pred;probabilities[method]=prob
            ts=sorted({0.,1.0000001,*prob.tolist()},reverse=True);cp=[]
            for t in ts:
                p=u0.copy();p[candidate]=np.where(prob>=t,0,u0[candidate]);cp.append(p)
                curves.append(dict(group=group,method=method,threshold=t,**c.point(rows,p)))
            gatecurves[method]=np.array(cp)
            audits.extend(dict(group=group,method=method,train_group='020_R0' if group=='020_R1' else group,**v) for v in folds)
            for r in rows:
                if r['candidate']:predrows.append(dict(group=group,method=method,proposition_id=r['proposition_id'],subject_id=r['subject_id'],human_gt=r['human_gt'],**output[r['proposition_id']]))
        if group.startswith('024'):variants['peer_U2']=np.where(candidate&np.array([r['peer_u2']==0 for r in rows]),0,u0)
        if group!='019' and group!='024_Q':
            for method in ('S','SE'):
                output,folds=learn.transfer(groups['019'],rows,c.METHODS[method]);name='transfer019_'+method;pred=u0.copy()
                for i,r in enumerate(rows):
                    if r['candidate'] and output[r['proposition_id']]['keep']:pred[i]=0
                variants[name]=pred;audits.extend(dict(group=group,method=name,train_group='019',**v) for v in folds)
        for name,pred in {'U0':u0,'U2':u2,**variants}.items():
            for author in ('all','human','llm'):
                ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author];sub=[rows[i] for i in ix]
                metrics.append(dict(group=group,method=name,author=author,**c.point(sub,pred[ix])))
                if name not in ('U0','U2'):paired[f'{group}/{name}/{author}/vsU2']=c.paired_compare(sub,c.prediction(sub,u2[ix]),c.prediction(sub,pred[ix]))
            for sid in sorted(set(r['subject_id'] for r in rows)):
                ix=[i for i,r in enumerate(rows) if r['subject_id']==sid];pats.append(dict(group=group,method=name,subject_id=sid,**c.point([rows[i] for i in ix],pred[ix])))
        for lam,pred in zip(times,gpred):
            for author in ('all','human','llm'):
                ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author];globalcurves.append(dict(group=group,author=author,lambda_value=lam,**c.point([rows[i] for i in ix],pred[ix])))
        for method,pred in variants.items():
            pt=c.point(rows,pred);matched=f.matched(gf,gr,pt['risk'],pt['R']);prob=probabilities.get(method)
            b=bootstrap(rows,gpred,pred,prob)
            loo=[]
            for sid in sorted(set(r['subject_id'] for r in rows)):
                w=np.array([r['subject_id']!=sid for r in rows]);tr,tf=f.counts(rows,gpred,w);ar,af=f.counts(rows,pred,w);loo.append(dict(excluded_patient=sid,**f.matched(tf,tr,float(af[0]),float(ar[0]))))
            summary[group][method]=dict(**pt,**matched,**b,AUROC=roc_auc_score(y,prob) if prob is not None and len(set(y))==2 else None,AUPRC=average_precision_score(y,prob) if prob is not None else None,candidate_R_prevalence=float(y.mean()),R_retention=pt['R']/sum(y),risk_retention=pt['risk']/sum(~y),leave_one_patient_out=loo)
        for method,other in [('SE','S'),('SED','SD')]:
            if method in variants and other in gatecurves:feature_increment[group+'/'+method+'-over-'+other]=compare_gate_curves(rows,variants[method],gatecurves[other])
        full=[dict(group=group,proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],**{name:c.LABELS[int(pred[i])] for name,pred in {'U0':u0,'U2':u2,**variants}.items()}) for i,r in enumerate(rows)]
        c.csvwrite(out/f'predictions_{group}.csv',full)
        print('Completed:',group,flush=True)
    c.csvwrite(out/'full_metrics.csv',metrics);c.csvwrite(out/'gate_curves.csv',curves);c.csvwrite(out/'global_lambda_curves.csv',globalcurves);c.csvwrite(out/'patients.csv',pats);c.csvwrite(out/'candidate_oof.csv',predrows)
    c.write(out/'summary.json',summary);c.write(out/'feature_increment.json',feature_increment);c.write(out/'paired_vs_U2.json',paired);c.write(out/'fit_audit.json',audits)
    decisions={}
    for method in ('S','SE','SD','SED'):
        s=summary['024_D'][method];am=[r for r in metrics if r['group']=='024_D' and r['method']==method and r['author']!='all']
        checks=dict(rescue80=s['R_retention']>=.8,risk75=s['risk_retention']<=.75,det_gain5=s['R_gain_vs_global']>=5,mix_gain3=s['R_gain_vs_mixture']>=3,mix_CI_positive=s['mixture_R_gain_ci95'][0]>0,loo8=sum(x['R_gain_vs_mixture']>0 for x in s['leave_one_patient_out'])>=8,authors_net_nonnegative=all(x['net']>=0 for x in am),historical_increment=any(summary[g].get(method,{}).get('R_gain_vs_mixture',-1)>0 for g in ('019','020_R0','020_R1')))
        checks={k:bool(v) for k,v in checks.items()}
        decisions[method]=dict(checks=checks,worth_further_development=all(checks.values()))
    c.write(out/'decision.json',dict(methods=decisions,evidence_increment={k:dict(worth_further_development=bool(v['R_gain_vs_mixture']>=3 and v['mixture_gain_ci95'][0]>0)) for k,v in feature_increment.items() if k.startswith('024_D/')},lambda_unchanged=2,new_API_calls=0))
    deps=[c.OUT/'preparation_001/manifest.json',c.OUT/'protocol_001.md']+list(c.TASK.glob('*.py'))
    c.write(out/'manifest.json',dict(dependencies={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
if __name__=='__main__':
    socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('025 network prohibited'))
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();out=Path(a.output).resolve() if a.output else c.OUT/'analysis_002'
    c.require(out==c.OUT/'analysis_002' or out.is_relative_to(c.ROOT/'outputs/replays'),'Unsafe output')
    run(out)
