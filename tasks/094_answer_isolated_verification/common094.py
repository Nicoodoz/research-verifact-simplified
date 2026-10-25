from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/094_answer_isolated_verification';PRIVATE=ROOT/'.local_models/094'
MODEL='deepseek-v4-flash-0731';CAP=20
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def h(v):return hashlib.sha256(v.encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
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
def bound(b):return ((len(canonical(b).encode())+2000)*3+b['max_tokens']*9)/1e6
