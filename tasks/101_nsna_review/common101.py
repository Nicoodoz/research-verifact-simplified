"""Task101 immutable public/private artifacts; never expose source text in public outputs."""
from pathlib import Path
import datetime as dt, hashlib, json, os, sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/101_nsna_review'
PRIVATE=ROOT/'.local_models/101_nsna_review'
sys.path.insert(0,str(ROOT/'src'))
MODEL='deepseek-v4-flash-0731'
ENDPOINT='https://maas.qianwenaiapi.com/compatible-mode/v1'
LABELS=('Supported','Not Supported','Not Addressed')
REVIEW_ARMS=('nsna_plain','nsna_review')
CAP=30.
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def put(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
 if p.exists():assert p.read_bytes()==b,('immutable differs',p)
 else:
  with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def putl(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=''.join(canonical(r)+'\n' for r in rows).encode('utf-8')
 if p.exists():assert p.read_bytes()==b,('immutable differs',p)
 else:p.write_bytes(b)
def job(row,arm,body,repeat=False):
 h=digest(canonical(body));rid=digest(canonical(['101/v1',row['stage'],row['id'],arm,repeat,h]))[:28]
 return dict(request_id=rid,id=row['id'],sid=row['sid'],stage=row['stage'],panel=row['panel'],arm=arm,repeat=repeat,body=body,body_sha256=h)
