"""Freeze 048 conflict-trigger cohort and stage1 baseline/query jobs."""
from pathlib import Path
from collections import Counter
import math,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c

def main():
    if any(c.OUT.iterdir()):raise RuntimeError("048 output not empty")
    cases={x["id"]:x for x in c.lines(c.R044/"planning_001/eval_cases.jsonl")}
    rows=c.read(c.R044/"results_recovery_001/score_rows.json")
    base=[x for x in rows if x["round"]==0 and x["condition"]=="base" and x.get("Score") and x.get("scores")]
    conflicts=[]
    for r in base:
        u2=c.ulabel(r["scores"],2)
        if r["Score"]!="Supported" and u2=="Supported":
            x=cases[r["id"]]
            conflicts.append(dict(id=r["id"],sid=x["sid"],author=x["author"],GT=x["GT"],
                claim=x["claim"],base_reference=x["base"],base_ids=x["base_ids"],
                historical_raw=r["Score"],historical_U0=c.ulabel(r["scores"],0),
                historical_U2=u2,historical_scores=r["scores"]))
    c.require(len(conflicts)==76,"conflict cohort drift")
    sids=sorted({x["sid"] for x in conflicts},key=lambda s:c.stable("048/patient/v1:",s))
    c.require(len(sids)==8,"expected 8 conflict patients")
    screen_patients=set(sids[:4]);confirm_patients=set(sids[4:])

    bysid={}
    for sid in screen_patients:
        pool=sorted([x for x in conflicts if x["sid"]==sid],
            key=lambda x:(c.stable("048/screen/v1:",x["id"]),x["id"]))
        c.require(len(pool)>=4,"screen patient has <4 conflicts")
        bysid[sid]=pool[:4]
    screen=[x for sid in sorted(screen_patients) for x in bysid[sid]]
    confirm=sorted([x for x in conflicts if x["sid"] in confirm_patients],
        key=lambda x:(c.stable("048/confirm/v1:",x["id"]),x["id"]))
    c.require(len(screen)==16 and len(confirm)==29,"screen/confirm size drift")
    inputs={x["proposition_id"]:x for x in c.lines(c.R031/"materials_001/inputs.jsonl")}
    candidates={x["proposition_id"]:x for x in c.lines(c.R031/"retrieval_001/candidates.jsonl")}
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    for x in screen+confirm:
        c.require(x["id"] in inputs and x["id"] in candidates,"missing 031 material")
        x["claim_embedding_id"]=inputs[x["id"]]["claim_embedding_id"]
        x["c48_candidate_ids"]=candidates[x["id"]]["candidate_ids"]["C48"]
        base_text={re.sub(r"\s+"," ",corpus[p]["text"]).strip() for p in x["base_ids"]}
        x["d48_extra_ids"]=[p for p in x["c48_candidate_ids"] if p not in set(x["base_ids"])
            and re.sub(r"\s+"," ",corpus[p]["text"]).strip() not in base_text]

    repeat_ids={x["id"] for x in sorted(screen,key=lambda z:c.stable("048/repeat/v1:",z["id"]))[:6]}
    jobs=[]
    for x in screen:
        pid=x["id"];h=c.stable("",pid)[:24]
        jobs.append(dict(request_id="048_B_"+h,stage="screen_stage1",kind="judge",
            model_key="deepseek",condition="B",id=pid,body=c.score_body(x["claim"],x["base_reference"])))
        jobs.append(dict(request_id="048_Q_"+h,stage="screen_stage1",kind="query",
            model_key="qwen",condition="query",id=pid,body=c.query_body(x["claim"])))
        if pid in repeat_ids:
            jobs.append(dict(request_id="048_Brep_"+h,stage="screen_stage1",kind="judge",
                model_key="deepseek",condition="B_repeat",id=pid,
                body=c.score_body(x["claim"],x["base_reference"])))
    c.jsonl(c.OUT/"screen_cases.jsonl",screen)
    c.jsonl(c.OUT/"confirmation_cases_frozen.jsonl",confirm)
    c.jsonl(c.OUT/"screen_stage1_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))

    sources=[
      c.R044/"planning_001/eval_cases.jsonl",
      c.R044/"results_recovery_001/score_rows.json",
      c.R031/"materials_001/inputs.jsonl",
      c.R031/"retrieval_001/candidates.jsonl",
      c.R031/"materials_001/corpus.jsonl",
      ROOT/"tasks/048_end_to_end_evidence_recovery/protocol.md"]
    c.put(c.OUT/"freeze.json",dict(created_utc=c.now(),trigger_n=len(conflicts),
      screen_patients=sorted(screen_patients),confirmation_patients=sorted(confirm_patients),
      screen_n=len(screen),confirmation_n=len(confirm),repeat_ids=sorted(repeat_ids),
      screen_stage1_jobs=len(jobs),screen_cap_cny=c.SCREEN_CAP,total_cap_cny=c.TOTAL_CAP,
      selection_uses_GT=False,GT_not_in_API=True,
      screen_gt_distribution=dict(Counter(x["GT"] for x in screen)),
      confirmation_gt_distribution=dict(Counter(x["GT"] for x in confirm)),
      source_sha256={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    print("048 PREPARED",dict(trigger=len(conflicts),screen=len(screen),confirm=len(confirm),
      screen_patients=sorted(screen_patients),confirm_patients=sorted(confirm_patients),
      jobs=len(jobs),screen_gt=dict(Counter(x["GT"] for x in screen))),flush=True)

if __name__=="__main__":main()
