"""Task078 pure helpers; importing does not read credentials or call APIs."""
import json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/078_component_ablation';TASK=Path(__file__).parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tasks/053_thinking_prior_validation'))
import common053 as c53
CAP=30.;MODEL='deepseek-v4-flash-0731';PRICES=(3.,9.)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def put(p,x,new=True):
 with Path(p).open('x' if new else 'w',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def jl(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:
  for r in x:f.write(canon(r)+'\n')
def bound(body):return ((len(canon(body).encode())+2000)*PRICES[0]+body['max_tokens']*PRICES[1])/1e6
def charge(tr,res):
 if tr is None or tr.get('http_status')==0:return res
 if tr.get('http_status')!=200:return 0.
 try:
  u=json.loads(tr['body_text'])['usage'];a,b=int(u['prompt_tokens']),int(u['completion_tokens']);assert min(a,b)>=0
  return (a*PRICES[0]+b*PRICES[1])/1e6
 except (KeyError,ValueError,TypeError,AssertionError):return res
def parse(job,tr):return c53.parse_response(tr,job['scored'],job['thinking'])
