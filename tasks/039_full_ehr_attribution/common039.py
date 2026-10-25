"""039 shared utilities: full-eligible-EHR high-recall attribution audit."""
from __future__ import annotations
import csv, hashlib, json, os, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/039_full_ehr_attribution"
CAP=60.0
sys.path.insert(0,str(ROOT/"tasks/038_evidence_explanation_audit"))
import common038 as b
MODEL_KEY="qwen"
MODEL=b.MODELS[MODEL_KEY]
LABELS=("Supported","Not Supported","Not Addressed","Uncertain")

read=b.read; jsonl=b.jsonl; csvread=b.csvread; put=b.put; csvwrite=b.csvwrite
require=b.require; now=b.now; canonical=b.canonical; file_hash=b.file_hash
transport_client=b.transport_client

def digest(v):
    return hashlib.sha256(canonical(v).encode("utf-8")).hexdigest()

def stable_hash(prefix,value):
    return hashlib.sha256((prefix+str(value)).encode()).hexdigest()

def clean_json(text):
    require(isinstance(text,str) and text.strip(),"empty content")
    t=text.strip()
    if t.startswith("```"):
        t=re.sub(r"^```(?:json)?\s*","",t); t=re.sub(r"\s*```$","",t)
    try:return json.loads(t)
    except json.JSONDecodeError:
        lo,hi=t.find("{"),t.rfind("}")
        require(lo>=0 and hi>lo,"no json object")
        return json.loads(t[lo:hi+1])

def quote_found(quote,text):
    if not isinstance(quote,str) or not quote.strip():return False
    pat=r"\s+".join(re.escape(x) for x in quote.split())
    return re.search(pat,text) is not None

QUERY_SYSTEM="""Generate conservative search aids for locating evidence for one clinical proposition in a patient's EHR.
You see only the proposition, not any patient record or gold label.
Return JSON only with keys requirements and queries.
requirements: 1-6 short material requirements actually asserted by the proposition. Preserve dates, scope, certainty, causal/temporal relations and qualifiers; do not add new facts.
queries: 1-4 short retrieval queries. Include the original key concepts plus useful lexical variants/abbreviations only when semantically safe. Do not weaken or strengthen the proposition. Do not answer whether the proposition is true."""

AUDIT_SYSTEM="""Audit one clinical proposition against supplied EHR evidence.
You do not know any gold label, model prediction, or prior explanation.
Evidence is split into C-prefixed items (the original C48 context seen by the verifier) and E-prefixed items (additional passages found by a high-recall search over the same eligible admission EHR corpus).

Use these labels:
Supported: every material part of the proposition is supported by the supplied evidence.
Not Supported: evidence addresses the proposition but contradicts it or supports only part of the complete proposition.
Not Addressed: the material claimed fact is not addressed.
Uncertain: the relationship cannot be determined reliably.

Return JSON only with keys audit_label, coverage, requirements, summary.
coverage is complete, partial, or uncertain.
For each material requirement return claim_requirement, relation (supported/contradicted/unaddressed/uncertain), and evidence.
Each evidence item has source (C48 or EHR), id (such as C3 or E17), and a short exact contiguous quote from that item.
For supported or contradicted relations cite at least one evidence item. Missing information is unaddressed, not contradicted. Preserve the proposition's exact strength and qualifiers. Do not use outside medical knowledge as patient evidence."""

def query_body(claim):
    return dict(model=MODEL,messages=[
        dict(role="system",content=QUERY_SYSTEM),
        dict(role="user",content=json.dumps({"proposition":claim},ensure_ascii=False))
    ],temperature=0,max_tokens=500,enable_thinking=False,response_format={"type":"json_object"})

def audit_body(claim,c48_text,expanded_text):
    payload={"proposition":claim,"C48":c48_text,"additional_EHR":expanded_text}
    return dict(model=MODEL,messages=[
        dict(role="system",content=AUDIT_SYSTEM),
        dict(role="user",content=json.dumps(payload,ensure_ascii=False))
    ],temperature=0,max_tokens=1800,enable_thinking=False,response_format={"type":"json_object"})

