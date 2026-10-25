"""044 shared utilities. Importing does not call services."""
from __future__ import annotations
import csv,hashlib,json,math,os,re,sys
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/044_incremental_evidence_recovery"
CAP=80.0
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
def bound(job):
    ip,op=PRICES[job["model_key"]];body=job["body"]
    return ((len(canonical(body).encode())+2000)*ip+body["max_tokens"]*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];i=int(u["prompt_tokens"]);o=int(u["completion_tokens"])
        ip,op=PRICES[job["model_key"]];return (i*ip+o*op)/1e6,"peak_no_cache_usage_estimate"
    except Exception:return bound(job),"unknown_usage_reservation"
def body_hash(body):return hashlib.sha256(canonical(body).encode()).hexdigest()
def stable_hash(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
def display_line(i,p):return pc.display_line(i,p)
def tok(text):return pc.tokenize(text)
def tset(text):return set(tok(text))
def jaccard(a,b):
    a=tset(a);b=tset(b);return len(a&b)/max(1,len(a|b))
def nums(text):return set(re.findall(r"\d+(?:\.\d+)?",text))
def claim_flags(text):
    s=text.lower()
    keys=("admission","admitted","discharge","discharged","eventually","after","before","later","subsequently","initial","initially","prior","during")
    return {f"flag_{k}":int(k in s) for k in keys}
def append_reference(base,passage_ids,passages):
    nums0=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",base)]
    start=max(nums0)+1 if nums0 else 1;parts=[base.rstrip()];added=[]
    for n,pid in enumerate(passage_ids,start):
        parts.append(display_line(n,passages[pid]));added.append(n)
    return "\n".join(parts),added

def available_candidates(candidate_ids,selected_ids,passages):
    selected_text={re.sub(r"\s+"," ",passages[p]["text"]).strip() for p in selected_ids}
    out=[]
    for pid in candidate_ids:
        if pid in selected_ids:continue
        norm=re.sub(r"\s+"," ",passages[pid]["text"]).strip()
        if norm in selected_text:continue
        out.append(pid)
    return out

def pack_by_order(order,passages,budget=1500,max_items=3):
    chosen=[];used=0
    for pid in order:
        length=len(display_line(1,passages[pid]))+1
        if used+length>budget:continue
        chosen.append(pid);used+=length
        if len(chosen)>=max_items:break
    return chosen,used
def build_options(claim,candidate_ids,scores,selected_ids,passages,selection_skips):
    avail=available_candidates(candidate_ids,set(selected_ids),passages)
    ranked=sorted(avail,key=lambda p:(-scores[p],p))
    simple,_=pack_by_order(ranked,passages)
    near_ids=[x["passage_id"] for x in selection_skips if x["reason"] in ("max_per_note","character_cap") and x["passage_id"] in avail]
    near_order=near_ids+[p for p in ranked if p not in near_ids]
    near,_=pack_by_order(near_order,passages)
    base_texts=[passages[p]["search_text"] for p in selected_ids]
    base_union=set().union(*(tset(x) for x in base_texts)) if base_texts else set()
    claim_tokens=tset(claim);n=max(1,len(ranked));rank_rel={p:1-i/max(1,n-1) for i,p in enumerate(ranked)}
    remaining=set(ranked);novel=[];used=0;covered=claim_tokens&base_union
    while remaining and len(novel)<3:
        best=None
        for p in remaining:
            length=len(display_line(1,passages[p]))+1
            if used+length>1500:continue
            pt=tset(passages[p]["search_text"])
            rel=rank_rel[p];gain=len((claim_tokens&pt)-covered)/max(1,len(claim_tokens))
            nov=1.0 if not base_texts and not novel else 1-max([jaccard(passages[p]["search_text"],x) for x in base_texts]+[jaccard(passages[p]["search_text"],passages[q]["search_text"]) for q in novel])
            key=(.65*rel+.20*gain+.15*nov,rel,scores[p],p)
            if best is None or key>best[0]:best=(key,p,length,pt)
        if best is None:break
        _,p,length,pt=best;novel.append(p);remaining.remove(p);used+=length;covered|=(claim_tokens&pt)
    return {"simple":simple,"near_miss":near,"novel":novel}
def option_features(claim,option,pids,scores,ranked_all,selected_ids,passages):
    feats={}
    for name in ("simple","near_miss","novel"):feats["opt_"+name]=int(option==name)
    feats["n_passages"]=len(pids);feats["chars"]=sum(len(display_line(1,passages[p]))+1 for p in pids)
    rank={p:i+1 for i,p in enumerate(ranked_all)};n=max(1,len(ranked_all))
    rel=[1-(rank[p]-1)/max(1,n-1) for p in pids] or [0.]
    feats["rel_mean"]=float(np.mean(rel));feats["rel_max"]=float(np.max(rel));feats["rel_min"]=float(np.min(rel))
    base=[passages[p] for p in selected_ids];base_notes={p["note_id"] for p in base};base_dates={p["date"] for p in base};base_cats={p["category"] for p in base}
    cj=[jaccard(claim,passages[p]["search_text"]) for p in pids] or [0.]
    feats["claim_jaccard_mean"]=float(np.mean(cj));feats["claim_jaccard_max"]=float(np.max(cj))
    nov=[]
    for p in pids:
        nov.append(1-max([jaccard(passages[p]["search_text"],q["search_text"]) for q in base] or [0.]))
    feats["novelty_mean"]=float(np.mean(nov)) if nov else 0.
    feats["same_note"]=sum(passages[p]["note_id"] in base_notes for p in pids)
    feats["new_date"]=sum(passages[p]["date"] not in base_dates for p in pids)
    feats["new_category"]=sum(passages[p]["category"] not in base_cats for p in pids)
    base_claim=set().union(*(tset(q["search_text"]) for q in base)) & tset(claim) if base else set()
    opt_claim=set().union(*(tset(passages[p]["search_text"]) for p in pids)) & tset(claim) if pids else set()
    feats["claim_token_gain"]=len(opt_claim-base_claim)/max(1,len(tset(claim)))
    cnums=nums(claim);feats["numeric_match"]=sum(bool(cnums&nums(passages[p]["text"])) for p in pids)
    feats.update(claim_flags(claim))
    return feats

def feature_vector(feats,keys):return [float(feats.get(k,0)) for k in keys]
