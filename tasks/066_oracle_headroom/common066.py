from pathlib import Path
import copy,hashlib,json,re,sys,datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/066_oracle_headroom"
CAP=20.0
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}
LABELS=("Supported","Not Supported","Not Addressed")

sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as b
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024

read=b.read; lines=b.lines; put=b.put; jsonl=b.jsonl; csvwrite=b.csvwrite
require=b.require; canonical=b.canonical
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(prefix,x): return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

# Exact 053 thinking-scoring request template.
_TS_TEMPLATE=None
for _j in lines(ROOT/"outputs/053_thinking_prior_validation/main_jobs.jsonl"):
    if _j.get("condition")=="T-S":
        _TS_TEMPLATE=copy.deepcopy(_j["body"]);break
require(_TS_TEMPLATE is not None,"missing 053 T-S template")
require(_TS_TEMPLATE.get("enable_thinking") is True and _TS_TEMPLATE.get("reasoning_effort")=="high","T-S template drift")

def score_body(claim,reference):
    x=copy.deepcopy(_TS_TEMPLATE)
    x["messages"][1]["content"]=json.dumps({"proposition":claim,"reference":reference},ensure_ascii=False,separators=(",",":"))
    return x

P0=np.array([1108.,100.,170.]);P0/=P0.sum()
CAL=np.array([48.,47.,48.]);CAL/=CAL.sum()
G=.1342909508820116
PB=np.log(P0/CAL);PB-=PB[2]
def priorg(scores):
    a=np.log(np.maximum(np.array([float(scores[k])/100 for k in LABELS]),1e-6))
    a[0]+=G
    return LABELS[int(np.argmax(a+PB))]

PLANNER_SYSTEM=(
"You are building an ORACLE evidence pack for an upper-bound study of clinical fact verification. "
"You are allowed to see the clinician gold label only to search for the most diagnostic raw EHR evidence; "
"the final verifier will NOT see the gold label. Do not invent, distort, or cherry-pick misleading evidence. "
"For Supported, seek direct evidence covering the complete proposition. For Not Supported, seek evidence that "
"addresses the proposition but contradicts it, leaves a material part unsupported, or shows plan/refusal/non-completion. "
"For Not Addressed, seek the most relevant records and preserve the distinction that absence is not contradiction. "
"Preserve time, negation, certainty, scope, numeric trends, and plan-versus-completion. "
"Return JSON only with requirements (1-6 strings), queries (1-6 strings), and goal (short string)."
)
def planner_body(claim,gt):
    payload={"proposition":claim,"gold_label_for_oracle_search_only":gt}
    return dict(model=MODELS["qwen"],messages=[
        dict(role="system",content=PLANNER_SYSTEM),
        dict(role="user",content=json.dumps(payload,ensure_ascii=False))
    ],temperature=0,max_tokens=700,enable_thinking=False,response_format={"type":"json_object"})

COMPOSER_SYSTEM=(
"You are an ORACLE evidence selector for an upper-bound study, not the final verifier. "
"You may see the clinician gold label only to identify the most diagnostic TRUE raw EHR passages. "
"Select 1-8 candidate IDs. Never fabricate evidence and never hide a material contradiction or qualifier merely to force the gold label. "
"For Supported, cover every material part directly when possible. For Not Supported, include the clearest contradiction, partial-support, "
"wrong-time, wrong-scope, or non-completion evidence. For Not Addressed, select the closest relevant context while recognizing that missing "
"information is not contradiction. Prefer minimal sufficient evidence but preserve decisive counterevidence. "
"Return JSON only with selected, decisive (boolean), unresolved (list), and why. Do not write the final three-class verdict for the downstream model."
)
def composer_body(claim,gt,requirements,candidates):
    payload={"proposition":claim,"gold_label_for_oracle_selection_only":gt,
             "requirements":requirements,"candidates":candidates}
    return dict(model=MODELS["qwen"],messages=[
        dict(role="system",content=COMPOSER_SYSTEM),
        dict(role="user",content=json.dumps(payload,ensure_ascii=False))
    ],temperature=0,max_tokens=1000,enable_thinking=False,response_format={"type":"json_object"})

