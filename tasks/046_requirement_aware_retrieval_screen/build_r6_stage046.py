"""Parse stage1 and freeze R6 semantic rerank jobs over targeted full-EHR BM25 results."""
from pathlib import Path
import json,re,math,hashlib
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen";R031=ROOT/"outputs/031_training_expansion_confirmation"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/046_requirement_aware_retrieval_screen"))
import run046
STOP=set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should".split())
def toks(s):return [x for x in re.findall(r"[a-z]+|\d+(?:\.\d+)?",s.lower()) if x not in STOP]
def norm(s):return re.sub(r"\s+"," ",s).strip()
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
    with Path(p).open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def jsonl(p,rows):
    with Path(p).open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def hid(pid):return hashlib.sha256(pid.encode()).hexdigest()[:24]
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

RERANK_SYS="""You are the semantic reranking stage of a clinical EHR retrieval system, not the final fact-verification judge.
A broader lexical search produced candidate raw EHR passages for one unresolved evidence gap. Select up to 3 passage IDs whose raw text is most useful to judge the COMPLETE proposition. Evidence may support, contradict, clarify event completion, time, numeric values, relations or certainty. Do not choose repetitive passages merely for keyword overlap. Do not output a final Supported/Not Supported/Not Addressed label.
Return JSON only: {"selected":["P01"],"why":"short rationale"}. selected may be []."""

def main():
    if (OUT/"stage2_jobs.jsonl").exists():raise RuntimeError("stage2 exists")
    cohort={x["id"]:x for x in lines(OUT/"cohort.jsonl")};attempts,term=run046.state()
    assert all(j["request_id"] in term for j in lines(OUT/"stage1_jobs.jsonl"))
    corpus=lines(R031/"materials_001/corpus.jsonl");bysid=defaultdict(list)
    for p in corpus:bysid[str(p["subject_id"])].append(p)
    s1=[];jobs=[]
    for pid,x in cohort.items():
        row=dict(id=pid)
        for route in ("R1","R2","R4"):
            p=term[f"046_{route}_"+hid(pid)]["parsed"];obj=(p.get("parsed") or {}) if p.get("status")=="valid" else {}
            allowed=x["extra_short_to_pid"];sel=[z for z in obj.get("selected",[]) if z in allowed][:3]
            row[route]=dict(selected_short=sel,selected_pids=[allowed[z] for z in sel],raw=obj)
        pp=term["046_R6plan_"+hid(pid)]["parsed"];plan=(pp.get("parsed") or {}) if pp.get("status")=="valid" else {}
        queries=[str(q).strip() for q in plan.get("queries",[]) if str(q).strip()][:2]
        dates=re.findall(r"Hospital Admission Start: (\d{4}-\d{2}-\d{2})|Hospital Admission End: (\d{4}-\d{2}-\d{2})",x["base_reference"])
        flat=[z for pair in dates for z in pair if z];lo,hi=(flat[0],flat[1]) if len(flat)>=2 else ("0000-00-00","9999-99-99")
        base_text={norm(m.group(1)) for m in re.finditer(r"\| Text: ([\s\S]*?)(?=\n\d+\. Date:|\Z)",x["base_reference"])}
        pool=[p for p in bysid[x["sid"]] if lo<=p["date"]<=hi and norm(p["text"]) not in base_text]
        tops=[]
        if queries and pool:
            order,sc=bm25(pool,queries)
            for i in order:
                if sc[i]<=0:continue
                tops.append((pool[i],sc[i]))
                if len(tops)>=12:break
        short={f"P{k+1:02d}":p["passage_id"] for k,(p,_) in enumerate(tops)}
        rendered=[f"{s} | Date {p['date']} | {p['category']} | Note {p['note_id']} | {p['text']}" for s,(p,_) in zip(short,tops)]
        row["R6plan"]=dict(gap=plan.get("gap"),queries=queries,candidate_short_to_pid=short,
                           candidate_scores={s:score for s,(_,score) in zip(short,tops)},candidate_n=len(tops))
        if tops:
            payload=dict(proposition=x["claim"],current_reference=x["base_reference"],gap=plan.get("gap"),retrieved_candidates=rendered)
            body=dict(model="qwen3.8-27b",messages=[dict(role="system",content=RERANK_SYS),dict(role="user",content=json.dumps(payload,ensure_ascii=False))],
                      temperature=0,max_tokens=450,enable_thinking=False,response_format={"type":"json_object"})
            jobs.append(dict(request_id="046_R6rank_"+hid(pid),route="R6rank",kind="reranker",model_key="qwen",id=pid,body=body))
        s1.append(row)
    jsonl(OUT/"stage1_selections.jsonl",s1);jsonl(OUT/"stage2_jobs.jsonl",jobs)
    put(OUT/"stage2_freeze.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      R1_selected=dict(Counter(len(x["R1"]["selected_pids"]) for x in s1)),
      R2_selected=dict(Counter(len(x["R2"]["selected_pids"]) for x in s1)),
      R4_selected=dict(Counter(len(x["R4"]["selected_pids"]) for x in s1)),
      R6_query_cases=sum(bool(x["R6plan"]["queries"]) for x in s1),R6_rerank_jobs=len(jobs),
      cumulative_cost_cny=sum(a["cost"] for a in attempts),GT_used=False))
    print(json.dumps(read(OUT/"stage2_freeze.json"),ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
