"""053 shared utilities. Importing does not access credentials or network."""
from pathlib import Path
import csv,datetime,hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/053_thinking_prior_validation"
CAP=15.0
MODEL_DS="deepseek-v4-flash-0731"
MODEL_Q="qwen3.8-27b"
LABELS=("Supported","Not Supported","Not Addressed")
VALID=("valid","valid_with_format_anomaly")
PRICES={MODEL_DS:(3,9),MODEL_Q:(3,12)}
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as b
canonical=b.canonical;require=b.require
c020=b.c020

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
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def judge_body(claim,reference,scored=True,thinking=False,model=MODEL_DS):
    return b.judge_body(claim,reference,scored,thinking,model)
def parse_response(tr,scored=True,expect_thinking=False):
    return b.parse_response(tr,scored,expect_thinking)
def decision(scores,lam=0.0):return c020.decision(scores,lam)

def actual_charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[job["body"]["model"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return reservation(job)

def reservation(job):
    cond=job["condition"]
    if cond=="N-S":return 0.015
    if cond=="T-S":return 0.060
    if cond=="Gate_peer":return 0.022
    return 0.060

def log_scores(scores):
    return {k:math.log(max(float(scores[k])/100,1e-6)) for k in LABELS}
def decode_logits(v):
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:v[k])
def calibrated(scores,theta,kind):
    v=log_scores(scores)
    if kind=="G":v["Supported"]+=theta[0]
    elif kind=="M":v["Supported"]+=theta[0];v["Not Supported"]+=theta[1]
    else:raise ValueError(kind)
    return v
def prior_adjust(v,reference_counts,calibration_counts):
    rt=sum(reference_counts.values());ct=sum(calibration_counts.values())
    out=dict(v)
    for k in LABELS:
        out[k]+=math.log((reference_counts[k]/rt)/(calibration_counts[k]/ct))
    return out
