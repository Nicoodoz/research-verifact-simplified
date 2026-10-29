"""CPU result checks and aggregate strata; no clinical text is published."""
from collections import Counter
from pathlib import Path
import sys,numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'))
import common109 as c
from analyze109 import metrics
from sklearn.metrics import matthews_corrcoef,accuracy_score
b=ROOT/'.local_models/109_boundary_replay/gpu_bundle';w=ROOT/'.local_models/109_boundary_replay/gpu_evidence/results'
base=c.rows(b/'data/baseline107.jsonl');new={r['id']:r for r in c.rows(w/'evaluation/predictions.jsonl')}
keys={r['id']:r for r in c.rows(ROOT/'.local_models/107_support_aux/gpu_bundle_5090_run/frozen/eval_keys.jsonl')}
core=c.read(ROOT/'outputs/109_boundary_replay/comparison.json');out={}
def risks(rows):
    subjects=sorted({str(r['sid']) for r in rows});by={s:[r for r in rows if str(r['sid'])==s] for s in subjects}
    def value(part,kind,arm):
        eligible=[r for r in part if (r['GT']!='Supported' if kind=='false_S_rate' else r['GT']==kind)]
        return sum(r['pred'][arm]==('Supported' if kind=='false_S_rate' else kind) for r in eligible)/len(eligible) if eligible else None
    result={}
    for kind in ['false_S_rate',*c.LABELS]:
        a=value(rows,kind,'baseline');d=value(rows,kind,'candidate');draws=[]
        if a is not None and len(subjects)>1:
            for seed in range(1000):
                sample=[r for i in np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True) for r in by[subjects[i]]]
                x=value(sample,kind,'baseline');y=value(sample,kind,'candidate')
                if x is not None:draws.append(y-x)
        result[kind]=dict(delta=None if a is None else d-a,ci95=np.percentile(draws,[2.5,97.5]).tolist() if draws else None,valid_draws=len(draws))
    return result
for panel in ['natural','pressure']:
    rows=[]
    for r in base:
        if r['panel']!=panel or not r['parsed']['valid'] or not new[r['id']]['parsed']['valid']:continue
        key=keys[r['id']]
        assert r['GT']==key['GT'] and str(r['sid'])==str(key['sid']) and r['panel']==key['panel']
        rows.append(dict(r,pred={'baseline':r['parsed']['verdict'],'candidate':new[r['id']]['parsed']['verdict'],'paper_r1':key['paper_r1']}))
    for arm,field in [('baseline','baseline_common'),('candidate','candidate_common')]:
        actual=core['panels'][panel][field];truth=[r['GT'] for r in rows];pred=[r['pred'][arm] for r in rows]
        assert abs(matthews_corrcoef(truth,pred)-actual['mcc'])<1e-12
        assert abs(accuracy_score(truth,pred)-actual['percent_agreement'])<1e-12
        assert sum(r['GT']!='Supported' and r['pred'][arm]=='Supported' for r in rows)==actual['false_S']
    patients=[]
    for number,sid in enumerate(sorted({str(r['sid']) for r in rows}),1):
        part=[r for r in rows if str(r['sid'])==sid]
        patients.append(dict(patient_index=number,N=len(part),correct_delta=sum(int(r['pred']['candidate']==r['GT'])-int(r['pred']['baseline']==r['GT']) for r in part),
            false_S_delta=sum(int(r['GT']!='Supported' and r['pred']['candidate']=='Supported')-int(r['GT']!='Supported' and r['pred']['baseline']=='Supported') for r in part)))
    transitions={g:{before:{after:sum(r['GT']==g and r['pred']['baseline']==before and r['pred']['candidate']==after for r in rows) for after in c.LABELS} for before in c.LABELS} for g in c.LABELS}
    out[panel]=dict(common_N=len(rows),paper_r1_historical_only=metrics(rows,{r['id']:r['pred']['paper_r1'] for r in rows}),
        author={author:{arm:metrics([r for r in rows if r['author']==author],{r['id']:r['pred'][arm] for r in rows if r['author']==author}) for arm in ['baseline','candidate']} for author in sorted({r['author'] for r in rows})},
        patient_count=len(patients),patient_changes=patients,
        patients_correct_improved=sum(p['correct_delta']>0 for p in patients),patients_correct_worsened=sum(p['correct_delta']<0 for p in patients),
        patients_false_S_reduced=sum(p['false_S_delta']<0 for p in patients),patients_false_S_increased=sum(p['false_S_delta']>0 for p in patients),
        transitions=transitions,patient_cluster_risk_CI=risks(rows),independent_sklearn_MCC_PA_and_false_S_counts_match=True)
c.put(ROOT/'outputs/109_boundary_replay/analysis_details.json',dict(task=109,panels=out,patient_indices_are_panel_local_not_new_patient_IDs=True,all_data_development_exposed=True))
print(c.canonical({p:{k:v for k,v in d.items() if k in ['patient_count','patients_correct_improved','patients_correct_worsened','independent_sklearn_MCC_PA_and_false_S_counts_match']} for p,d in out.items()}))
