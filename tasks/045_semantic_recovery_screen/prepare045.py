"""Freeze 045 16-claim diagnostic cohort and stage-1 API jobs."""
from pathlib import Path
import json,hashlib,copy
from collections import Counter,defaultdict

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/045_semantic_recovery_screen"
R044=ROOT/"outputs/044_incremental_evidence_recovery"

def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def jsonl(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

def make_body(base_body,reference,extra_system=None,model=None):
    b=copy.deepcopy(base_body)
    if model:b["model"]=model
    payload=json.loads(b["messages"][1]["content"]);payload["reference"]=reference
    b["messages"][1]["content"]=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
    if extra_system:b["messages"][0]["content"]+="\n\n"+extra_system
    return b
SCOPE="""Decision-scope rules for this run:
Judge only the material assertions actually made in the proposition. Do not add requirements that the proposition does not state.
A later change does not by itself negate a claim explicitly about an earlier time point.
A plan, recommendation, consideration, or possibility does not by itself prove a completed or certain event.
Conversely, semantically equivalent wording can support a claim without verbatim repetition.
Distinguish missing evidence from contradictory evidence: missing or unaddressed material belongs to Not Addressed, while Not Supported requires the fact to be addressed but not fully supported or contradicted.
When rejecting a proposition, identify the exact material component, qualifier, time relation, or certainty level that fails."""

SELECT_SYS="""You select optional additional EHR evidence for a later fact-verification Judge.
You do NOT decide the final Supported/Not Supported/Not Addressed label and you do not know the gold label.
Given a proposition, the current reference, and three candidate evidence bundles, choose exactly one of: none, rank, complement, time.
Choose a bundle only when its added raw EHR text materially helps judge the COMPLETE proposition, including support, contradiction, qualifiers, timing, or event completion. Avoid redundant evidence.
Return JSON only: {"choice":"none|rank|complement|time","need":"short description of what additional evidence is useful","why":"short rationale"}."""

GAP_SYS="""You create targeted EHR search queries after seeing a first-pass verification answer.
The first-pass answer is a fallible clue, not truth. Do NOT output a final verification label.
Identify the exact unresolved fact/relation/qualifier, and generate at most two short search queries for the same patient's target admission EHR. Queries should seek either confirming or disconfirming evidence and preserve time/status distinctions such as planned vs completed.
Return JSON only: {"gap":"short unresolved fact/relation, or none","queries":["query1","query2"]}.
If the reference already contains enough information and no targeted search is useful, return an empty queries list."""

QJ_SYS="""Verify one clinical proposition using only the supplied patient reference.
Labels:
Supported = reference supports the complete proposition.
Not Supported = reference addresses the claimed fact but does not fully support it or contradicts it.
Not Addressed = the material claimed fact is not addressed.
Do not add unstated requirements; plans are not completed events; later changes do not negate an explicitly earlier-time claim; missing is not contradiction.
Return JSON only with keys verdict, reason, checks, label_scores. verdict must be exactly one of the three labels. checks is a list of concise objects with aspect, assessment, evidence_ids. label_scores contains all three labels as integers summing to 100."""
def main():
    if OUT.exists() and any(OUT.iterdir()):raise RuntimeError("045 output not empty")
    cases={x["id"]:x for x in lines(R044/"planning_001/eval_cases.jsonl")}
    score_rows=read(R044/"results_recovery_001/score_rows.json")
    base={x["id"]:x for x in score_rows if x["condition"]=="base" and x["round"]==0 and x.get("Score")}
    mappings=[x for x in lines(R044/"eval_score/mapping.jsonl") if x["condition"]=="base" and x["round"]==0]
    rid={x["id"]:x["request_id"] for x in mappings}
    jobs044={x["request_id"]:x for x in lines(R044/"eval_score/jobs.jsonl")}
    available=[dict(id=i,GT=cases[i]["GT"],author=cases[i]["author"],sid=cases[i]["sid"],
                    correct=base[i]["Score"]==cases[i]["GT"]) for i in base]

    # Exact diagnostic quotas; no correct LLM Not-Addressed examples exist in this cohort.
    quota=[
      (False,"Supported","human"),(False,"Supported","human"),(False,"Supported","llm"),(False,"Supported","llm"),
      (False,"Not Supported","human"),(False,"Not Supported","llm"),
      (False,"Not Addressed","human"),(False,"Not Addressed","llm"),
      (True,"Supported","human"),(True,"Supported","human"),(True,"Supported","llm"),(True,"Supported","llm"),
      (True,"Not Supported","human"),(True,"Not Supported","llm"),
      (True,"Not Addressed","human"),(True,"Not Addressed","human")
    ]
    counts=Counter();chosen=[]
    for q in quota:
        correct,lab,author=q
        pool=[x for x in available if x["correct"]==correct and x["GT"]==lab and x["author"]==author and x["id"] not in {z["id"] for z in chosen} and counts[x["sid"]]<3]
        pool.sort(key=lambda x:(h("045/cohort/v1:"+x["id"]),x["id"]))
        if not pool:raise RuntimeError("quota impossible "+str(q))
        x=pool[0];chosen.append(x);counts[x["sid"]]+=1
    assert len(chosen)==16 and max(counts.values())<=3
    cohort=[];stage1=[]
    repeat_ids={x["id"] for x in sorted(chosen,key=lambda z:h("045/repeat/v1:"+z["id"]))[:4]}
    for x in chosen:
        c=cases[x["id"]];b=base[x["id"]];base_body=jobs044[rid[x["id"]]]["body"]
        tails={k:v["reference"][len(c["base"]):].strip() for k,v in c["packs"].items()}
        row=dict(id=x["id"],sid=x["sid"],author=x["author"],GT=x["GT"],base_correct=x["correct"],
          claim=c["claim"],base_reference=c["base"],base_verdict=b["Score"],base_reason=b.get("reason"),base_checks=b.get("checks"),
          base_request_id=rid[x["id"]],tails=tails,packs={k:dict(ids=v["ids"],added_chars=v["added_chars"]) for k,v in c["packs"].items()})
        cohort.append(row)

        bodyA=make_body(base_body,c["base"],SCOPE)
        stage1.append(dict(request_id="045_A_"+h(x["id"])[:24],route="A",kind="judge",model_key="deepseek",id=x["id"],body=bodyA))

        select_payload=dict(proposition=c["claim"],current_reference=c["base"],candidate_bundles=tails)
        bodyB=dict(model="qwen3.8-27b",messages=[dict(role="system",content=SELECT_SYS),dict(role="user",content=json.dumps(select_payload,ensure_ascii=False))],
          temperature=0,max_tokens=350,enable_thinking=False,response_format={"type":"json_object"})
        stage1.append(dict(request_id="045_Bsel_"+h(x["id"])[:24],route="B_selector",kind="selector",model_key="qwen",id=x["id"],body=bodyB))

        gap_payload=dict(proposition=c["claim"],current_reference=c["base"],first_pass=dict(verdict=b["Score"],reason=b.get("reason"),checks=b.get("checks")))
        bodyC=dict(model="qwen3.8-27b",messages=[dict(role="system",content=GAP_SYS),dict(role="user",content=json.dumps(gap_payload,ensure_ascii=False))],
          temperature=0,max_tokens=300,enable_thinking=False,response_format={"type":"json_object"})
        stage1.append(dict(request_id="045_Cgap_"+h(x["id"])[:24],route="C_gap",kind="gap",model_key="qwen",id=x["id"],body=bodyC))

        qpayload=dict(proposition=c["claim"],reference=c["base"])
        bodyD=dict(model="qwen3.8-27b",messages=[dict(role="system",content=QJ_SYS),dict(role="user",content=json.dumps(qpayload,ensure_ascii=False))],
          temperature=0,max_tokens=1300,enable_thinking=False,response_format={"type":"json_object"})
        stage1.append(dict(request_id="045_D_"+h(x["id"])[:24],route="D",kind="qjudge",model_key="qwen",id=x["id"],body=bodyD))

        if x["id"] in repeat_ids:
            stage1.append(dict(request_id="045_repeat_"+h(x["id"])[:24],route="baseline_repeat",kind="judge",model_key="deepseek",id=x["id"],body=copy.deepcopy(base_body)))
    OUT.mkdir(parents=True,exist_ok=True)
    jsonl(OUT/"cohort.jsonl",cohort);jsonl(OUT/"stage1_jobs.jsonl",stage1)
    sources=[R044/"planning_001/eval_cases.jsonl",R044/"results_recovery_001/score_rows.json",R044/"eval_score/mapping.jsonl",
             R044/"eval_score/jobs.jsonl",ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"]
    put(OUT/"freeze.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      cohort_n=16,patient_counts=dict(counts),quota=quota,repeat_ids=sorted(repeat_ids),stage1_jobs=len(stage1),budget_cny=8,
      sources={str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in sources},
      protocol_sha=sha(ROOT/"tasks/045_semantic_recovery_screen/protocol.md"),GT_not_in_API=True))
    print("045 FROZEN",Counter((x["base_correct"],x["GT"],x["author"]) for x in chosen),"patients",dict(counts),"stage1",len(stage1))
if __name__=="__main__":main()
