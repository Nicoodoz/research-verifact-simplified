"""Task 105 paths; no model loading, network, cloud or paid side effects."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/105_brief_supervision'
PRIVATE=ROOT/'.local_models/105_brief_supervision'
LABELS=('Supported','Not Supported','Not Addressed')
ARMS=('base_judge','label_only','evidence_brief')
REVISION='c202236235762e1c871ad0ccb60c8ee5ba337b9a'

def canonical(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def put(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp');temp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'));temp.replace(path)
def putl(path,values):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(''.join(canonical(r)+'\n' for r in values).encode('utf-8'))
def frozen(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data:raise ValueError('Frozen artifact differs: '+str(path))
    if not path.exists():path.write_bytes(data)