def outer(tr):
    require(tr.get("http_status")==200,"no http200")
    x=json.loads(tr["body_text"])
    return x["choices"][0]["message"]["content"],x.get("model"),x.get("usage",{})

def clean_json(s):
    t=s.strip()
    if t.startswith("```"):
        t=re.sub(r"^```(?:json)?\\s*","",t)
        t=re.sub(r"\\s*```$","",t)
    try:
        return json.loads(t)
    except Exception:
        lo,hi=t.find("{"),t.rfind("}")
        require(lo>=0 and hi>lo,"no json object")
        return json.loads(t[lo:hi+1])

def parse_planner(tr):
    out={"status":"invalid","requirements":[],"queries":[],"goal":None,"errors":[]}
    try:
        content,model,usage=outer(tr);o=clean_json(content)
        req=o.get("requirements");qs=o.get("queries")
        require(isinstance(req,list) and 1<=len(req)<=6 and all(isinstance(x,str) and x.strip() for x in req),"bad requirements")
        require(isinstance(qs,list) and 1<=len(qs)<=6 and all(isinstance(x,str) and x.strip() for x in qs),"bad queries")
        out.update(status="valid",requirements=req,queries=qs,goal=o.get("goal"),output_text=content,model_returned=model,usage=usage)
    except Exception as e:
        out["errors"].append(type(e).__name__+":"+str(e)[:180])
    return out

def parse_composer(tr,job):
    out={"status":"invalid","selected":[],"decisive":False,"unresolved":[],"errors":[]}
    try:
        content,model,usage=outer(tr);o=clean_json(content)
        sel=o.get("selected")
        require(isinstance(sel,list) and len(sel)<=8,"bad selected")
        sel=list(dict.fromkeys(str(x) for x in sel))
        allowed=job["candidate_lookup"]
        require(all(x in allowed for x in sel),"unknown selected")
        out.update(status="valid",selected=sel,decisive=bool(o.get("decisive",False)),unresolved=o.get("unresolved") if isinstance(o.get("unresolved"),list) else [],why=o.get("why"),output_text=content,model_returned=model,usage=usage)
    except Exception as e:
        out["errors"].append(type(e).__name__+":"+str(e)[:180])
    return out

def parse(job,tr):
    if tr.get("http_status")!=200:
        return {"status":"invalid","errors":["no_http200"]}
    if job["kind"]=="judge":
        q=core024.parse(tr,True)
        if q.get("model_returned") not in (None,MODELS["deepseek"]):
            q["status"]="invalid_core_fields";q.setdefault("errors",[]).append("unexpected_model")
        return q
    if job["kind"]=="planner": return parse_planner(tr)
    if job["kind"]=="composer": return parse_composer(tr,job)
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

def candidate_line(cid,p):
    return f"{cid} | Date {p.get('date')} | Time {p.get('time')} | {p.get('category')} | Note {p.get('note_id')} | Text: {p.get('text','')}"

def final_line(i,p):
    return f"{i}. Date: {p.get('date')}, Time: {p.get('time')}, Note Category: {p.get('category')}, Note ID: {p.get('note_id')}, Raw characters: [{p.get('start')},{p.get('end_exclusive')}) | Text: {p.get('text','')}"

def build_reference(pids,corpus,max_chars=8000,max_items=8):
    objs=[corpus[x] for x in pids if x in corpus]
    objs.sort(key=lambda p:(str(p.get("date","")),str(p.get("time","")),str(p.get("note_id","")),int(p.get("start",0))))
    parts=[];kept=[];used=0
    for p in objs:
        line=final_line(len(parts)+1,p);L=len(line)+1
        if parts and used+L>max_chars: continue
        if not parts and L>max_chars:
            q=dict(p);q["text"]=str(p.get("text",""))[:max(200,max_chars-300)]
            line=final_line(1,q);L=len(line)+1
        parts.append(line);kept.append(p["passage_id"]);used+=L
        if len(parts)>=max_items: break
    require(parts,"empty final reference")
    return "\n".join(parts),kept,used
