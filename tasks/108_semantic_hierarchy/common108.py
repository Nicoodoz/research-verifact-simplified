"""108 local helpers; no model, cloud or paid side effects on import."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/108_semantic_hierarchy'
PRIVATE=ROOT/'.local_models/108_semantic_hierarchy'
LABELS=('Supported','Not Supported','Not Addressed')
ARMS=('flat_ce','hier_shared','hier_pool')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def canonical(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def write(path,text):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_bytes((text.rstrip()+'\n').encode('utf-8'));os.replace(t,p)
def put(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))
def putl(path,values):write(path,'\n'.join(canonical(v) for v in values))
