"""042 shared I/O, selector rules and Judge parsing. Importing does not call APIs."""
from __future__ import annotations
import csv, hashlib, json, math, os, re, sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/042_coverage_aware_evidence_packing"
CAP=45.0
LABELS=("Supported","Not Supported","Not Addressed")
VALID=("valid","valid_with_format_anomaly")

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
from transport_direct024 import DirectClient
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

canonical=c020.canonical
require=c020.require
file_hash=c020.file_hash
def now(): return datetime.now(timezone.utc).isoformat()
def digest(v): return hashlib.sha256(canonical(v).encode("utf-8")).hexdigest()
def sha(p): return file_hash(Path(p))
def read(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def csvread(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
    require(bool(rows),"empty csv")
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def score_body(text,reference):
    b=c020.body(text,reference,scored=True)
    b["model"]="deepseek-v4-flash-0731"
    return b
def parse_score(tr):
    p=core024.parse(tr,True)
    if p.get("model_returned") not in (None,"deepseek-v4-flash-0731"):
        p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_model")
    return p
def bound(job):
    body=job["body"]
    return ((len(canonical(body).encode("utf-8"))+2000)*3+body["max_tokens"]*9)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];i=int(u["prompt_tokens"]);o=int(u["completion_tokens"])
        return (i*3+o*9)/1e6,"peak_no_cache_usage_estimate"
    except Exception:
        return bound(job),"unknown_usage_reservation"

def ulabel(scores,lam):
    return c020.decision(scores,lam=lam)

def display_line(i,p):
    return pc.display_line(i,p)

def render(selected,passages,admission):
    ordered=sorted(selected,key=lambda pid:(passages[pid]["date"],passages[pid]["time"],passages[pid]["note_id"],passages[pid]["start"]))
    header=f"Hospital Admission Start: {admission['ADMITTIME']}\nHospital Admission End: {admission['DISCHTIME']}\nElectronic Health Record Context\nOrdered by Time (Earliest to Latest):\n"
    text=header+("\n".join(display_line(i,passages[pid]) for i,pid in enumerate(ordered,1)) or "No Electronic Health Record Context Found.")
    return text,ordered

def baseline_select(candidate_ids,scores,passages,admission):
    return pc.select_evidence(candidate_ids,scores,passages,admission,cap=8000,max_items=16,max_per_note=2)
def softnote_select(candidate_ids,scores,passages,admission):
    selected=[];seen=set();size=0;skipped=[]
    for pid in sorted(candidate_ids,key=lambda x:(-scores[x],x)):
        p=passages[pid];dup=(p["date"],p["category"],p["text"])
        length=len(display_line(len(selected)+1,p))+1
        reason="duplicate_same_date_text" if dup in seen else "character_cap" if size+length>8000 else "max_items" if len(selected)>=16 else None
        if reason:skipped.append(dict(passage_id=pid,reason=reason,score=scores[pid]));continue
        selected.append(pid);seen.add(dup);size+=length
    text,ordered=render(selected,passages,admission)
    return dict(selected_ids=ordered,relevance_order=selected,selection_skips=skipped,reference=text,
                reference_sha256=hashlib.sha256(text.encode()).hexdigest(),body_characters=size,character_ceiling=8000)

def token_set(text): return set(pc.tokenize(text))
def covmmr_select(claim,candidate_ids,scores,passages,admission):
    ranked=sorted(candidate_ids,key=lambda x:(-scores[x],x));n=len(ranked)
    rank_rel={pid:(1.0 if n==1 else 1-(i/(n-1))) for i,pid in enumerate(ranked)}
    ct=list(dict.fromkeys(pc.tokenize(claim)));docsets={pid:token_set(passages[pid]["search_text"]) for pid in ranked}
    df={t:sum(t in docsets[p] for p in ranked) for t in ct}
    weights={t:math.log((n+1)/(df[t]+1))+1 for t in ct};den=sum(weights.values()) or 1.0
    selected=[];seen=set();covered=set();counts=Counter();size=0;skipped=[];remaining=set(ranked)
    # Protocol-fixed seed: preserve the highest reranked passage whenever it fits.
    if ranked:
        pid=ranked[0];p=passages[pid];length=len(display_line(1,p))+1;dup=(p["date"],p["category"],p["text"])
        if length<=8000:
            selected.append(pid);remaining.remove(pid);seen.add(dup);size+=length;counts[p["note_id"]]+=1;covered|=(docsets[pid]&set(ct))
    while remaining and len(selected)<16:
        best=None
        for pid in sorted(remaining):
            p=passages[pid];dup=(p["date"],p["category"],p["text"])
            length=len(display_line(len(selected)+1,p))+1
            if dup in seen or size+length>8000:continue
            gain=sum(weights[t] for t in ct if t in docsets[pid] and t not in covered)/den
            novelty=1.0 if not selected else 1-max(len(docsets[pid]&docsets[q])/max(1,len(docsets[pid]|docsets[q])) for q in selected)
            penalty=.05*max(0,counts[p["note_id"]]-1)
            utility=.70*rank_rel[pid]+.20*gain+.10*novelty-penalty
            key=(utility,rank_rel[pid],scores[pid],pid)
            if best is None or key>best[0]:best=(key,pid,length,dup)
        if best is None:break
        _,pid,length,dup=best;p=passages[pid]
        selected.append(pid);remaining.remove(pid);seen.add(dup);size+=length;counts[p["note_id"]]+=1;covered|=(docsets[pid]&set(ct))
    for pid in ranked:
        if pid not in selected:skipped.append(dict(passage_id=pid,reason="coverage_utility_or_budget",score=scores[pid]))
    text,ordered=render(selected,passages,admission)
    return dict(selected_ids=ordered,relevance_order=selected,selection_skips=skipped,reference=text,
                reference_sha256=hashlib.sha256(text.encode()).hexdigest(),body_characters=size,character_ceiling=8000)
def metrics(rows,pred_key):
    from sklearn.metrics import matthews_corrcoef
    gt=[r["GT"] for r in rows];pr=[r[pred_key] for r in rows];n=len(rows)
    correct=sum(a==b for a,b in zip(gt,pr));false_s=sum(a!="Supported" and b=="Supported" for a,b in zip(gt,pr))
    out=dict(n=n,correct=correct,PA=correct/n,MCC=float(matthews_corrcoef(gt,pr)),false_S=false_s)
    for lab in LABELS:
        den=sum(x==lab for x in gt);num=sum(x==lab and y==lab for x,y in zip(gt,pr))
        out["recall_"+lab.replace(" ","_")]=num/den if den else None
    return out

def body_hash(body):return hashlib.sha256(canonical(body).encode()).hexdigest()

def screen_rank(pid):return hashlib.sha256(("042/screen/v1:"+pid).encode()).hexdigest()
