import os,json,csv,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/092_task_adapted_verifier'
PRIVATE=ROOT/'.local_models/092'
LABELS=['Supported','Not Supported','Not Addressed']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f:return [json.loads(x) for x in f if x.strip()]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def put(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows),encoding='utf-8');os.replace(tmp,p)
def csvrows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
