"""Local artifacts for the user-authorized 098 completion and one fixed follow-up."""
from pathlib import Path
import datetime as dt,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/100_preregistered_followup'
PRIVATE=ROOT/'.local_models/100_preregistered_followup'
CAP=130.0
OPERATING=125.0
LABELS=('Supported','Not Supported','Not Addressed')
sys.path.insert(0,str(ROOT/'src'))
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def put(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==b,p
 else:
  with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def putl(p,rr):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=''.join(canonical(r)+'\n' for r in rr).encode()
 if p.exists():assert p.read_bytes()==b,p
 else:p.write_bytes(b)
