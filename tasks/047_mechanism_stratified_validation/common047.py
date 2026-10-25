"""047 shared deterministic utilities; no API calls on import."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json, math, re, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/047_mechanism_stratified_validation"
R044=ROOT/"outputs/044_incremental_evidence_recovery"
R031=ROOT/"outputs/031_training_expansion_confirmation"
LABELS=("Supported","Not Supported","Not Addressed")
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}
TOTAL_CAP=30.0
SCREEN_CAP=8.0

sys.path.insert(0,str(ROOT/"tasks/020_lambda2_patient_validation"))
import common020 as c020
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

canonical=c020.canonical
require=c020.require
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def read(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]
def put(p,v,new=True):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    mode="x" if new else "w"
    with p.open(mode,encoding="utf-8",newline="\n") as f:
        json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False); f.write("\n")
def jsonl(p,rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def csvwrite(p,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def score_body(claim,reference,model_key="deepseek"):
    b=c020.body(claim,reference,scored=True)
    b["model"]=MODELS[model_key]
    return b
def parse_judge(tr):
    return core024.parse(tr,True)
def u2(scores):
    return c020.decision(scores,lam=2)

STOP=set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should".split())
def toks(text):
    return [x for x in re.findall(r"[a-z]+|\d+(?:\.\d+)?",text.lower()) if x not in STOP]
def tset(text): return set(toks(text))
def norm(text): return re.sub(r"\s+"," ",text).strip()
def stable(prefix,x): return hashlib.sha256((prefix+str(x)).encode()).hexdigest()

def ref_blocks(reference):
    m=re.search(r"(?m)^1\. Date:",reference)
    require(m is not None,"reference has no numbered evidence")
    header=reference[:m.start()].rstrip()
    body=reference[m.start():]
    blocks=re.split(r"\n(?=\d+\. Date:)",body)
    require(len(blocks)>0,"empty evidence blocks")
    return header,blocks

def renumber(block,n):
    return re.sub(r"^\d+\.",str(n)+".",block,count=1)

def focus_reference(claim,reference,n_priority=2):
    header,blocks=ref_blocks(reference)
    q=tset(claim)
    scored=[(len(q&tset(b)),i,b) for i,b in enumerate(blocks)]
    top=[i for _,i,_ in sorted(scored,key=lambda z:(-z[0],z[1]))[:min(n_priority,len(blocks))]]
    order=top+[i for i in range(len(blocks)) if i not in set(top)]
    changed_order=order!=list(range(len(blocks)))
    header=header.replace("Ordered by Time (Earliest to Latest):",
        "Evidence blocks: first two prioritize proposition-token overlap; remaining blocks keep original order:")
    out=header+"\n"+"\n".join(renumber(blocks[i],j+1) for j,i in enumerate(order))
    return out,order,changed_order

SELECT_SYS="""You are an evidence selector, not the final clinical fact-verification judge.
Given one proposition, its current EHR reference, and additional RAW EHR passages, choose up to 3 candidate IDs whose raw text would materially improve judging the COMPLETE proposition.
Useful evidence may support, contradict, clarify time or certainty, or distinguish planned/refused/completed/changed events.
Do not select a passage merely because it repeats information already clear in the current reference. Do not infer or output a final Supported/Not Supported/Not Addressed label.
Return JSON only: {"selected":["C01"],"why":"short rationale"}. selected may be []."""

def candidate_text(short,p):
    return f"{short} | Date {p['date']} | {p['category']} | Note {p['note_id']} | {p['text']}"

def selector_body(claim,reference,rendered):
    payload=dict(proposition=claim,current_reference=reference,candidates=rendered)
    return dict(model=MODELS["qwen"],messages=[
        dict(role="system",content=SELECT_SYS),
        dict(role="user",content=json.dumps(payload,ensure_ascii=False))],
        temperature=0,max_tokens=450,enable_thinking=False,
        response_format={"type":"json_object"})

def display_line(i,p):
    return pc.display_line(i,p)

def sentence_window(p,claim,max_chars=520):
    text=p["text"];spans=[]
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)",text):
        if m.group(0).strip():spans.append((m.start(),m.end()))
    if not spans:return dict(p)
    q=tset(claim)
    best=max(range(len(spans)),key=lambda i:(len(q&tset(text[spans[i][0]:spans[i][1]])),spans[i][1]-spans[i][0]))
    lo=max(0,best-1);hi=min(len(spans)-1,best+1);a=spans[lo][0];b=spans[hi][1]
    if b-a>max_chars:a,b=spans[best]
    return dict(p,start=p["start"]+a,end_exclusive=p["start"]+b,text=text[a:b].strip())

def append_windows(base,selected_pids,corpus,claim,budget=1500,max_items=3):
    nums=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",base)]
    n=max(nums)+1 if nums else 1
    base_text={norm(m.group(1)) for m in re.finditer(r"\| Text: ([\s\S]*?)(?=\n\d+\. Date:|\Z)",base)}
    parts=[base.rstrip()];kept=[];used=0
    for pid in selected_pids:
        if pid not in corpus:continue
        w=sentence_window(corpus[pid],claim)
        if norm(w["text"]) in base_text:continue
        s=display_line(n+len(kept),w);L=len(s)+1
        if used+L>budget:continue
        parts.append(s);kept.append(dict(passage_id=pid,note_id=w["note_id"],
            start=w["start"],end_exclusive=w["end_exclusive"],text=w["text"]))
        used+=L
        if len(kept)>=max_items:break
    return "\n".join(parts),kept,used

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
    gt=[r["GT"] for r in rows];pr=[r[pred_key] for r in rows]
    out=dict(n=len(rows),correct=sum(a==b for a,b in zip(gt,pr)),
        PA=sum(a==b for a,b in zip(gt,pr))/len(rows),
        MCC=float(matthews_corrcoef(gt,pr)),
        false_S=sum(a!="Supported" and b=="Supported" for a,b in zip(gt,pr)))
    for lab in LABELS:
        den=sum(a==lab for a in gt)
        out["recall_"+lab.replace(" ","_")]=sum(a==lab and b==lab for a,b in zip(gt,pr))/den if den else None
    return out
