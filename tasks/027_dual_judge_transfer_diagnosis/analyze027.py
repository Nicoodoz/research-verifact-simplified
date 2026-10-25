"""Offline curve/shift/conflict diagnosis; uses frozen predictions, never fits."""
import argparse,collections,math
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
import common027 as x
c=x.c
METHODS=['D_s','D_margin','Q_s','Q_margin','SD']
TARGETS=[.8,.85,.9,.95,1.]

def sources():
    names=['outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl','outputs/025_lambda_flip_risk_separability/analysis_003/candidate_oof.csv','outputs/025_lambda_flip_risk_separability/analysis_003/fit_audit.json','outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl','outputs/026_frozen_sd_patient_transfer/analysis_001/gate_inference.json','outputs/026_frozen_sd_patient_transfer/analysis_001/predictions.csv','outputs/026_frozen_sd_patient_transfer/preparation_001/cohort.csv','outputs/026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl','outputs/026_frozen_sd_patient_transfer/gate_freeze/gate.json','outputs/026_frozen_sd_patient_transfer/analysis_001/global_frontier.csv','outputs/025_lambda_flip_risk_separability/analysis_003/global_lambda_curves.csv','outputs/025_lambda_flip_risk_separability/report.md','outputs/026_frozen_sd_patient_transfer/report.md','reviews/025_lambda_flip_risk_separability.md','reviews/026_frozen_sd_patient_transfer.md']
    return [x.ROOT/n for n in names]

def load():
    base=x.ROOT/'outputs';rr=c.jl(base/'025_lambda_flip_risk_separability/preparation_001/rows.jsonl');old=[r for r in rr if r['group']=='024_D'];qold={r['proposition_id']:r for r in rr if r['group']=='024_Q'}
    oof={r['proposition_id']:r for r in c.csvrows(base/'025_lambda_flip_risk_separability/analysis_003/candidate_oof.csv') if r['group']=='024_D' and r['method']=='SD'}
    norms=c.jl(base/'026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl');nn={(r['proposition_id'],r['model_key'],r['arm']):r for r in norms};new=[]
    for r in c.csvrows(base/'026_frozen_sd_patient_transfer/preparation_001/cohort.csv'):
        ds=nn[r['proposition_id'],'deepseek','S']['scores'];u0=int(c.decode(c.logs(ds),0));u2=int(c.decode(c.logs(ds),2));new.append(dict(r,scores=ds,u0=u0,u2=u2,candidate=u0!=0 and u2==0))
    gate=x.read(base/'026_frozen_sd_patient_transfer/gate_freeze/gate.json');c.require(set(gate['training_patients']).isdisjoint(r['subject_id'] for r in new),'Patient overlap')
    inference={r['proposition_id']:r for r in x.read(base/'026_frozen_sd_patient_transfer/analysis_001/gate_inference.json')};groups={};candidates=[]
    for group,rows in [('025',old),('026',new)]:
        items=[]
        for r in rows:
            if not r['candidate']:continue
            pid=r['proposition_id'];qs=qold[pid]['scores'] if group=='025' else nn[pid,'qwen','S']['scores'];f=x.features(r['scores'],qs);fp,terms=x.probability(gate,f)
            if group=='025':
                c.require(all(abs(f[k]-r['features'][k])<1e-12 for k in gate['features']),'025 feature mismatch');prob=float(oof[pid]['prob']);threshold=float(oof[pid]['threshold']);keep=oof[pid]['keep']=='True'
            else:
                c.require(abs(fp-inference[pid]['prob'])<1e-12,'026 frozen inference differs');prob=fp;threshold=gate['threshold'];keep=prob>=threshold
            kind='R' if r['human_gt']==x.LABELS[0] else 'H' if x.LABELS[r['u0']]==r['human_gt'] else 'W'
            item=dict(group=group,proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],kind=kind,u0=r['u0'],D_scores=r['scores'],Q_scores=qs,features=f,D_s=f['s'],D_margin=f['s_margin'],Q_s=f['peer_s'],Q_margin=f['peer_margin'],SD=prob,threshold=threshold,keep=keep,final_gate_probability=fp,final_gate_threshold=gate['threshold'],final_gate_terms=terms,probability_scope='patient_OOF' if group=='025' else 'frozen_transfer')
            items.append(item);candidates.append(item)
        groups[group]=(rows,items)
    return groups,candidates,gate

