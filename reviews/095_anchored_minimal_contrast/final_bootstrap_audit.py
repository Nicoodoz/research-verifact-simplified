"""Independent patient-resampling verification using explicit confusion counts."""
import json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'outputs/095_anchored_minimal_contrast';D=Path(__file__).parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def values(cm):
    n=cm.sum();a=cm.sum(1);b=cm.sum(0);diag=cm.diagonal();correct=diag.sum();den=np.sqrt(max(0,(n*n-(a*a).sum())*(n*n-(b*b).sum())))
    pa=correct/n;mcc=(n*correct-(a*b).sum())/den if den else 0;f1=np.divide(2*diag,a+b,out=np.zeros(3),where=(a+b)!=0).mean()
    q=(a+b)/(2*n);pe=np.sum(q*(1-q))/2;ac1=(pa-pe)/(1-pe)
    return np.array([pa,mcc,f1,ac1])
assert any(r['stage']=='analysis_ready' for r in rows(O/'progress.jsonl'))
allrows=rows(O/'unified_9065_predictions.jsonl');reports=read(O/'baseline_paired.json');labels=['Supported','Not Supported','Not Addressed'];summary={}
for name,z in reports.items():
    rr=[r for r in allrows if r['B_raw_valid' if name=='raw_B-Original' else 'B_core_valid']];sids=sorted({r['sid'] for r in rr});idx={s:i for i,s in enumerate(sids)};counts=np.zeros((2,len(sids),3,3),dtype=np.int64)
    for r in rr:
        for arm,model in enumerate([z['base'],z['candidate']]):counts[arm,idx[r['sid']],labels.index(r['GT']),labels.index(r['predictions'][model])]+=1
    diffs=[]
    for seed in range(1000):
        selection=np.random.RandomState(seed).choice(len(sids),len(sids),replace=True)
        diffs.append(values(counts[1,selection].sum(0))-values(counts[0,selection].sum(0)))
    ci=np.quantile(np.asarray(diffs),[.025,.975],axis=0)
    for index,key in [(0,'percent_agreement'),(1,'mcc'),(3,'gwet_ac1')]:assert np.allclose(ci[:,index],z['official_paired_compare']['metrics'][key]['ci95'],atol=1e-10)
    rng=np.random.RandomState(95095);diffs=[]
    for selection in rng.randint(0,len(sids),size=(1000,len(sids))):diffs.append(values(counts[1,selection].sum(0))[2]-values(counts[0,selection].sum(0))[2])
    mf=np.quantile(diffs,[.025,.975]);assert np.allclose(mf,z['CI95']['Macro_F1'],atol=1e-10)
    summary[name]={'PA_ci95':ci[:,0].tolist(),'MCC_ci95':ci[:,1].tolist(),'AC1_ci95':ci[:,3].tolist(),'Macro_F1_ci95':mf.tolist(),'resampling_verified':True}
with (D/'final_bootstrap_checks.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
print('independently verified',len(summary),'paired patient bootstrap comparisons, 1000 draws each')
