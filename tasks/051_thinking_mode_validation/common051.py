"""051 shared utilities; no credentials/API on import."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/051_thinking_mode_validation"
MODEL="deepseek-v4-flash-0731"
SCREEN_CAP=25.0
TOTAL_CAP=50.0
PRICE=(3,9)  # conservative busy-hour ceiling; actual usage is recorded.
VALID=("valid","valid_with_format_anomaly")

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
canonical=c020.canonical;require=c020.require
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
def now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def put(p,v,new=True):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x" if new else "w",encoding="utf-8",newline="\n") as f:
        json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def csvwrite(p,rows):
    import csv
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def judge_body(claim,reference,scored,thinking):
    b=c020.body(claim,reference,scored=scored)
    b["model"]=MODEL
    b["enable_thinking"]=bool(thinking)
    b["max_tokens"]=8192 if thinking else 2048
    if thinking:b["reasoning_effort"]="high"
    else:b.pop("reasoning_effort",None)
    b["temperature"]=0;b["stream"]=False
    return b

def parse_response(tr,scored,thinking):
    p=core024.parse(tr,scored)
    if tr.get("http_status")==200:
        try:
            native=json.loads(tr["body_text"]);msg=native["choices"][0]["message"]
            rc=msg.get("reasoning_content")
            p["reasoning_present"]=bool(isinstance(rc,str) and rc.strip())
            p["reasoning_chars"]=len(rc) if isinstance(rc,str) else 0
            usage=native.get("usage") or {}
            details=usage.get("completion_tokens_details") or {}
            p["reasoning_tokens"]=details.get("reasoning_tokens",usage.get("reasoning_tokens"))
        except Exception:
            p["reasoning_present"]=False;p["reasoning_chars"]=0;p["reasoning_tokens"]=None
    if thinking:
        adh=[x for x in p.get("adherence",[]) if x!="unexpected_thinking"]
        p["adherence"]=adh
        if p.get("status")=="valid_with_format_anomaly" and not adh:p["status"]="valid"
        if p.get("status") in VALID and not p.get("reasoning_present"):
            p["adherence"].append("thinking_requested_but_no_reasoning_content")
            p["status"]="valid_with_format_anomaly"
    return p

def bound(job):
    b=job["body"];ip,op=PRICE
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",2048)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICE
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)