def auc(y,s,w=None):
    w=np.ones(len(y)) if w is None else w
    return float(roc_auc_score(y,s,sample_weight=w)) if len(set(y[w>0]))==2 else None

def conflicts(items):
    groups=collections.defaultdict(list)
    for r in items:groups[tuple(r['features'][k] for k in c.METHODS['SD'])].append(r)
    mixed=[];counts=[]
    for key,rs in groups.items():
        cc=collections.Counter(r['kind'] for r in rs);counts.append((cc['R'],cc['H']+cc['W']))
        if cc['R'] and cc['H']+cc['W']:mixed.append(dict(ids=[r['proposition_id'] for r in rs],subjects=sorted(set(r['subject_id'] for r in rs)),counts=dict(cc),features=dict(zip(c.METHODS['SD'],key))))
    dp={0:0}
    for R,F in counts:
        nxt=dict(dp)
        for f,r in dp.items():nxt[f+F]=max(nxt.get(f+F,-1),r+R)
        dp=nxt
    raw=np.array([[r[model][lab] for model in ('D_scores','Q_scores') for lab in x.LABELS] for r in items]);near=[]
    for i in range(len(items)):
        for j in range(i):
            distance=float(max(abs(raw[i]-raw[j])))
            if distance<=10:near.append(dict(id1=items[j]['proposition_id'],id2=items[i]['proposition_id'],max_score_difference=distance,opposite_R_risk=(items[i]['kind']=='R')!=(items[j]['kind']=='R'),different_patient=items[i]['subject_id']!=items[j]['subject_id']))
    R=sum(r['kind']=='R' for r in items)
    return dict(n=len(items),unique_exact_groups=len(groups),mixed_groups=mixed,mixed_claims=sum(len(g['ids']) for g in mixed),unavoidable_binary_errors=sum(min(r,f) for r,f in counts),oracle_group_accuracy=sum(max(r,f) for r,f in counts)/len(items),oracle_curve=[dict(risk=f,R=r) for f,r in sorted(dp.items())],oracle_min_risk_at_retention={str(t):min(f for f,r in dp.items() if r>=math.ceil(t*R-1e-10)) for t in TARGETS},near_pairs=near,near_summary={str(t):dict(pairs=sum(p['max_score_difference']<=t for p in near),opposite_pairs=sum(p['max_score_difference']<=t and p['opposite_R_risk'] for p in near),cross_patient_opposite=sum(p['max_score_difference']<=t and p['opposite_R_risk'] and p['different_patient'] for p in near)) for t in (0,5,10)})

