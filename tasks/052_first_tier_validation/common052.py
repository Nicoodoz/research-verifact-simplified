"""052 shared utilities; importing performs no credential/API access."""
from pathlib import Path
import csv,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/052_first_tier_validation"
MODEL_DS="deepseek-v4-flash-0731"
MODEL_Q="qwen3.8-27b"
CAP=80.0
PRICES={MODEL_DS:(3,9),MODEL_Q:(3,12)}
VALID=("valid","valid_with_format_anomaly")
LABELS=("Supported","Not Supported","Not Addressed")

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
canonical=c020.canonical;require=c020.require

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
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
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+"\n")
def csvwrite(p,rows):
    rows=list(rows)
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def judge_body(claim,reference,scored,thinking,model=MODEL_DS):
    b=c020.body(claim,reference,scored=scored)
    b["model"]=model;b["stream"]=False;b["temperature"]=0
    b["enable_thinking"]=bool(thinking)
    if thinking:
        b["reasoning_effort"]="high";b["max_tokens"]=8192
    else:
        b.pop("reasoning_effort",None);b["max_tokens"]=2048
    return b

def parse_response(tr,scored,thinking):
    p=core024.parse(tr,scored)
    if tr.get("http_status")==200:
        try:
            native=json.loads(tr["body_text"]);msg=native["choices"][0]["message"];rc=msg.get("reasoning_content")
            p["reasoning_present"]=bool(isinstance(rc,str) and rc.strip())
            usage=native.get("usage") or {};details=usage.get("completion_tokens_details") or {}
            p["reasoning_tokens"]=details.get("reasoning_tokens",usage.get("reasoning_tokens"))
        except Exception:
            p["reasoning_present"]=False;p["reasoning_tokens"]=None
    if thinking:
        adh=[x for x in p.get("adherence",[]) if x!="unexpected_thinking"];p["adherence"]=adh
        if p.get("status")=="valid_with_format_anomaly" and not adh:p["status"]="valid"
        if p.get("status") in VALID and not p.get("reasoning_present"):
            p["adherence"].append("thinking_requested_but_no_reasoning_content");p["status"]="valid_with_format_anomaly"
    return p

def bound(job):
    b=job["body"];ip,op=PRICES[b["model"]]
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",2048)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[job["body"]["model"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)

def judge_body(claim,reference,scored,thinking,model=MODEL_DS):
    b=c020.body(claim,reference,scored=scored)
    b["model"]=model;b["enable_thinking"]=bool(thinking);b["temperature"]=0;b["stream"]=False
    b["max_tokens"]=8192 if thinking else 2048
    if thinking:b["reasoning_effort"]="high"
    else:b.pop("reasoning_effort",None)
    return b

def parse_response(tr,scored,expect_thinking):
    p=core024.parse(tr,scored)
    if tr.get("http_status")!=200:return p
    try:
        native=json.loads(tr["body_text"]);msg=native["choices"][0]["message"]
        reasoning=msg.get("reasoning_content")
        p["reasoning_present"]=bool(isinstance(reasoning,str) and reasoning.strip())
        p["reasoning_chars"]=len(reasoning) if isinstance(reasoning,str) else 0
        usage=native.get("usage") or {};details=usage.get("completion_tokens_details") or {}
        p["reasoning_tokens"]=details.get("reasoning_tokens",usage.get("reasoning_tokens"))
        if expect_thinking:
            p["adherence"]=[x for x in p.get("adherence",[]) if x!="unexpected_thinking"]
            if p.get("status")=="valid_with_format_anomaly" and not p["adherence"]:p["status"]="valid"
            if p.get("status") in VALID and not p["reasoning_present"]:
                p["adherence"].append("thinking_requested_but_no_reasoning_content");p["status"]="valid_with_format_anomaly"
        elif p["reasoning_present"]:
            p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_reasoning_present")
    except Exception as exc:
        p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("thinking_parse:"+type(exc).__name__)
    return p

def decision(scores,lam=0.0):
    import math
    vals={k:math.log(max(float(scores[k])/100,1e-6))+(lam if k=="Supported" else 0.0) for k in LABELS}
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:vals[k])

def bound(job):
    b=job["body"];ip,op=PRICES[b["model"]]
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",2048)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[job["body"]["model"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)
