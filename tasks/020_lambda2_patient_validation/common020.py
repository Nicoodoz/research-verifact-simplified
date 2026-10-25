"""020 shared constants; importing never reads credentials or calls services."""
from pathlib import Path
from datetime import datetime, timezone
import csv, json, math, sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/020_lambda2_patient_validation'
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tasks/019_support_boundary_screen'))
import common019 as prior
from common016 import baseline, pilot, sf, RAW, embedding_jobs, csvrows
from atomic019 import save
from verifact_research.inference.siliconflow_pool import canonical, fingerprint, file_hash, require, load_accounts, balance_exhausted
from verifact_research.inference.aliyun import load_config, AliyunClient
from verifact_research.evaluation import evaluate, paired_compare
LABELS=prior.LABELS
MODEL=prior.MODEL
ALI_MODEL=prior.ALI_MODEL
NATIVE=baseline.native
CAP=80.0
GLOBAL_ROUTE=prior.GLOBAL_ROUTE
PHASES={'new10_embedding':'new10/preparation_002','new10_rerank':'new10/candidates_001','new10_judge':'new10/base_preparation_001'}

def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def jsonlines(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def write_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);save(path,obj,new=True)
def write_lines(path,rows):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(canonical(r)+'\n')
def write_csv(path,rows,keys=None):
    keys=keys or list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def patient_ids(phase):
    require(phase=='new10','Only new10 authorized');return baseline.patient_order()[30:40]
def hash_rank(text,namespace='020/hash/v1:'):return fingerprint(namespace+text)
def seal(folder,dependencies=(),code=()):
    paths=[p for p in folder.rglob('*') if p.is_file()]+list(dependencies)+list(code)
    write_json(folder/'manifest.json',dict(created_utc=now(),sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}))
def check_manifest(path):
    path=Path(path);path=path/'manifest.json' if path.is_dir() else path;m=read(path)
    for k,v in m['sha256'].items():require(file_hash(ROOT/k)==v,'Frozen file changed: '+k)
    return m
def body(text,reference,scored=False):return prior.body(text,reference,scored)
def decision(scores,lam=2):
    require(lam in (0,2),'No new parameter search');return prior.decision(scores,lam)
def bound(job):
    return prior.bound(job['body']) if job['kind']=='chat' else NATIVE.bound(job)
def charge(job,transport):
    return prior.charge(job['body'],transport) if job['kind']=='chat' else NATIVE.cost(job,transport)
def parse(job,tr):
    if job['kind']=='chat':return prior.parse(tr,job['arm']=='S')
    if tr.get('http_status')!=200:return dict(status='invalid',errors=['no_http200'])
    try:
        n=prior.strict_json(tr['body_text'])
        require(n.get('model',job['body']['model'])==job['body']['model'],'Unexpected model')
        if job['kind']=='embedding':
            import numpy as np
            data=n['data'];require(sorted(x['index'] for x in data)==list(range(len(job['body']['input']))),'Embedding index mismatch')
            for x in data:
                v=np.asarray(x['embedding'],dtype=float)
                require(v.shape==(1024,) and np.isfinite(v).all() and np.linalg.norm(v)>0,'Bad embedding')
        else:
            data=n['results'];require(sorted(x['index'] for x in data)==list(range(len(job['body']['documents']))),'Rerank index mismatch')
            require(all(math.isfinite(float(x['relevance_score'])) for x in data),'Bad rerank score')
        return dict(status='success',errors=[])
    except (ValueError,TypeError,KeyError,IndexError) as exc:return dict(status='invalid',errors=[str(exc)[:160]])
def job_preparation(stage):
    require(stage in PHASES,'Unregistered phase');return OUT/PHASES[stage]
def totals(rows,preds):return prior.totals(rows,preds)
def prediction_rows(rows,labels):return prior.prediction_rows(rows,labels)
