"""Freeze 046 first-batch cohort, D48 extra candidates, and selector/planner jobs."""
from pathlib import Path
import json,hashlib,re,copy
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen"
R044=ROOT/"outputs/044_incremental_evidence_recovery"
R045=ROOT/"outputs/045_semantic_recovery_screen"
R031=ROOT/"outputs/031_training_expansion_confirmation"

def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hh(s):return hashlib.sha256(s.encode()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def norm(s):return re.sub(r"\s+"," ",s).strip()
def candidate_text(short,p):
    return f"{short} | Date {p['date']} | {p['category']} | Note {p['note_id']} | {p['text']}"
R1_SYS="""You are an evidence selector, not the final fact-verification judge.
Given a clinical proposition, the current evidence reference, and additional candidate EHR passages, choose up to 3 candidate IDs whose RAW TEXT would materially improve judging the COMPLETE proposition. Useful evidence may support, contradict, clarify timing/qualifiers, or establish that an event was planned, refused, completed, or changed.
Do not choose passages merely because they repeat current evidence. Do not infer a final Supported/Not Supported/Not Addressed label.
Return JSON only: {"selected":["C01"],"why":"short rationale"}. selected may be []."""

R2_SYS="""You are a requirement-aware clinical evidence selector, not the final judge.
First identify only the material facts, time relations, event states, qualifiers, certainty, or relations ACTUALLY asserted by the proposition; do not invent additional requirements.
Then compare the current reference with candidate EHR passages and choose up to 3 candidate IDs that fill an unresolved requirement or provide material confirming/disconfirming evidence. A plan is distinct from completion; possibility is distinct from certainty; an explicit refusal/cancellation may be material counterevidence to a claim of performance.
Return JSON only: {"requirements":["..."],"unresolved":["..."],"selected":["C01"],"why":"..."}. selected may be []."""

R4_SYS="""You select a SMALL COMPLEMENTARY SET of raw EHR passages for fact verification; you are not the final judge.
Some propositions require multiple records together: before/after values, plan versus execution, early versus later state, treatment plus outcome, or a relation between entities. From the candidates, choose up to 3 IDs that form the most useful joint evidence set beyond the current reference. Prefer complementary evidence over individually repetitive passages. Include contradiction when material. Do not decide the final label.
Return JSON only: {"relation":"what joint relation matters, or none","selected":["C01","C07"],"why":"..."}. selected may be []."""

R6_SYS="""You generate targeted SAME-ADMISSION EHR search queries, not a final verification label.
Given a proposition and the current evidence reference, identify at most one unresolved evidence gap that a broader search could clarify. The current reference may already contain enough evidence; if so return no queries. Preserve event status, time, numeric and certainty distinctions. Search for confirming OR disconfirming evidence.
Return JSON only: {"gap":"short description or none","queries":["query1","query2"]}. At most 2 queries."""
def select_greedy(pool,targets,counts,used,prefix):
    out=[]
    for n,(gt,author) in enumerate(targets):
        cand=[x for x in pool if x["GT"]==gt and x["id"] not in used and counts[x["sid"]]<3 and (author is None or x["author"]==author)]
        if not cand and author is not None:
            cand=[x for x in pool if x["GT"]==gt and x["id"] not in used and counts[x["sid"]]<3]
        if not cand:raise RuntimeError("cannot fill target "+str((gt,author)))
        cand.sort(key=lambda x:(hh(prefix+x["id"]),x["id"]))
        z=cand[0];out.append(z);used.add(z["id"]);counts[z["sid"]]+=1
    return out

def main():
    if any(OUT.iterdir()):raise RuntimeError("046 output not empty")
    cases={x["id"]:x for x in lines(R044/"planning_001/eval_cases.jsonl")}
    score=read(R044/"results_recovery_001/score_rows.json")
    pred={(x["id"],x["condition"]):x for x in score if x["round"]==0 and x.get("Score")}
    allrows=[dict(id=i,sid=c["sid"],author=c["author"],GT=c["GT"],base=pred[(i,"base")]["Score"]) for i,c in cases.items() if (i,"base") in pred]
    # Retrieval-sensitive anchors: base wrong but the historical simple rank append corrected.
    sens=[x for x in allrows if (x["id"],"rank") in pred and x["base"]!=x["GT"] and pred[(x["id"],"rank")]["Score"]==x["GT"]]
    # Judge-error controls are the two D rescues found in 045; use as controls, not retrieval wins.
    dchanged=[x for x in read(R045/"analysis_summary.json")["changed_cases"] if x["route"]=="D" and x["new_correct"] and not x["base_correct"]]
    judge_ids={x["id"] for x in dchanged};sens=[x for x in sens if x["id"] not in judge_ids]
    counts=Counter();used=set()
    targets=[("Supported","human"),("Not Supported","human"),("Supported","human"),
             ("Supported","llm"),("Supported","llm"),("Not Addressed","llm")]
    retrieval=select_greedy(sens,targets,counts,used,"046/retrieval/v1:")
    judge=[x for x in allrows if x["id"] in judge_ids]
    judge.sort(key=lambda x:x["id"])
    for x in judge:
        if x["id"] not in used:used.add(x["id"]);counts[x["sid"]]+=1
    if len(judge)!=2:raise RuntimeError("judge controls drift")
    correct=[x for x in allrows if x["base"]==x["GT"] and x["id"] not in used]
    protect_targets=[("Supported","human"),("Supported","human"),("Supported","llm"),("Supported","llm"),
                     ("Not Supported","human"),("Not Supported","llm"),("Not Addressed","human"),("Not Addressed","human")]
    protection=select_greedy(correct,protect_targets,counts,used,"046/protect/v1:")
    cohort_ids=[x["id"] for x in retrieval+judge+protection]
    assert len(cohort_ids)==16 and len(set(cohort_ids))==16 and max(counts.values())<=3
    candidates={x["proposition_id"]:x for x in lines(R031/"retrieval_001/candidates.jsonl")}
    corpus={x["passage_id"]:x for x in lines(R031/"materials_001/corpus.jsonl")}
    mapping=[x for x in lines(R044/"eval_score/mapping.jsonl") if x["condition"]=="base" and x["round"]==0]
    base_rid={x["id"]:x["request_id"] for x in mapping};jobs044={x["request_id"]:x for x in lines(R044/"eval_score/jobs.jsonl")}
    cohort=[];jobs=[];repeats=set(sorted(cohort_ids,key=lambda i:hh("046/repeat/v1:"+i))[:4])
    for pid in cohort_ids:
        c=cases[pid];base=pred[(pid,"base")];cids=candidates[pid]["candidate_ids"]["C48"]
        base_texts={norm(corpus[x]["text"]) for x in c["base_ids"]}
        extras=[x for x in cids if x not in set(c["base_ids"]) and norm(corpus[x]["text"]) not in base_texts]
        short={f"C{k+1:02d}":x for k,x in enumerate(extras)}
        rendered=[candidate_text(s,corpus[p]) for s,p in short.items()]
        typ="retrieval_sensitive" if pid in {x["id"] for x in retrieval} else "judge_error_control" if pid in judge_ids else "protection"
        cohort.append(dict(id=pid,sid=c["sid"],author=c["author"],GT=c["GT"],type=typ,claim=c["claim"],base_reference=c["base"],
          base_ids=c["base_ids"],base_verdict=base["Score"],base_scores=base["scores"],base_reason=base.get("reason"),base_checks=base.get("checks"),
          base_request_id=base_rid[pid],extra_short_to_pid=short,extra_candidates=rendered))
        payload=dict(proposition=c["claim"],current_reference=c["base"],candidates=rendered)
        for route,system,max_tokens in (("R1",R1_SYS,450),("R2",R2_SYS,650),("R4",R4_SYS,500)):
            body=dict(model="qwen3.8-27b",messages=[dict(role="system",content=system),dict(role="user",content=json.dumps(payload,ensure_ascii=False))],
              temperature=0,max_tokens=max_tokens,enable_thinking=False,response_format={"type":"json_object"})
            jobs.append(dict(request_id=f"046_{route}_"+hh(pid)[:24],route=route,kind="selector",model_key="qwen",id=pid,body=body))
        p6=dict(proposition=c["claim"],current_reference=c["base"])
        body=dict(model="qwen3.8-27b",messages=[dict(role="system",content=R6_SYS),dict(role="user",content=json.dumps(p6,ensure_ascii=False))],
          temperature=0,max_tokens=350,enable_thinking=False,response_format={"type":"json_object"})
        jobs.append(dict(request_id="046_R6plan_"+hh(pid)[:24],route="R6plan",kind="planner",model_key="qwen",id=pid,body=body))
        if pid in repeats:
            jobs.append(dict(request_id="046_repeat_"+hh(pid)[:24],route="baseline_repeat",kind="judge",model_key="deepseek",
              id=pid,body=copy.deepcopy(jobs044[base_rid[pid]]["body"])))
    jsonl(OUT/"cohort.jsonl",cohort);jsonl(OUT/"stage1_jobs.jsonl",jobs)
    sources=[R044/"planning_001/eval_cases.jsonl",R044/"results_recovery_001/score_rows.json",R044/"eval_score/jobs.jsonl",
      R031/"retrieval_001/candidates.jsonl",R031/"materials_001/corpus.jsonl",R045/"analysis_summary.json"]
    put(OUT/"freeze.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      cohort_n=16,types=dict(Counter(x["type"] for x in cohort)),patients=dict(counts),repeat_ids=sorted(repeats),stage1_jobs=len(jobs),
      budget_cny=8,GT_not_in_API=True,sources={str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in sources},
      protocol_sha=sha(ROOT/"tasks/046_requirement_aware_retrieval_screen/protocol.md")))
    print("046 frozen",dict(Counter(x["type"] for x in cohort)),dict(counts),"jobs",len(jobs),flush=True)
if __name__=="__main__":main()