def bound(job):
    ip,op=b.PRICES[MODEL_KEY]
    return ((len(canonical(job["body"]).encode())+2000)*ip+job["body"]["max_tokens"]*op)/1e6

def charge(job,tr):
    try:
        raw=json.loads(tr["body_text"]);u=raw["usage"];i=int(u["prompt_tokens"]);o=int(u["completion_tokens"])
        ip,op=b.PRICES[MODEL_KEY];return (i*ip+o*op)/1e6,"peak_no_cache_usage_estimate"
    except Exception:return bound(job),"unknown_usage_reservation"

def outer_content(tr):
    require(tr.get("http_status")==200,"no http200")
    raw=json.loads(tr["body_text"])
    return raw["choices"][0]["message"]["content"],raw.get("model"),raw.get("usage",{})

def parse_query(job,tr):
    out=dict(status="invalid",requirements=None,queries=None,errors=[])
    try:
        content,model,usage=outer_content(tr);obj=clean_json(content)
        req=obj.get("requirements");qs=obj.get("queries")
        require(isinstance(req,list) and 1<=len(req)<=6 and all(isinstance(x,str) and x.strip() for x in req),"bad requirements")
        require(isinstance(qs,list) and 1<=len(qs)<=4 and all(isinstance(x,str) and x.strip() for x in qs),"bad queries")
        out.update(status="valid",requirements=req,queries=qs,model_returned=model,usage=usage,output_text=content)
    except Exception as exc:out["errors"].append(type(exc).__name__+":"+str(exc)[:180])
    return out

def parse_audit(job,tr):
    out=dict(status="invalid",audit_label=None,coverage=None,requirements=[],errors=[],strict_supported=False,
             used_c48=False,used_external=False,citations_valid=False)
    try:
        content,model,usage=outer_content(tr);obj=clean_json(content)
        label=obj.get("audit_label");coverage=obj.get("coverage");rows=obj.get("requirements")
        require(label in LABELS,"bad label");require(coverage in ("complete","partial","uncertain"),"bad coverage")
        require(isinstance(rows,list) and 1<=len(rows)<=6,"bad rows")
        lookup=job["evidence_lookup"];checked=[];all_valid=True
        for row in rows:
            require(isinstance(row,dict),"bad row");rel=row.get("relation")
            require(rel in ("supported","contradicted","unaddressed","uncertain"),"bad relation")
            evs=row.get("evidence",[]);require(isinstance(evs,list),"bad evidence list");cev=[]
            for ev in evs:
                require(isinstance(ev,dict),"bad evidence item")
                src=ev.get("source");eid=str(ev.get("id",""));quote=ev.get("quote","")
                require(src in ("C48","EHR") and eid in lookup,"bad evidence id")
                valid=quote_found(quote,lookup[eid]["text"]);all_valid=all_valid and valid
                cev.append(dict(source=src,id=eid,quote=quote,valid=bool(valid)))
            if rel in ("supported","contradicted") and not cev:all_valid=False
            checked.append(dict(claim_requirement=row.get("claim_requirement"),relation=rel,evidence=cev))
        strict=label=="Supported" and coverage=="complete" and all(r["relation"]=="supported" for r in checked) and all_valid
        used_c48=any(e["source"]=="C48" for r in checked for e in r["evidence"])
        used_external=any(e["source"]=="EHR" for r in checked for e in r["evidence"])
        out.update(status="valid",audit_label=label,coverage=coverage,requirements=checked,summary=obj.get("summary"),
                   strict_supported=bool(strict),used_c48=used_c48,used_external=used_external,
                   citations_valid=bool(all_valid),model_returned=model,usage=usage,output_text=content)
    except Exception as exc:out["errors"].append(type(exc).__name__+":"+str(exc)[:180])
    return out

def parse_job(job,tr):
    return parse_query(job,tr) if job["kind"]=="query" else parse_audit(job,tr)
