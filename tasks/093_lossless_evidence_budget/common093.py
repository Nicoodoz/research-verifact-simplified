from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/093_lossless_evidence_budget';PRIVATE=ROOT/'.local_models/093'
def h(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def putl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
