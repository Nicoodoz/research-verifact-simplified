from pathlib import Path
import json,hashlib,datetime,os
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/095_anchored_minimal_contrast';PRIVATE=ROOT/'.local_models/095'
MODEL='deepseek-v4-flash-0731';CAP=150
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def sha(p):
    hh=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):hh.update(b)
    return hh.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f:return [json.loads(x) for x in f if x.strip()]
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def putl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(canonical(r)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def progress(stage,note):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'progress.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(canonical(dict(utc=now(),stage=stage,note=note))+'\n')
