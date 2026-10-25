"""035: offline numerical inputs and shared audited evaluation."""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import csv, json, hashlib, sys, socket
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import evaluate, paired_compare
from verifact_research.evaluation.metrics import metrics_from_confusions
LABELS=('Supported','Not Supported','Not Addressed')
METHODS=('U0','U2','U2_T','Joint_NLL','Task_T','Robust_T','MCC_T')
def denied(*args,**kwargs):raise RuntimeError('035 is offline')
socket.create_connection=denied
socket.socket.connect=denied
socket.socket.connect_ex=denied
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def jsonl(p):
    with Path(p).open(encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
def csvread(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def put(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvwrite(p,rows):
    if not rows:raise ValueError('Empty CSV '+str(p))
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def decode(v):return np.array([1,2,0])[np.argmax(v[:,[1,2,0]],axis=1)]
def cohort(rows):return [dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=LABELS[r['y']]) for r in rows]
def predictions(rows,p):return [dict(proposition_id=r['id'],verdict=LABELS[int(y)]) for r,y in zip(rows,p)]
def arrays(rows):
    s=np.array([r['scores'] for r in rows],float)
    if not np.isfinite(s).all() or np.any(s<0) or not np.allclose(s.sum(1),100):raise ValueError('Invalid scores')
    z=np.log(np.maximum(s/100,1e-6));y=np.array([r['y'] for r in rows],int)
    return z,y

def load_data():
    paths={
      'old':ROOT/'outputs/022_competition_aware_support_calibration/preparation_001/rows.jsonl',
      'oldfold':ROOT/'outputs/022_competition_aware_support_calibration/preparation_001/folds.json',
      'main':ROOT/'outputs/033_gate_training_subset/evaluation_001/full_rows.jsonl',
      'mainpred':ROOT/'outputs/033_gate_training_subset/evaluation_001/full_predictions.csv',
      'groups':ROOT/'outputs/003_error_analysis/patient_groups.json',
      'deepseek':ROOT/'outputs/024_lambda2_transfer_validation/analysis_001/predictions_deepseek.csv',
      'qwen':ROOT/'outputs/024_lambda2_transfer_validation/analysis_001/predictions_qwen.csv'}
    old=jsonl(paths['old']);main=jsonl(paths['main']);folds=read(paths['oldfold'])
    dev=set(read(paths['groups'])['groups']['development'])
    extra=sorted(dev-set(folds),key=lambda x:hashlib.sha256(('035/lambda/folds/v1:'+x).encode()).hexdigest())
    folds.update({s:i%4 for i,s in enumerate(extra)})
    def convert(r,kind):
        scores=r['scores'] if kind!='csv' else {c:float(r['score_'+c]) for c in LABELS}
        sid=str(r['subject_id']);assert sid in dev
        return dict(id=r['proposition_id'],sid=sid,author=r['author_type'],
          y=LABELS.index(r['human_gt']),scores=[scores[c] for c in LABELS],fold=folds[sid],
          repeat=int(r.get('repeat',0)),source=r.get('source',r.get('partition',kind)))
    datasets={'old_R0':[convert(r,'old') for r in old if r['repeat']==0],
      'old_R1':[convert(r,'old') for r in old if r['repeat']==1],
      'main40':[convert(r,'main') for r in main]}
    for m in ['deepseek','qwen']:
        rr=csvread(paths[m]);assert len(rr)==879 and all(r['score_Supported']!='' for r in rr)
        datasets['bridge_'+m]=[convert(r,'csv') for r in rr]
    assert [len(datasets[k]) for k in datasets]==[1529,879,3675,879,879]
    for name,rr in datasets.items():
        assert len({r['id'] for r in rr})==len(rr)
        arrays(rr)
    assert set(r['sid'] for r in datasets['main40'])==dev
    source_preds={r['proposition_id']:r for r in csvread(paths['mainpred'])}
    z,_=arrays(datasets['main40']);z2=z.copy();z2[:,0]+=2
    for r,a,b in zip(datasets['main40'],decode(z),decode(z2)):
        p=source_preds[r['id']];assert p['GT']==LABELS[r['y']] and p['subject_id']==r['sid']
        assert p['U0']==LABELS[a] and p['U2']==LABELS[b]
    reference={r['id']:(r['sid'],r['y'],r['author']) for r in datasets['main40']}
    for rr in datasets.values():
        for r in rr:assert reference[r['id']]==(r['sid'],r['y'],r['author'])
    return datasets,folds,{str(p.relative_to(ROOT)):sha(p) for p in paths.values()}
