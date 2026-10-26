"""099 independent task state. Never imports or modifies the098 execution state."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/099_judge_selection'
PRIVATE=ROOT/'.local_models/099_judge_selection'
MODELS=('qwen3.8-flash','qwen3.8-27b','qwen3.5-27b','qwen3.5-35b-a3b')
LABELS=('Supported','Not Supported','Not Addressed')
PRICES={MODELS[0]:(.8,2.7,.1),MODELS[1]:(3.,12.,.6),MODELS[2]:(.6,4.8,None),MODELS[3]:(.4,3.2,None)}
REPOS={MODELS[0]:'Qwen/Qwen3.8-Flash-Next',MODELS[1]:'Qwen/Qwen3.8-27B',MODELS[2]:'Qwen/Qwen3.5-27B',MODELS[3]:'Qwen/Qwen3.5-35B-A3B'}
CAP=20.
ENDPOINT='https://maas.qianwenaiapi.com/compatible-mode/v1'
THINKING=2048
ANSWER=512
sys.path.insert(0,str(ROOT/'src'))

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x.encode('utf-8')).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def put(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if p.exists():assert p.read_bytes()==b,f'Frozen file differs: {p}'
    else:
        with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def putl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=''.join(canonical(x)+'\n' for x in rows).encode('utf-8')
    if p.exists():assert p.read_bytes()==b,f'Frozen file differs: {p}'
    else:
        with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def bound(body):
    i,o,_=PRICES[body['model']]
    return ((len(canonical(body).encode('utf-8'))+2048)*i+(THINKING+ANSWER+32)*o)/1e6
def parse(tr):
    try:
        native=json.loads(tr['body_text']);assert tr['http_status']==200
        choice=native['choices'][0];content=choice['message']['content']
        def unique(pairs):
            x={}
            for k,v in pairs:
                if k in x:raise ValueError('duplicate JSON key')
                x[k]=v
            return x
        obj=json.loads(content,object_pairs_hook=unique);assert isinstance(obj,dict) and obj.get('verdict') in LABELS
        reason_ok=isinstance(obj.get('reason'),str) and bool(obj['reason'].strip())
        return dict(verdict=obj['verdict'],valid=True,reason_present=reason_ok,finish_reason=choice.get('finish_reason'),format_anomaly=not reason_ok or choice.get('finish_reason')!='stop')
    except (KeyError,ValueError,TypeError,IndexError,AssertionError,AttributeError):
        return dict(verdict=None,valid=False,reason_present=False,format_anomaly=True)
