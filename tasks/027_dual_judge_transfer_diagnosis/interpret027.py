"""Descriptive operating-point and fusion checks; no fitting/threshold selection."""
import math,collections
import numpy as np
from sklearn.metrics import roc_auc_score
import common027 as x
import analyze027_saved as source
def run():
    x.offline();a=x.OUT/'analysis_002';out=x.OUT/'interpretation_001';groups,items,gate=source.load();rows=x.c.csvrows(a/'curves.csv');summary={}
    for group in ('025','026'):
        rr=[r for r in items if r['group']==group];y=np.array([r['kind']=='R' for r in rr]);summary[group]={}
        for ptype in ('SD','final_gate_probability'):
            pp=np.array([r[ptype] for r in rr]);keep=pp>=gate['threshold'];summary[group][ptype]=dict(mean_probability=float(pp.mean()),R_mean=float(pp[y].mean()),risk_mean=float(pp[~y].mean()),Brier=float(np.mean((pp-y)**2)),AUC=float(roc_auc_score(y,pp)),at_fixed026_threshold=dict(R=int(sum(keep&y)),risk=int(sum(keep&~y))),in_sample=group=='025' and ptype=='final_gate_probability')
        high=[r for r in rows if r['group']==group and r['method']=='SD' and float(r['retention'])>=.8];summary[group]['high_rescue_SD_diagnostic_only']=dict(points=len(high),mixed_gain_min=min(float(r['gain_vs_global_mixture']) for r in high),mixed_gain_max=max(float(r['gain_vs_global_mixture']) for r in high),points_positive=sum(float(r['gain_vs_global_mixture'])>0 for r in high),points_gain_atleast3=sum(float(r['gain_vs_global_mixture'])>=3 for r in high))
        bands=collections.defaultdict(lambda:collections.Counter())
        for r in rr:
            key=('Q_U2_S' if r['features']['peer_u2_s'] else 'Q_U2_nonS')+'/'+('gate_keep' if r['keep'] else 'gate_reject');bands[key][r['kind']]+=1
        summary[group]['peer_gate_cross_table']={k:dict(v) for k,v in bands.items()}
        summary[group]['D_raw_S_distribution']=dict(collections.Counter(r['D_scores']['Supported'] for r in rr))
        summary[group]['Q_raw_S_distribution']=dict(collections.Counter(r['Q_scores']['Supported'] for r in rr))
    rr=groups['026'][1];reject=[r['SD'] for r in rr if not r['keep']];accept=[r['SD'] for r in rr if r['keep']]
    summary['frozen026_workpoint']=dict(threshold=gate['threshold'],identical_decisions_interval=dict(lower_exclusive=max(reject),upper_inclusive=min(accept)),formula='p>=threshold',not_new_selected_threshold=True)
    summary['coef']=[dict(feature=k,standardized_coef=b,raw_linear_weight=b/s) for k,b,s in zip(gate['features'],gate['coef'],gate['scale'])]
    # Mechanical contribution decomposition, not Shapley or causal feature importance.
    contrib=[]
    for r in items:
        terms=r['final_gate_terms'];contrib.append(dict(group=r['group'],proposition_id=r['proposition_id'],subject_id=r['subject_id'],kind=r['kind'],D_centered_logit=sum(terms[:7]),Q_centered_logit=sum(terms[7:]),intercept=gate['intercept'],final_probability=r['final_gate_probability']))
    # Patient composition is different: report explicit fixed author standardization descriptively.
    comp=x.c.csvrows(a/'composition.csv');get=lambda g,scope:next(r for r in comp if r['group']==g and r['scope']==scope)
    hnew=float(get('026','human')['n'])/52;old_h=get('025','human');old_l=get('025','llm')
    summary['composition_standardization']=dict(old_R_rate=76/103,new_R_rate=34/52,old_with_new_author_weights=hnew*float(old_h['R'])/float(old_h['n'])+(1-hnew)*float(old_l['R'])/float(old_l['n']),causal_interpretation=False)
    # Direct paired AUC SD versus Q_s and high-rescue minimum risk differences under resampling.
    paired={}
    for group,(full,its) in groups.items():
        ids=sorted(set(r['subject_id'] for r in full));ix=np.array([ids.index(r['subject_id']) for r in its]);yy=np.array([r['kind']=='R' for r in its]);sv=np.array([r['SD'] for r in its]);qv=np.array([r['Q_s'] for r in its]);diff=[]
        for seed in range(1000):
            w=np.bincount(np.random.RandomState(seed).choice(len(ids),len(ids),replace=True),minlength=len(ids))[ix]
            if len(set(yy[w>0]))==2:diff.append(float(roc_auc_score(yy,sv,sample_weight=w)-roc_auc_score(yy,qv,sample_weight=w)))
        paired[group]=dict(SD_minus_Qs_AUC=float(roc_auc_score(yy,sv)-roc_auc_score(yy,qv)),ci95=np.percentile(diff,[2.5,97.5]).tolist(),valid_draws=len(diff))
    summary['SD_vs_Q_AUC']=paired
    out.mkdir(exist_ok=False);x.put(out/'summary.json',summary);x.c.csvwrite(out/'linear_contributions.csv',contrib)
    x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in [a/'manifest.json',x.TASK/'interpret027.py',x.TASK/'analyze027_saved.py']},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()}))
    print(x.c.canonical(summary))
if __name__=='__main__':run()
