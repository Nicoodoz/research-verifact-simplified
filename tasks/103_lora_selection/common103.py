"""103 isolated paths and immutable research records."""
from pathlib import Path
import sys,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/103_lora_selection'
PRIVATE=ROOT/'.local_models/103_lora_selection'
sys.path.insert(0,str(ROOT/'src'))
MODELS=('qwen3.5-27b','qwen3.8-27b','qwen3.5-35b-a3b','qwen3.6-35b-a3b')
REPOS=dict(zip(MODELS,('Qwen/Qwen3.5-27B','Qwen/Qwen3.8-27B','Qwen/Qwen3.5-35B-A3B','Qwen/Qwen3.6-35B-A3B')))|{'qwen3.5-9b':'Qwen/Qwen3.5-9B'}
LABELS=('Supported','Not Supported','Not Addressed')
PRICES={MODELS[0]:(.6,4.8,None),MODELS[1]:(3.,12.,.6),MODELS[2]:(.4,3.2,None),MODELS[3]:(1.8,10.8,None)}
CAP=30.; THINKING=4096; ANSWER=768
ENDPOINT='https://maas.qianwenaiapi.com/compatible-mode/v1'
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def put(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
 if p.exists():assert p.read_bytes()==b,f'Frozen differs: {p}'
 else:p.write_bytes(b)
def putl(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=''.join(canonical(r)+'\n' for r in x).encode()
 if p.exists():assert p.read_bytes()==b,f'Frozen differs: {p}'
 else:p.write_bytes(b)