def run(out):
    x.offline();c.require(not out.exists(),'New output required');groups,allitems,gate=load();out.mkdir(parents=True)
    x.put(out/'candidates.json',allitems);curves=[];global_curves=[];ranking=[];anchors=[];distribution=[];composition=[];patients=[];uncertainty={};conf={};reliability=[]
    for group,(rows,items) in groups.items():
        byid={r['proposition_id']:r for r in items};y=np.array([r['kind']=='R' for r in items]);sid=[r['subject_id'] for r in items];subjects=sorted(set(r['subject_id'] for r in rows));sidx=np.array([subjects.index(v) for v in sid]);R=int(sum(y));F=int(sum(~y));u0=np.array([r['u0'] for r in rows]);candix=[i for i,r in enumerate(rows) if r['candidate']]
        times,gp=x.frontier.global_states(rows);gr,gf=x.frontier.counts(rows,gp)
        for t,p in zip(times,gp):global_curves.append(dict(group=group,lambda_value=t,**c.point(rows,p)))
        states={};values={};counts={}
        for method in METHODS:
            s=np.array([r[method] for r in items]);ts,pp=x.ranking_states(s);res=pp@y.astype(float);risk=pp@(~y).astype(float);states[method]=(ts,pp);values[method]=s;counts[method]=(res,risk)
            for t,keep,rr,ff in zip(ts,pp,res,risk):
                p=u0.copy();p[candix]=np.where(keep,0,p[candix]);mm=c.point(rows,p);globalm=x.frontier.matched(gf,gr,ff,rr)
                curves.append(dict(group=group,method=method,threshold=t,retention=rr/R,**mm,global_mixture_R_at_risk=globalm['global_mixture_R_at_risk'],gain_vs_global_mixture=globalm['R_gain_vs_mixture']))
            for target in TARGETS:
                i=x.first_target(res,risk,math.ceil(target*R-1e-10));g=x.frontier.matched(gf,gr,risk[i],res[i]);local=x.frontier.matched(*counts.get('D_margin',(res,risk))[::-1],risk[i],res[i]) if 'D_margin' in counts else None
                anchors.append(dict(group=group,method=method,target_retention=target,target_R=math.ceil(target*R-1e-10),actual_R=int(res[i]),risk=int(risk[i]),diagnostic_threshold=ts[i],gain_vs_global_mixture=g['R_gain_vs_mixture']))
            for scope in ['all','human','llm']+subjects:
                ix=np.array([scope=='all' or r['author_type']==scope or r['subject_id']==scope for r in items]);yy=y[ix];ss=s[ix]
                if not len(yy):continue
                ranking.append(dict(group=group,scope=scope,method=method,n=int(sum(ix)),R=int(sum(yy)),AUROC=auc(yy,ss),AP=float(average_precision_score(yy,ss)) if sum(yy) else None,prevalence=float(np.mean(yy)),within_patient_AUROC=x.patient_auc(yy,ss,np.ones(sum(ix)),[v for v,k in zip(sid,ix) if k])))
        # Candidate-local paired comparison at preregistered high-retention anchors.
        for a in [r for r in anchors if r['group']==group]:
            dr,df=counts['D_margin'];i=x.first_target(dr,df,a['target_R']);a['risk_saved_vs_D_margin']=int(df[i])-a['risk'];a['D_margin_actual_R']=int(dr[i]);a['local_D_mixture_gain']=x.frontier.matched(df,dr,a['risk'],a['actual_R'])['R_gain_vs_mixture']
        draws={m:[] for m in METHODS};diffdraw={m:[] for m in ('Q_s','Q_margin','SD')};riskdraw={(m,t):[] for m in ('Q_s','Q_margin','SD') for t in TARGETS}
        for seed in range(1000):
            w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[sidx].astype(float);wy=w*y;wf=w*(~y);av={m:auc(y,values[m],w) for m in METHODS}
            for m in METHODS:
                if av[m] is not None:draws[m].append(av[m])
            for m in diffdraw:
                if av[m] is not None and av['D_margin'] is not None:diffdraw[m].append(av[m]-av['D_margin'])
            if sum(wy):
                rc={m:(p@wy,p@wf) for m,(_,p) in states.items()}
                for target in TARGETS:
                    targetR=math.ceil(target*sum(wy)-1e-10);dr,df=rc['D_margin'];di=x.first_target(dr,df,targetR)
                    for m in ('Q_s','Q_margin','SD'):
                        r,f=rc[m];i=x.first_target(r,f,targetR);riskdraw[m,target].append(float(df[di]-f[i]))
        uncertainty[group]=dict(AUC={m:dict(ci95=np.percentile(v,[2.5,97.5]).tolist(),valid_draws=len(v)) for m,v in draws.items()},AUC_difference_vs_D_margin={m:np.percentile(v,[2.5,97.5]).tolist() for m,v in diffdraw.items()},risk_saved_vs_D_margin={m+'/'+str(t):np.percentile(v,[2.5,97.5]).tolist() for (m,t),v in riskdraw.items()},cluster_patients=subjects,iterations=1000,no_refit=True)
        conf[group]=conflicts(items)
        for scope in ['all','human','llm']+subjects:
            its=[r for r in items if scope=='all' or r['author_type']==scope or r['subject_id']==scope]
            composition.append(dict(group=group,scope=scope,n=len(its),**{k:sum(r['kind']==k for r in its) for k in ('R','H','W')},kept_R=sum(r['keep'] and r['kind']=='R' for r in its),kept_H=sum(r['keep'] and r['kind']=='H' for r in its),kept_W=sum(r['keep'] and r['kind']=='W' for r in its)))
            for kind in ('all','R','H','W','risk'):
                subset=[r for r in its if kind=='all' or r['kind']==kind or (kind=='risk' and r['kind']!='R')]
                if not subset:continue
                for feature in c.METHODS['SD']+['SD','final_gate_probability']:
                    v=[r[feature] if feature in r else r['features'][feature] for r in subset];distribution.append(dict(group=group,scope=scope,kind=kind,feature=feature,n=len(v),mean=float(np.mean(v)),q10=float(np.quantile(v,.1)),median=float(np.median(v)),q90=float(np.quantile(v,.9))))
        for probtype in ('SD','final_gate_probability'):
            p=np.array([r[probtype] for r in items]);reliability.append(dict(group=group,probability=probtype,bin='all',n=len(y),mean_probability=float(p.mean()),R_rate=float(y.mean()),Brier=float(np.mean((p-y)**2)),training_in_sample=group=='025' and probtype=='final_gate_probability'))
            edges=[0,.2,.4,.6,.8,1.0000001]
            for lo,hi in zip(edges[:-1],edges[1:]):
                ix=(p>=lo)&(p<hi)
                if sum(ix):reliability.append(dict(group=group,probability=probtype,bin=f'[{lo},{hi})',n=int(sum(ix)),mean_probability=float(p[ix].mean()),R_rate=float(y[ix].mean()),Brier=float(np.mean((p[ix]-y[ix])**2)),training_in_sample=group=='025' and probtype=='final_gate_probability'))
    conf['pooled_descriptive']=conflicts(allitems)
    # Same feature oracle across all observed candidates; no training/deployment claim.
    x.put(out/'conflicts.json',conf);x.put(out/'uncertainty.json',uncertainty)
    for name,rr in [('ranking',ranking),('curves',curves),('global_curves',global_curves),('high_rescue',anchors),('composition',composition),('distributions',distribution),('reliability',reliability)]:c.csvwrite(out/(name+'.csv'),rr)
    # All 17 errors, all six rejected risks; up to eight kept-R controls selected without text inspection.
    its=groups['026'][1];selected=[r for r in its if (r['keep'] and r['kind']!='R') or (not r['keep'])];controls={}
    for r in its:
        if r['keep'] and r['kind']=='R':controls.setdefault((r['subject_id'],r['author_type']),[]).append(r)
    choices=[min(v,key=lambda r:c.digest(r['proposition_id'])) for v in controls.values()];choices.sort(key=lambda r:c.digest(r['subject_id']+'/'+r['author_type']));selected+=choices[:8]
    x.put(out/'case_selection.json',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],kind=r['kind'],keep=r['keep'],role='error' if r['keep']!=(r['kind']=='R') else 'control',selection_rule='all_gate_errors/all_rejected_risk/stratified_hash_kept_R') for r in selected])
    x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in sources()+[x.OUT/'protocol_001.md',x.TASK/'common027.py',Path(__file__)]},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()},API_calls=0,new_training=0,reserved_access=False))
    print('027 offline diagnostics complete:',len(allitems),'candidates;',len(selected),'deep-read cases')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();out=Path(a.output).resolve() if a.output else x.OUT/'analysis_001';c.require(out==x.OUT/'analysis_001' or out.is_relative_to(x.ROOT/'outputs/replays'),'Unsafe output');run(out)
