"""Task 097 local helpers. Public outputs never contain clinical source text."""
from pathlib import Path
import hashlib, json, datetime

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/097_native_judge_source_dependence'
PRIVATE = ROOT / '.local_models/097_native_judge_source_dependence'
MODEL = 'deepseek-v4-flash-0731'
LABELS = ('Supported', 'Not Supported', 'Not Addressed')

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f:
        return [json.loads(x) for x in f if x.strip()]
def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def digest(x): return hashlib.sha256(x.encode('utf-8')).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write_json(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if p.exists():
        assert p.read_bytes()==data, f'frozen file differs: {p}'
    else: p.write_bytes(data)
def write_lines(p,rr):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    data=b''.join((canonical(r)+'\n').encode('utf-8') for r in rr)
    if p.exists():
        assert p.read_bytes()==data, f'frozen file differs: {p}'
    else: p.write_bytes(data)
