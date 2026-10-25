from pathlib import Path
import csv,hashlib,json,math,re,sys,datetime
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/065_verification_evidence_construction"
R044=ROOT/"outputs/044_incremental_evidence_recovery"
R031=ROOT/"outputs/031_training_expansion_confirmation"
CAP=15.0
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"}
PRICES={"deepseek":(3,9),"qwen":(3,12)}
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c48
sys.path.insert(0,str(ROOT/"tasks/039_full_ehr_attribution"))
import common039 as c39
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc
canonical=c48.canonical
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(prefix,x):return hashlib.sha256((prefix+str(x)).encode()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
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
    rows=list(rows)
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def require(x,msg):
    if not x:raise RuntimeError(msg)
def score_body(claim,reference):
    b=c48.score_body(claim,reference);b["model"]=MODELS["deepseek"];return b
def parse_score(tr):
    p=core024.parse(tr,True)
    if p.get("model_returned") not in (None,MODELS["deepseek"]):
        p["status"]="invalid_core_fields";p.setdefault("errors",[]).append("unexpected_model")
    return p
def query_body(claim):
    b=c39.query_body(claim);b["model"]=MODELS["qwen"];return b

COMPOSER_SYSTEM = (
"You are an evidence composer for clinical fact verification, not the final judge. "
"Given one proposition, its material verification requirements, and raw EHR candidate passages, "
"select a SMALL MINIMAL-SUFFICIENT evidence set for a separate verifier. "
"Select 3-8 candidate IDs when possible. Preserve direct evidence for every material requirement, "
"including material contradiction or counterevidence. Prefer explicit raw evidence over merely related background. "
"Avoid redundancy and noisy context. A plan or order is not completion; possibility is not certainty; "
"preserve dates, temporal order, negation, numeric trends, and scope. "
"Do NOT output Supported, Not Supported, or Not Addressed and do not decide the proposition. "
"Return JSON only with keys selected, coverage, why."
)
def composer_body(claim,requirements,candidates):
    payload={"proposition":claim,"requirements":requirements,"candidates":candidates}
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
    if t.startswith("'''"):
        pass
    if t.startswith("```"):
        t=re.sub(r"^```(?:json)?\s*","",t)
        t=re.sub(r"\s*```$","",t)
    try:return json.loads(t)
    except Exception:
        lo,hi=t.find("{"),t.rfind("}")
        require(lo>=0 and hi>lo,"no json");return json.loads(t[lo:hi+1])
def parse_query(tr):
    out={"status":"invalid","requirements":[],"queries":[],"errors":[]}
    try:
        content,model,usage=outer(tr);o=clean_json(content)
        req=o.get("requirements");qs=o.get("queries")
        require(isinstance(req,list) and 1<=len(req)<=6,"bad requirements")
        require(isinstance(qs,list) and 1<=len(qs)<=4,"bad queries")
        out.update(status="valid",requirements=req,queries=qs,model_returned=model,usage=usage,output_text=content)
    except Exception as e:out["errors"].append(type(e).__name__+":"+str(e)[:180])
    return out
def parse_composer(tr,job):
    out={"status":"invalid","selected":[],"coverage":[],"errors":[]}
    try:
        content,model,usage=outer(tr);o=clean_json(content);sel=o.get("selected")
        require(isinstance(sel,list) and 1<=len(sel)<=8,"bad selected")
        allowed=job["candidate_lookup"];sel=[str(x) for x in sel]
        require(all(x in allowed for x in sel),"unknown selected id")
        sel=list(dict.fromkeys(sel));require(1<=len(sel)<=8,"dedup selected bad")
        out.update(status="valid",selected=sel,coverage=o.get("coverage",[]),why=o.get("why"),
                   model_returned=model,usage=usage,output_text=content)
    except Exception as e:out["errors"].append(type(e).__name__+":"+str(e)[:180])
    return out
def parse(job,tr):
    if tr.get("http_status")!=200:return {"status":"invalid","errors":["no_http200"]}
    if job["kind"]=="judge":return parse_score(tr)
    if job["kind"]=="planner":return parse_query(tr)
    if job["kind"]=="composer":return parse_composer(tr,job)
    raise ValueError(job["kind"])
def bound(job):
    ip,op=PRICES[job["model_key"]];b=job["body"]
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",1500)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[job["model_key"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)
def norm(s):return re.sub(r"\s+"," ",s).strip()
def candidate_line(cid,p):
    return f"{cid} | Date {p['date']} | Time {p['time']} | {p['category']} | Note {p['note_id']} | Text: {p['text']}"
def final_line(i,p):
    return f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"
def build_reference(selected_pids,corpus,max_chars=4000,max_items=8):
    objs=[corpus[p] for p in selected_pids if p in corpus]
    objs.sort(key=lambda p:(str(p.get("date","")),str(p.get("time","")),
                            str(p.get("note_id","")),int(p.get("start",0))))
    parts=[];kept=[];used=0
    for p in objs:
        line=final_line(len(parts)+1,p);L=len(line)+1
        if parts and used+L>max_chars:continue
        if not parts and L>max_chars:
            q=dict(p);q["text"]=str(p["text"])[:max(100,max_chars-250)]
            line=final_line(1,q);L=len(line)+1
        parts.append(line);kept.append(p["passage_id"]);used+=L
        if len(parts)>=max_items:break
    require(parts,"empty reference")
    return "\n".join(parts),kept,used
