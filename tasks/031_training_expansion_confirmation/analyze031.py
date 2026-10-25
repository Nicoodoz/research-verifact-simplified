"""Only after eight GT-blind predictions are sealed: unified confirmation evaluation."""
import argparse,os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from scipy.optimize import linprog
import common031 as c
from fit_predict031 import scoped_gt
from verifact_research.evaluation.metrics import patient_bootstrap,METRICS

METHODS=[era+'_'+m for era in ('before','after') for m in ('A','B','C','D')]
PRIMARY=[('after_A','after_C'),('after_B','after_D')]
PAIRS=PRIMARY+[('after_A','after_B'),('after_C','after_D')]+[('before_'+m,'after_'+m) for m in 'ABCD']+[('before_A','before_C'),('before_B','before_D')]
def states(rows,source,name):
    probs=[source[r['proposition_id']]['methods'][name]['probability'] for r in rows if 'probability' in source[r['proposition_id']]['methods'][name]];thresholds=[float(np.nextafter(max(probs),np.inf)),*sorted(set(probs),reverse=True)] if probs else [1.];formal=np.array([source[r['proposition_id']]['methods'][name]['prediction'] for r in rows]);pp=[formal]
    for t in thresholds:pp.append(np.array([0 if r['candidate'] and source[r['proposition_id']]['methods'][name].get('probability',-1)>=t else r['u0'] for r in rows]))
    return [None,*thresholds],np.array(pp)
def ci(draws,primary=False):
    return dict(ci95=np.percentile(draws,[2.5,97.5]).tolist(),ci97_5_Bonferroni2=np.percentile(draws,[1.25,98.75]).tolist() if primary else None)
