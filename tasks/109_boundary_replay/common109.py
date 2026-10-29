"""109 shared metadata helpers; no model, CUDA, cloud, SSH or API side effects."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/109_boundary_replay'
PRIVATE=ROOT/'.local_models/109_boundary_replay'
LABELS=('Supported','Not Supported','Not Addressed')
SOURCE_ADAPTER_SHA='096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'
REVISION='c202236235762e1c871ad0ccb60c8ee5ba337b9a'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def rows(path):return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
def canonical(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):result.update(block)
    return result.hexdigest()
def write(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.tmp')
    temporary.write_bytes((text.rstrip()+'\n').encode('utf-8'));os.replace(temporary,path)
def put(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))
def putl(path,values):write(path,'\n'.join(canonical(row) for row in values))
def utc():return datetime.now(timezone.utc).isoformat()
