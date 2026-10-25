"""096 R1 preparation. Import has no network or credential side effects."""
from pathlib import Path
import datetime,json,hashlib,os
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/096_r1_native_priorg';PRIVATE=ROOT/'.local_models/096_r1_native_priorg'
MODEL='Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ'
TOKENIZER=ROOT/'.local_models/085_valdemardi_tokenizer'
LABELS=('Supported','Not Supported','Not Addressed')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def encoded(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(x):return hashlib.sha256(encoded(x)).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if p.exists():
        assert read(p)==x,'Refuse to overwrite different frozen file '+str(p)
        return
    with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def putl(p,rr):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);data=b''.join(encoded(r)+b'\n' for r in rr)
    if p.exists():assert p.read_bytes()==data,'frozen jsonl differs';return
    with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def write(p,t):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='\n') as f:f.write(t.strip()+'\n')
def append(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('ab') as f:f.write(encoded(x)+b'\n');f.flush();os.fsync(f.fileno())
def key(s,pid):return hashlib.sha256((s+pid).encode()).hexdigest()
