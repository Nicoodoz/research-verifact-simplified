"""043 shared utilities. Importing does not call services."""
from __future__ import annotations
import csv,hashlib,json,math,os,re,sys
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/043_targeted_evidence_utility"
CAP=35.0
LABELS=("Supported","Not Supported","Not Addressed")
VALID=("valid","valid_with_format_anomaly")
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
from transport_direct024 import DirectClient
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

canonical=c020.canonical;require=c020.require;file_hash=c020.file_hash
def now():return datetime.now(timezone.utc).isoformat()
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return file_hash(Path(p))
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def csvread(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
    require(bool(rows),"empty csv");keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def score_body(text,reference):
    b=c020.body(text,reference,scored=True);b["model"]=MODELS["deepseek"];return b
def parse_score(tr):
    p=core024.parse(tr,True)
    if p.get("model_returned") not in (None,MODELS["deepseek"]):
        p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_model")
    return p
def ulabel(scores,lam):return c020.decision(scores,lam=lam)
AUDIT_SYSTEM="""Evaluate whether a clinical verification answer's explanation matches its own verdict and is grounded in the supplied reference.
You do not know the gold label, any post-processing label, or the experimental condition.
Return JSON only with keys label_reason_alignment, grounding, added_evidence_material, explanation.
label_reason_alignment: consistent if the reason/checks semantically support the stated verdict; contradictory if they support a different verdict; mixed if materially internally mixed.
grounding: grounded if the material factual claims used in the reason are supported by the supplied reference; partial if only some are grounded; ungrounded if central factual claims are not supported.
added_evidence_material: yes if one or more listed appended reference entries materially contribute to the answer's reasoning; no if they do not; not_applicable if no appended IDs are listed.
Do not decide what the verdict should have been. Audit the explanation relative to the stated verdict and supplied evidence."""
def audit_body(claim,reference,verdict,reason,checks,added_ids):
    payload=dict(proposition=claim,reference=reference,answer=dict(verdict=verdict,reason=reason,checks=checks),appended_reference_ids=added_ids)
    return dict(model=MODELS["qwen"],messages=[dict(role="system",content=AUDIT_SYSTEM),
      dict(role="user",content=json.dumps(payload,ensure_ascii=False))],temperature=0,max_tokens=600,enable_thinking=False,response_format={"type":"json_object"})
def clean_json(text):
    t=text.strip()
    try:return json.loads(t)
    except json.JSONDecodeError:
        a,b=t.find("{"),t.rfind("}");require(a>=0 and b>a,"no json");return json.loads(t[a:b+1])
def parse_audit(tr):
    out=dict(status="invalid",errors=[])
    try:
        require(tr.get("http_status")==200,"no http200");raw=json.loads(tr["body_text"]);ch=raw["choices"][0];obj=clean_json(ch["message"]["content"])
        a=obj.get("label_reason_alignment");g=obj.get("grounding");m=obj.get("added_evidence_material")
        require(a in ("consistent","contradictory","mixed"),"bad alignment");require(g in ("grounded","partial","ungrounded"),"bad grounding")
        require(m in ("yes","no","not_applicable"),"bad material")
        out.update(status="valid",label_reason_alignment=a,grounding=g,added_evidence_material=m,explanation=obj.get("explanation"),
                   model_returned=raw.get("model"),usage=raw.get("usage",{}),output_text=ch["message"]["content"])
    except Exception as exc:out["errors"].append(type(exc).__name__+":"+str(exc)[:160])
    return out
def bound(job):
    ip,op=PRICES[job["model_key"]];body=job["body"]
    return ((len(canonical(body).encode())+2000)*ip+body["max_tokens"]*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];i=int(u["prompt_tokens"]);o=int(u["completion_tokens"])
        ip,op=PRICES[job["model_key"]];return (i*ip+o*op)/1e6,"peak_no_cache_usage_estimate"
    except Exception:return bound(job),"unknown_usage_reservation"
def parse_job(job,tr):return parse_score(tr) if job["kind"]=="score" else parse_audit(tr)
def body_hash(body):return hashlib.sha256(canonical(body).encode()).hexdigest()
def stable_hash(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()

def jaccard(a,b):
    a=set(pc.tokenize(a));b=set(pc.tokenize(b));return len(a&b)/max(1,len(a|b))
def category_from_line(text):
    m=re.search(r"Note Category: ([^,]+),",text);return m.group(1).strip() if m else ""
def strip_external_prefix(text):
    return re.sub(r"^E\d+\.\s*","",text,count=1)
def append_entries(reference,entries):
    nums=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",reference)];start=(max(nums)+1) if nums else 1
    added=[];parts=[reference.rstrip()]
    for i,text in enumerate(entries,start):
        line=f"{i}. "+strip_external_prefix(text);parts.append(line);added.append(i)
    return "\n".join(parts),added