def run(destination):
    out=c.OUT/destination;c.require(not out.exists(),'No overwrite analysis');inf=c.OUT/'inference_001';manifest=c.read(inf/'manifest.json');path=inf/'confirmation_predictions_blind.jsonl';c.require(c.sha(path)==manifest['predictions_sha256'],'Blind predictions changed');c.require(len(manifest['model_sha256'])==8,'Eight models not sealed')
    for p,h in manifest['model_sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Model changed before evaluation')
    src=c.lines(path);lookup={r['proposition_id']:r for r in src};gt=scoped_gt(set(lookup));out.mkdir();c.put(out/'GT_connection.json',dict(connected_utc=c.now(),prediction_freeze_created=manifest['created_utc'],prediction_sha256=c.sha(path),after_all_eight_models=True,confirmation_only=True));c.csvwrite(out/'confirmation_GT.csv',[dict(proposition_id=p,human_gt=g) for p,g in gt.items()])
    rows=[dict(r,human_gt=gt[r['proposition_id']]) for r in src if r['u0'] is not None];missing=[r['proposition_id'] for r in src if r['u0'] is None];c.require(rows,'No evaluable main scoring')
    preds={name:np.array([r['methods'][name]['prediction'] for r in rows]) for name in METHODS};preds.update(U0=np.array([r['u0'] for r in rows]),U2=np.array([r['u2'] for r in rows]));metrics={};pairs={};patients=[];transitions=[];curves=[];matched={};draws={};loo=[]
    # Auxiliary failures remain U0 in all full evaluable-score rows; never successful-only selection.
    for author in ('all','human','llm'):
        ix=np.array([i for i,r in enumerate(rows) if author=='all' or r['author_type']==author]);ss=[rows[i] for i in ix]
        if not ss:continue
        for name,p in preds.items():
            m=c.base.old.point(ss,p[ix]);Rtotal=sum(r['candidate'] and r['human_gt']=='Supported' for r in ss);m.update(rescue_retention=m['R']/Rtotal if Rtotal else None,R_available=Rtotal,full_intended_n=sum(author=='all' or r['author_type']==author for r in src));m['PA_full_missing_as_error']=m['correct']/m['full_intended_n'];metrics[author+'/'+name]=m
        for base,new in PAIRS:pairs[author+'/'+new+'-minus-'+base]=c.base.old.paired_compare(ss,c.base.old.prediction(ss,preds[base][ix]),c.base.old.prediction(ss,preds[new][ix]))
    for sid in sorted({r['subject_id'] for r in rows}):
        ix=np.array([i for i,r in enumerate(rows) if r['subject_id']==sid]);ss=[rows[i] for i in ix]
        for name,p in preds.items():patients.append(dict(subject_id=sid,method=name,**c.base.old.point(ss,p[ix])))
    import evaluate029 as ev
    for base,new in PAIRS:transitions.extend(dict(comparison=new+'-minus-'+base,**r) for r in ev.transition([dict(r,group='confirmation') for r in rows],preds[base],preds[new]))
    times,gp=c.base.frontier.global_states(rows);refs={'global_lambda':gp};parameters={'global_lambda':times}
    for name in METHODS:parameters[name],refs[name]=states(rows,lookup,name)
    comparisons=[('after_C','after_A'),('after_D','after_B'),('after_B','after_A'),('after_D','after_C'),('before_C','before_A'),('before_D','before_B')]+[(n,'global_lambda') for n in METHODS]
    for name,pp in refs.items():
        R,F=c.base.frontier.counts(rows,pp)
        for i,(r,f) in enumerate(zip(R,F)):curves.append(dict(reference=name,index=i,parameter=parameters[name][i],R=float(r),risk=float(f),formal_point=name in METHODS and i==0))
    subjects=sorted({r['subject_id'] for r in rows});si=np.array([subjects.index(r['subject_id']) for r in rows]);weights=np.array([np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects)) for seed in range(1000)],float)
    all_counts={}
    truth=np.array([r['human_gt']=='Supported' for r in rows]);u0=np.array([r['u0'] for r in rows])
    for ref,pp in refs.items():
        changed=(pp==0)&(u0[None,:]!=0);rr=np.array([changed[:,si==k]@truth[si==k].astype(float) for k in range(len(subjects))]);ff=np.array([changed[:,si==k]@(~truth[si==k]).astype(float) for k in range(len(subjects))]);all_counts[ref]=(weights@rr,weights@ff)
    for target,reference in comparisons:
        R,F=c.base.frontier.counts(rows,refs[reference]);tr,tf=c.base.frontier.counts(rows,preds[target]);key=target+'-vs-'+reference;value=c.base.frontier.matched(F,R,float(tf[0]),float(tr[0]));lp=linprog(-R,A_ub=F[None,:],b_ub=[tf[0]],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');c.require(lp.success and abs(tr[0]+lp.fun-value['R_gain_vs_mixture'])<1e-8,'Matched LP mismatch');d=[]
        br,bf=all_counts[reference];targetr,targetf=all_counts[target]
        for i in range(1000):d.append(c.base.frontier.matched(bf[i],br[i],targetf[i,0],targetr[i,0])['R_gain_vs_mixture'])
        matched[key]=dict(**value,**ci(d,(reference,target) in PRIMARY));draws[key]=d
        for sid in subjects:
            w=np.array([r['subject_id']!=sid for r in rows],float);R,F=c.base.frontier.counts(rows,refs[reference],w);tr,tf=c.base.frontier.counts(rows,preds[target],w);loo.append(dict(comparison=key,excluded_patient=sid,**c.base.frontier.matched(F,R,float(tf[0]),float(tr[0]))))
    # Paired information-gain difference before/after; test weights shared, no retraining.
    encoded=np.array([c.LABELS.index(r['human_gt']) for r in rows]);metricdraw={n:patient_bootstrap(3*encoded+p,[r['subject_id'] for r in rows],1000) for n,p in preds.items()};did={}
    for plus,base in [('C','A'),('D','B')]:
        d=(metricdraw['after_'+plus]-metricdraw['after_'+base])-(metricdraw['before_'+plus]-metricdraw['before_'+base]);key=f'({plus}-{base})_after_minus_before';did[key]={name:ci(d[:,i]) for i,name in enumerate(METRICS)};md=np.array(draws[f'after_{plus}-vs-after_{base}'])-np.array(draws[f'before_{plus}-vs-before_{base}']);did[key]['matched_gain_difference']=dict(**ci(md),note='各自训练工作点的同risk增量之差；工作点risk可不同，非固定共同risk因果效应')
    c.put(out/'coverage.json',dict(intended_n=len(src),score_valid_n=len(rows),score_missing_ids=missing,complete_main_score=not missing,auxiliary_fallback_counts={n:sum(r['methods'][n]['status']=='fallback_U0_missing_aux' for r in src) for n in METHODS},prediction_scope='full confirmation if all score valid; otherwise common main-score-valid with full-denominator PA bounds, explicitly incomplete'))
    c.put(out/'metrics.json',metrics);c.csvwrite(out/'metrics.csv',[dict(author=k.split('/')[0],method=k.split('/')[1],**v) for k,v in metrics.items()]);c.put(out/'paired.json',pairs);c.put(out/'matched.json',matched);c.put(out/'bootstrap_draws.json',draws);c.put(out/'information_difference.json',did);c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'transitions.csv',transitions);c.csvwrite(out/'curves.csv',curves);c.csvwrite(out/'leave_one_patient.csv',loo)
    c.csvwrite(out/'predictions.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=gt[r['proposition_id']],U0=c.LABELS[r['u0']] if r['u0'] is not None else '',U2=c.LABELS[r['u2']] if r['u2'] is not None else '',**{n:c.LABELS[r['methods'][n]['prediction']] if r['methods'][n]['prediction'] is not None else '' for n in METHODS}) for r in src]);c.put(out/'metadata.json',dict(bootstrap='1000 paired patient draws, fixed eight model predictions, no refit',primary_comparisons=PRIMARY,multiplicity='95% plus97.5% Bonferroni2 for two main matched-risk contrasts; auxiliary comparisons descriptive',no_new_lambda_or_threshold=True,confirmation_GT_join_after_prediction_freeze=True,missing_not_imputed=True))
    c.put(out/'manifest.json',dict(created_utc=c.now(),source_prediction_sha256=c.sha(path),outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('Confirmation evaluation complete',len(rows),'/',len(src),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='analysis_001');args=p.parse_args();run(args.output)
