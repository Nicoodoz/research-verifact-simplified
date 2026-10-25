from pathlib import Path
import copy,hashlib,json,re,sys,datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/067_conservative_evidence_packing"
CAP=30.0
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}
LABELS=("Supported","Not Supported","Not Addressed")

sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as b
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024

read=b.read;lines=b.lines;put=b.put;jsonl=b.jsonl;csvwrite=b.csvwrite
require=b.require;canonical=b.canonical
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

_TS_TEMPLATE=None
for _j in lines(ROOT/"outputs/052_first_tier_validation/main_jobs.jsonl"):
    if _j.get("condition")=="T-S":
        _TS_TEMPLATE=copy.deepcopy(_j["body"]);break
require(_TS_TEMPLATE is not None,"missing 052 T-S template")
require(_TS_TEMPLATE.get("enable_thinking") is True and _TS_TEMPLATE.get("reasoning_effort")=="high","T-S drift")

def score_body(claim,reference):
    x=copy.deepcopy(_TS_TEMPLATE)
    x["messages"][1]["content"]=json.dumps({"proposition":claim,"reference":reference},ensure_ascii=False,separators=(",",":"))
    return x

P0=np.array([1108.,100.,170.]);P0/=P0.sum()
CAL=np.array([48.,47.,48.]);CAL/=CAL.sum()
G=.1342909508820116
PB=np.log(P0/CAL);PB-=PB[2]
def priorg(scores):
    a=np.log(np.maximum(np.array([float(scores[k])/100 for k in LABELS]),1e-6));a[0]+=G
    return LABELS[int(np.argmax(a+PB))]

AUDIT_SYSTEM=(
"You are a conservative evidence-pack auditor for clinical fact verification, not the final judge. "
"You receive one proposition, the IDs currently shown to the verifier, and all 48 C48 raw EHR candidates. "
"Your job is ONLY to identify material verification requirements and whether the current pack is missing a C48 passage that is needed to test them. "
"Do not output Supported, Not Supported, or Not Addressed and do not guess the gold label. "
"Preserve both supporting and opposing evidence. A plan/order is not completion; possibility is not certainty; preserve negation, time, scope, event state, and numeric trends. "
"The existing pack is the safety baseline: recommend additions only when they add material information absent from the existing pack. "
"Mark an existing passage safe_drop only if it is genuinely redundant/context-only and removing it cannot erase support, contradiction, temporal qualification, negation, certainty, event-state, scope, or numeric-trend information. "
"Return JSON only with: requirements (1-6 strings), must_keep_baseline (IDs), additions (0-4 objects with id, requirement, role, priority integer 1-3, why), safe_drop_baseline (IDs), unresolved (strings). "
"Allowed roles: direct_support, direct_contradiction, temporal, negation, certainty, event_state, scope, numeric_or_trend."
)
def audit_body(claim,baseline_ids,candidates):
    payload={"proposition":claim,"current_pack_ids":baseline_ids,"C48_candidates":candidates}
    return dict(model=MODELS["qwen"],messages=[
        dict(role="system",content=AUDIT_SYSTEM),
        dict(role="user",content=json.dumps(payload,ensure_ascii=False))
    ],temperature=0,max_tokens=850,enable_thinking=False,response_format={"type":"json_object"})

def outer(tr):
    require(tr.get("http_status")==200,"no http200")
    x=json.loads(tr["body_text"])
    return x["choices"][0]["message"]["content"],x.get("model"),x.get("usage",{})

def clean_json(s):
    t=s.strip()
    if t.startswith("```"):
        t=re.sub(r"^```(?:json)?\s*","",t)
        t=re.sub(r"\s*```$","",t)
    try:
        return json.loads(t)
    except Exception:
        lo,hi=t.find("{"),t.rfind("}")
        require(lo>=0 and hi>lo,"no json")
        return json.loads(t[lo:hi+1])

ROLES={"direct_support","direct_contradiction","temporal","negation","certainty","event_state","scope","numeric_or_trend"}

