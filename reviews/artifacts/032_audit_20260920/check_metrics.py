
import json,csv,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[3];base=root/'outputs/032_evidence_relation_correction';a=Path(__file__).parent
rows=[json.loads(s) for s in (base/'inference_001/predictions_blind.jsonl').read_text().splitlines()]
with (root/'outputs/031_training_expansion_confirmation/analysis_001/confirmation_GT.csv').open(encoding='utf-8') as f:gt={r['proposition_id']:r['human_gt'] for r in csv.DictReader(f)}
labels=['Supported','Not Supported','Not Addressed'];y=np.array([labels.index(gt[r['proposition_id']]) for r in rows])
metrics=json.loads((base/'analysis_001/metrics.json').read_text());pairs=json.loads((base/'analysis_001/paired.json').read_text())
def calc(cm):
 n=cm.sum();correct=np.trace(cm);pred=cm.sum(0);truth=cm.sum(1)
 den=np.sqrt((n*n-pred@pred)*(n*n-truth@truth));mcc=(correct*n-truth@pred)/den if den else 0
 return np.array([correct/n,mcc])
count=0
for key,m in metrics.items():
 scope,method=key.split('/');ii=[i for i,r in enumerate(rows) if scope=='all' or r['author_type']==scope];p=np.array([rows[i]['predictions'][method] for i in ii]);truth=y[ii]
 cm=np.bincount(3*truth+p,minlength=9).reshape(3,3)
 assert cm.tolist()==m['confusion_matrix']
 assert np.allclose(calc(cm),[m['PA'],m['MCC']],rtol=0,atol=1e-12)
 assert int(sum((truth!=0)&(p==0)))==m['false_S'];count+=1
patients=sorted({r['subject_id'] for r in rows});sid=np.array([patients.index(r['subject_id']) for r in rows])
p=np.array([r['predictions']['attention'] for r in rows]);q=np.array([r['predictions']['U2'] for r in rows]);draws=[]
for seed in range(1000):
 w=np.bincount(np.random.RandomState(seed).choice(12,12),minlength=12)[sid]
 pc=np.bincount(3*y+p,weights=w,minlength=9).reshape(3,3);qc=np.bincount(3*y+q,weights=w,minlength=9).reshape(3,3)
 draws.append(calc(pc)-calc(qc))
ci=np.percentile(draws,[2.5,97.5],axis=0)
for i,k in enumerate(['percent_agreement','mcc']):assert np.allclose(ci[:,i],pairs['attention__vs__U2']['metrics'][k]['ci95'],rtol=0,atol=1e-12)
summary=dict(passed=True,confusion_PA_MCC_falseS_groups=count,primary_bootstrap_draws=1000,PA_CI=ci[:,0].tolist(),MCC_CI=ci[:,1].tolist(),API_calls=0)
(a/'independent_metrics.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(summary)
