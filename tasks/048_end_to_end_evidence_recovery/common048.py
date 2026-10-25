"""048 shared deterministic utilities; importing never calls an API."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,re,sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/048_end_to_end_evidence_recovery"
R044=ROOT/"outputs/044_incremental_evidence_recovery"
R031=ROOT/"outputs/031_training_expansion_confirmation"
SCREEN_CAP=10.0
TOTAL_CAP=30.0
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}
VALID=("valid","valid_with_format_anomaly")

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
sys.path.insert(0,str(ROOT/"tasks/039_full_ehr_attribution"))
import common039 as c039
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

canonical=c020.canonical
require=c020.require
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
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def score_body(claim,reference):
    b=c020.body(claim,reference,scored=True);b["model"]=MODELS["deepseek"];return b
def parse_score(tr):
    p=core024.parse(tr,True)
    if p.get("model_returned") not in (None,MODELS["deepseek"]):
        p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_model")
    return p
def ulabel(scores,lam):return c020.decision(scores,lam=lam)
def query_body(claim):
    b=c039.query_body(claim);b["model"]=MODELS["qwen"];return b
def audit_body(claim,c48_text,expanded_text):
    b=c039.audit_body(claim,c48_text,expanded_text);b["model"]=MODELS["qwen"];return b

def parse_reference(reference,passage_lookup):
    starts=list(re.finditer(r"(?m)^(\d+)\. Date:",reference))
    require(starts,"empty reference")
    entries=[];ids=set()
    for i,m in enumerate(starts):
        end=starts[i+1].start() if i+1<len(starts) else len(reference)
        text=reference[m.start():end].strip();num=int(m.group(1))
        mm=re.search(r"Note ID: (\d+), Raw characters: \[(\d+),(\d+)\)",text)
        pid=None
        if mm:pid=passage_lookup.get((mm.group(1),int(mm.group(2)),int(mm.group(3))))
        if pid:ids.add(pid)
        # Prefix C but retain the original evidence line verbatim after its numeric prefix.
        stripped=re.sub(r"^\d+\.\s*","",text,count=1)
        entries.append((f"C{num}",f"C{num}. {stripped}",pid))
    return entries,ids

def line_external(i,p):
    return f"E{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"

def build_audit_job(request_id,claim,reference,candidate_pids,passages):
    plook={(str(p["note_id"]),int(p["start"]),int(p["end_exclusive"])):pid for pid,p in passages.items()}
    cents,cids=parse_reference(reference,plook)
    external=[]
    for i,pid in enumerate(candidate_pids,1):
        p=passages[pid];external.append((f"E{i}",line_external(i,p),pid))
    c48_text="\n".join(x[1] for x in cents)
    ext_text="\n".join(x[1] for x in external) if external else "No additional EHR passages selected."
    lookup={eid:dict(source="C48",text=text,passage_id=pid) for eid,text,pid in cents}
    lookup.update({eid:dict(source="EHR",text=text,passage_id=pid) for eid,text,pid in external})
    return dict(request_id=request_id,kind="audit",model_key="qwen",body=audit_body(claim,c48_text,ext_text),evidence_lookup=lookup,candidate_pids=list(candidate_pids),c48_ids=sorted(cids))

def cited_external_passages(parsed,job,max_items=12):
    if parsed.get("status")!="valid":return []
    out=[]
    lookup=job["evidence_lookup"]
    for row in parsed.get("requirements",[]):
        for ev in row.get("evidence",[]):
            eid=str(ev.get("id",""))
            if ev.get("source")!="EHR" or not ev.get("valid") or eid not in lookup:continue
            pid=lookup[eid].get("passage_id")
            if pid and pid not in out:out.append(pid)
            if len(out)>=max_items:return out
    return out

def append_passages(base,pids,passages):
    nums=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",base)]
    start=max(nums)+1 if nums else 1
    parts=[base.rstrip()];kept=[]
    base_text={re.sub(r"\s+"," ",m.group(1)).strip() for m in re.finditer(r"\| Text: ([\s\S]*?)(?=\n\d+\. Date:|\Z)",base)}
    for pid in pids:
        if pid not in passages or pid in kept:continue
        p=passages[pid];norm=re.sub(r"\s+"," ",p["text"]).strip()
        if norm in base_text:continue
        parts.append(pc.display_line(start+len(kept),p));kept.append(pid)
    return "\n".join(parts),kept

def bound(job):
    ip,op=PRICES[job["model_key"]];b=job["body"]
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",1500)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[job["model_key"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)

def simple_metrics(rows,pred_key):
    from sklearn.metrics import matthews_corrcoef
    gt=[r["GT"] for r in rows];pr=[r[pred_key] for r in rows];n=len(rows)
    out=dict(n=n,correct=sum(a==b for a,b in zip(gt,pr)),
      PA=sum(a==b for a,b in zip(gt,pr))/n,
      MCC=float(matthews_corrcoef(gt,pr)),
      false_S=sum(a!="Supported" and b=="Supported" for a,b in zip(gt,pr)))
    for lab in ("Supported","Not Supported","Not Addressed"):
        den=sum(a==lab for a in gt)
        out["recall_"+lab.replace(" ","_")]=sum(a==lab and b==lab for a,b in zip(gt,pr))/den if den else None
    return out