def parse_audit(tr,job):
    out={"status":"invalid","requirements":[],"must_keep_baseline":[],"additions":[],"safe_drop_baseline":[],"unresolved":[],"errors":[]}
    try:
        content,model,usage=outer(tr)
        o=clean_json(content)
        req=o.get("requirements");mk=o.get("must_keep_baseline");adds=o.get("additions");sd=o.get("safe_drop_baseline");un=o.get("unresolved")
        require(isinstance(req,list) and 1<=len(req)<=6 and all(isinstance(x,str) and x.strip() for x in req),"bad requirements")
        require(isinstance(mk,list) and isinstance(adds,list) and len(adds)<=4 and isinstance(sd,list) and isinstance(un,list),"bad list fields")
        allowed=set(job["candidate_lookup"]);base=set(job["baseline_short_ids"])
        mk=list(dict.fromkeys(str(x) for x in mk));sd=list(dict.fromkeys(str(x) for x in sd))
        require(all(x in base for x in mk),"must_keep not baseline")
        require(all(x in base for x in sd),"safe_drop not baseline")
        aa=[]
        for z in adds:
            require(isinstance(z,dict),"bad addition")
            cid=str(z.get("id"));role=str(z.get("role"));prio=int(z.get("priority"))
            require(cid in allowed and cid not in base,"addition must be nonbaseline C48")
            require(role in ROLES and 1<=prio<=3,"bad role/priority")
            aa.append(dict(id=cid,requirement=str(z.get("requirement","")),role=role,priority=prio,why=str(z.get("why",""))))
        out.update(status="valid",requirements=req,must_keep_baseline=mk,additions=aa,safe_drop_baseline=sd,unresolved=[str(x) for x in un],output_text=content,model_returned=model,usage=usage)
    except Exception as e:
        out["errors"].append(type(e).__name__+":"+str(e)[:180])
    return out

def parse(job,tr):
    if tr.get("http_status")!=200:
        return {"status":"invalid","errors":["no_http200"]}
    if job["kind"]=="audit":
        return parse_audit(tr,job)
    if job["kind"]=="judge":
        q=core024.parse(tr,True)
        if q.get("model_returned") not in (None,MODELS["deepseek"]):
            q["status"]="invalid_core_fields";q.setdefault("errors",[]).append("unexpected_model")
        return q
    raise ValueError(job["kind"])

def bound(job):
    ip,op=PRICES[job["model_key"]];body=job["body"]
    return ((len(canonical(body).encode())+2000)*ip+body.get("max_tokens",1500)*op)/1e6

def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"]
        ip,op=PRICES[job["model_key"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:
        return bound(job)

def norm(s):
    return re.sub(r"\s+"," ",str(s)).strip().lower()

def candidate_line(cid,p):
    return f"{cid} | Date {p.get('date')} | Time {p.get('time')} | {p.get('category')} | Note {p.get('note_id')} | Text: {p.get('text','')}"

def display_line(i,p):
    return f"{i}. Date: {p.get('date')}, Time: {p.get('time')}, Note Category: {p.get('category')}, Note ID: {p.get('note_id')}, Raw characters: [{p.get('start')},{p.get('end_exclusive')}) | Text: {p.get('text','')}"

def reference_header(ref):
    m=re.search(r"(?m)^1\. Date:",ref)
    return ref[:m.start()] if m else ""

def reference_blocks(ref):
    parts=re.split(r"(?m)^\d+\. Date:",ref)
    out=[]
    for z in parts[1:]:
        t=z.split("| Text:",1)
        if len(t)==2:
            out.append(norm(t[1]))
    return out

RISK_RE=re.compile(r"\b(?:no|not|without|denies|denied|negative|never|none|unable|possible|possibly|probable|probably|likely|suspect|suspected|concern|concerned|if|would|could|may|might|plan|planned|planning|scheduled|ordered|order|refused|refuse|cancelled|canceled|pending|consider|considered|held|hold|stopped|stop|discontinued|discontinue|completed|performed|done|recommend|recommended)\b",re.I)
def text_is_hard_protected(text):
    return bool(RISK_RE.search(str(text)))

def pack_size(pids,corpus):
    return sum(len(display_line(i+1,corpus[pid]))+1 for i,pid in enumerate(pids) if pid in corpus)

def build_reference_from_ids(pids,corpus,baseline_reference):
    objs=[corpus[x] for x in pids if x in corpus]
    objs.sort(key=lambda p:(str(p.get("date","")),str(p.get("time","")),str(p.get("note_id","")),int(p.get("start",0))))
    body="\n".join(display_line(i,p) for i,p in enumerate(objs,1))
    return reference_header(baseline_reference)+body
