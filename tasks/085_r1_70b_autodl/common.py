"""AutoDL branch primitives; imports never contact AWS or an inference service."""
from pathlib import Path
import datetime, hashlib, json, os, sys
ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'tasks/085_r1_70b_autodl'
OUT=ROOT/'outputs/085_r1_70b_autodl'
OLD=ROOT/'outputs/085_r1_70b_model_swap'
MODEL='casperhansen/deepseek-r1-distill-llama-70b-awq'
TOKENIZER='deepseek-ai/DeepSeek-R1-Distill-Llama-70B'
LABELS=('Supported','Not Supported','Not Addressed')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def write(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def put(p,x):write(p,(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
def putl(p,x):write(p,(''.join(canonical(v)+'\n' for v in x)).encode())
def check_old():
    f=read(OLD/'source_manifest.json')
    for rel,d in f['source_sha256'].items():assert sha(ROOT/rel)==d,rel
    for name,d in f['artifacts_sha256'].items():assert sha(OLD/name)==d,name
def body(j):
    return dict(model=MODEL,messages=[dict(role='system',content=j['instruction_semantic_content']),dict(role='user',content=json.dumps(dict(proposition=j['claim'],reference=j['reference']),ensure_ascii=False,separators=(',',':')))],
        temperature=0,top_p=1,max_tokens=8192,stream=False)
def freeze_job(j):
    b=body(j);d=digest(canonical(b).encode())
    return dict(id=j['id'],sid=j['sid'],arm=j['arm'],body=b,body_sha256=d,request_id=digest(('085-autodl/'+j['id']+'/'+j['arm']+'/'+d).encode())[:32])
