"""Offline-only schemas, deterministic features and task-owned atomic storage."""
from pathlib import Path
import csv,datetime,hashlib,json,os,socket,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/029_semantic_information_gate';PREP=OUT/'preparation_001'
sys.path.insert(0,str(ROOT/'tasks/025_lambda_flip_risk_separability'))
import common025 as old
import frontier025_numeric as frontier
LABELS=old.LABELS
SCORE=old.S_NAMES+old.D_NAMES
REPEAT=['repeat_s','repeat_ns','repeat_na']
SEMANTIC=['requirement_count','fraction_supported','fraction_contradicted','fraction_unaddressed','fraction_uncertain','coverage_complete']
QUALITY=['claim_quote_valid_fraction','evidence_quote_valid_fraction','format_anomaly']
FEATURES={'A':SCORE,'B':SCORE+REPEAT,'C':SCORE+SEMANTIC+QUALITY,'D':SCORE+REPEAT+SEMANTIC+QUALITY,'C_no_quality':SCORE+SEMANTIC,'D_no_quality':SCORE+REPEAT+SEMANTIC}
def require(v,msg):
    if not v:raise ValueError(msg)
def blocked(*a,**kw):raise RuntimeError('029 forbids network and external APIs')
def offline():socket.socket.connect=blocked;socket.socket.connect_ex=blocked;socket.create_connection=blocked;socket.getaddrinfo=blocked
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def lines(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def csvread(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.ndarray):return clean(v.tolist())
    if isinstance(v,np.generic):return clean(v.item())
    if isinstance(v,float) and not np.isfinite(v):return None
    return v
def write_text(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:f.write(text);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def put(path,v):write_text(path,json.dumps(clean(v),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def jsonl(path,rows):write_text(path,''.join(json.dumps(clean(r),ensure_ascii=False,allow_nan=False)+'\n' for r in rows))
def csvwrite(path,rows):
    import io
    rows=list(rows);buf=io.StringIO(newline='');fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
    for r in rows:w.writerow({k:json.dumps(clean(v),ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    write_text(path,buf.getvalue())
def score_features(ds,q):
    d0=int(old.decode(old.logs(ds),0));q0=int(old.decode(old.logs(q),0));q2=int(old.decode(old.logs(q),2))
    return dict(**old.score_features(ds),**dict(zip(old.D_NAMES,[q[LABELS[0]]/100,old.logs(q)[0]-max(old.logs(q)[1:]),float(q0==0),float(q2==0),float(q0==d0)])))
def new_features(repeat,trace):
    require(repeat['status'] in ('valid','valid_with_format_anomaly') and trace['status'] in ('valid','valid_with_format_anomaly'),'Core invalid source; do not silently impute')
    require(repeat['verdict'] in LABELS,'Bad repeat label');rows=trace['rows'];require(1<=len(rows)<=8,'Bad trace row count')
    require(all(r['relation'] in ('supported','contradicted','unaddressed','uncertain') for r in rows),'Bad trace relation')
    ev=[e for r in rows for e in r['evidence']]
    return dict(**{k:float(repeat['verdict']==label) for k,label in zip(REPEAT,LABELS)},requirement_count=float(len(rows)),**{'fraction_'+rel:sum(r['relation']==rel for r in rows)/len(rows) for rel in ('supported','contradicted','unaddressed','uncertain')},coverage_complete=float(trace['claim_coverage']=='complete'),claim_quote_valid_fraction=sum(bool(r['claim_spans']) for r in rows)/len(rows),evidence_quote_valid_fraction=sum(bool(e['valid']) for e in ev)/len(ev) if ev else 0.,format_anomaly=float(trace['status']!='valid' or bool(trace.get('adherence')) or any(r.get('diagnostics') for r in rows)))
def schema():
    descriptions={**{n:'025冻结S+D同名特征，从D/Q原score重建' for n in SCORE},**{n:'028 repeat最终verdict的固定三类one-hot' for n in REPEAT},'requirement_count':'trace requirements项数','coverage_complete':'claim_coverage == complete','claim_quote_valid_fraction':'claim_spans非空的要求项比例','evidence_quote_valid_fraction':'valid=true的证据引用比例；无证据引用为0','format_anomaly':'trace非valid状态、adherence或任一row diagnostics非空'}
    for k in SEMANTIC:
        if k.startswith('fraction_'):descriptions[k]='该relation的项数 / requirements数'
    return dict(conditions=FEATURES,fields=[dict(name=k,definition=descriptions[k],quality_feature=k in QUALITY) for k in SCORE+REPEAT+SEMANTIC+QUALITY],excluded=['GT','patient_id','author_type','cohort','manual_error_type','free_text','hard_gate_keep','historical_SD_probability'])
def environment():
    import importlib.metadata,platform
    return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),versions={k:importlib.metadata.version(k) for k in ('numpy','scipy','pandas','scikit-learn','xgboost')})
def verify_frozen():
    m=read(PREP/'manifest.json')
    for section in ('sources','files','code'):
        for p,h in m[section].items():require(sha(ROOT/p)==h,'Frozen input changed: '+p)
    require(environment()['versions']==read(PREP/'environment.json')['versions'],'Environment versions changed')
    return m
