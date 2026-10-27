"""102 immutable files, public metadata and private clinical payloads."""
from pathlib import Path
import datetime as dt,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/102_demo_relation';PRIVATE=ROOT/'.local_models/102_demo_relation'
sys.path.insert(0,str(ROOT/'src'))
LABELS=('Supported','Not Supported','Not Addressed')
ARMS=('verifact_ref','demo_topic','demo_relation')
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def put(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
 if p.exists():assert p.read_bytes()==b,('frozen file differs',str(p))
 else:p.write_bytes(b)
def putl(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=''.join(canonical(r)+'\n' for r in rows).encode('utf-8')
 if p.exists():assert p.read_bytes()==b,('frozen file differs',str(p))
 else:p.write_bytes(b)
