"""022 offline utilities; no clients, credentials, or network operations."""
from pathlib import Path
import csv,hashlib,json,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/022_competition_aware_support_calibration'
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare
LABELS=('Supported','Not Supported','Not Addressed')
METHODS=('B','V_raw','U0','U2','G','C','M','V','T','Always_S')
LEARNED=('G','C','M','V','T')
def require(x,msg):
    if not x:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def csvrows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(canonical(obj)+'\n')
def lines(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(canonical(r)+'\n')
def csvwrite(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def seal(out,deps=(),code=()):
    write(out/'manifest.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),files={p.relative_to(ROOT).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},dependencies={p.relative_to(ROOT).as_posix():sha(p) for p in deps},code={p.relative_to(ROOT).as_posix():sha(p) for p in code}))
def check(out):
    m=read(out/'manifest.json')
    for k in ('files','dependencies','code'):
        for p,h in m[k].items():require(sha(ROOT/p)==h,'Frozen SHA mismatch: '+p)
def prediction(rows,labels):return [dict(proposition_id=r['proposition_id'],verdict=LABELS[int(v)]) for r,v in zip(rows,labels)]
