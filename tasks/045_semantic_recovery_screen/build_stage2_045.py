"""Parse 045 stage1 and freeze only necessary B/C final-Judge jobs."""
from pathlib import Path
import json,re,math,copy,hashlib
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/045_semantic_recovery_screen";R044=ROOT/"outputs/044_incremental_evidence_recovery"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/045_semantic_recovery_screen"))
import run045

def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def jsonl(p,rows):
    with Path(p).open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
STOP=set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should".split())
def toks(s):return [x for x in re.findall(r"[a-z]+|\d+(?:\.\d+)?",s.lower()) if x not in STOP]
def display(i,p):return f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"
def norm(s):return re.sub(r"\s+"," ",s).strip()
def bm25(passages,queries):
    counts=[Counter(toks(p["search_text"])) for p in passages];lens=[sum(x.values()) for x in counts];avg=sum(lens)/max(1,len(lens))
    post=defaultdict(list)
    for i,c in enumerate(counts):
        for t,n in c.items():post[t].append((i,n))
    score=[0.0]*len(passages)
    for query in queries:
        local=[0.0]*len(passages)
        for t in set(toks(query)):
            es=post.get(t,[]);idf=math.log(1+(len(passages)-len(es)+.5)/(len(es)+.5))
            for i,n in es:local[i]+=idf*n*2.2/(n+1.2*(.25+.75*lens[i]/max(1,avg)))
        for i,v in enumerate(local):score[i]+=v
    return sorted(range(len(passages)),key=lambda i:(-score[i],passages[i]["passage_id"])),score

def judge_body(base_body,reference):
    b=copy.deepcopy(base_body);payload=json.loads(b["messages"][1]["content"]);payload["reference"]=reference
    b["messages"][1]["content"]=json.dumps(payload,ensure_ascii=False,separators=(",",":"));return b

def main():
    if (OUT/"stage2_jobs.jsonl").exists():raise RuntimeError("stage2 frozen")
    cohort={x["id"]:x for x in lines(OUT/"cohort.jsonl")}
    attempts,term=run045.state()
    assert all(j["request_id"] in term for j in lines(OUT/"stage1_jobs.jsonl"))
    jobs044={x["request_id"]:x for x in lines(R044/"eval_score/jobs.jsonl")}
    corpus=lines(ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl")
    bysid=defaultdict(list)
    for p in corpus:bysid[str(p["subject_id"])].append(p)
    selections=[];jobs=[]
    for pid,x in cohort.items():
        # B semantic bundle choice
        rb=term["045_Bsel_"+hashlib.sha256(pid.encode()).hexdigest()[:24]]["parsed"]
        choice=(rb.get("parsed") or {}).get("choice","none") if rb.get("status")=="valid" else "none"
        if choice not in ("none","rank","complement","time"):choice="none"
        bref=x["base_reference"] if choice=="none" else x["base_reference"].rstrip()+"\n"+x["tails"][choice]
        selections.append(dict(id=pid,route="B",choice=choice,reference_changed=choice!="none",
          selector=(rb.get("parsed") or {}),added_chars=max(0,len(bref)-len(x["base_reference"]))))
        if choice!="none":
            body=judge_body(jobs044[x["base_request_id"]]["body"],bref)
            jobs.append(dict(request_id="045_Bfinal_"+hashlib.sha256(pid.encode()).hexdigest()[:24],route="B",kind="judge",model_key="deepseek",id=pid,body=body))

        # C feedback-guided query + local BM25
        rc=term["045_Cgap_"+hashlib.sha256(pid.encode()).hexdigest()[:24]]["parsed"]
        obj=(rc.get("parsed") or {}) if rc.get("status")=="valid" else {}
        queries=[str(q).strip() for q in obj.get("queries",[]) if str(q).strip()][:2]
        base_dates=re.findall(r"Hospital Admission Start: (\d{4}-\d{2}-\d{2})|Hospital Admission End: (\d{4}-\d{2}-\d{2})",x["base_reference"])
        flat=[z for tup in base_dates for z in tup if z];lo,hi=(flat[0],flat[1]) if len(flat)>=2 else ("0000-00-00","9999-99-99")
        pool=[p for p in bysid[x["sid"]] if lo<=p["date"]<=hi]
        base_text={norm(m.group(1)) for m in re.finditer(r"\| Text: ([\s\S]*?)(?=\n\d+\. Date:|\Z)",x["base_reference"])}
        pool=[p for p in pool if norm(p["text"]) not in base_text]
        picked=[];scores={}
        if queries and pool:
            order,sc=bm25(pool,queries)
            used=0
            for i in order:
                if sc[i]<=0:continue
                line=display(len(picked)+1,pool[i]);L=len(line)+1
                if used+L>1500:continue
                picked.append(pool[i]);scores[pool[i]["passage_id"]]=sc[i];used+=L
                if len(picked)>=2:break
        cref=x["base_reference"]
        if picked:
            nums=[int(z) for z in re.findall(r"(?m)^(\d+)\. Date:",cref)];start=max(nums)+1 if nums else 1
            cref=cref.rstrip()+"\n"+"\n".join(display(start+k,p) for k,p in enumerate(picked))
        selections.append(dict(id=pid,route="C",queries=queries,gap=obj.get("gap"),reference_changed=bool(picked),
          passage_ids=[p["passage_id"] for p in picked],scores=scores,added_chars=max(0,len(cref)-len(x["base_reference"]))))
        if picked:
            body=judge_body(jobs044[x["base_request_id"]]["body"],cref)
            jobs.append(dict(request_id="045_Cfinal_"+hashlib.sha256(pid.encode()).hexdigest()[:24],route="C",kind="judge",model_key="deepseek",id=pid,body=body))
    jsonl(OUT/"stage2_selections.jsonl",selections);jsonl(OUT/"stage2_jobs.jsonl",jobs)
    put(OUT/"stage2_freeze.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      jobs=len(jobs),B_choices=dict(Counter(x.get("choice") for x in selections if x["route"]=="B")),
      C_changed=sum(x["reference_changed"] for x in selections if x["route"]=="C"),
      stage1_cost_cny=sum(a["cost"] for a in attempts),GT_used_to_build_stage2=False))
    print(json.dumps(read(OUT/"stage2_freeze.json"),ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
