"""Task032 utilities; no clients, credentials or raw EHR access."""
import os,sys,json,csv,hashlib,datetime,time,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/032_evidence_relation_correction'
CACHE=ROOT/'.local_models/032'
LABELS=('Supported','Not Supported','Not Addressed')
sys.path.insert(0,str(ROOT/'src'))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def require(v,msg):
    if not v:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def text(p,s):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(s,encoding='utf-8')
    for attempt in range(5):
        try:os.replace(tmp,p);return
        except PermissionError:
            if attempt==4:raise
            time.sleep(.15*(attempt+1))
def put(p,v):text(p,json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def jsonl(p,rr):text(p,''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rr))
def csvread(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvwrite(p,rr):
    import io
    rr=list(rr);s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=list(dict.fromkeys(k for r in rr for k in r)));w.writeheader();w.writerows(rr);text(p,s.getvalue())
def state(stage,**kw):put(OUT/'execution_status.json',dict(stage=stage,updated_utc=now(),pid=os.getpid(),**kw))
def block_network():
    def denied(*a,**k):raise RuntimeError('032 computation is offline; clinical content must not leave device')
    socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
def scoped_gt(ids):
    found={};ids=set(ids)
    with (ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['proposition_id'] in ids:found[r['proposition_id']]=r['human_gt']
    require(set(found)==ids,'Allowed GT IDs not fully aligned');return found

def metric(rows,pred):
    from verifact_research.evaluation import evaluate
    import numpy as np
    pp=[dict(proposition_id=r['proposition_id'],verdict=LABELS[int(p)]) for r,p in zip(rows,pred)]
    m=evaluate(rows,pp,profile='none');y=np.array([LABELS.index(r['human_gt']) for r in rows]);p=np.asarray(pred)
    return dict(n=len(rows),correct=int(sum(y==p)),PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],false_S=int(sum((p==0)&(y!=0))),confusion_matrix=m['confusion_matrix'],recall={k:v['recall'] for k,v in m['per_class'].items()})
