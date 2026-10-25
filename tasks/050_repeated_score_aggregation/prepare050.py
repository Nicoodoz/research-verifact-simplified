"""Freeze 050 screen/control cohort, confirmation cohort, and six identical screen scoring rounds."""
from pathlib import Path
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/050_repeated_score_aggregation"))
import common050 as c
R044=ROOT/"outputs/044_incremental_evidence_recovery"
R048=ROOT/"outputs/048_end_to_end_evidence_recovery"

def choose_controls(pool,sid,target,prefix):
    cand=[x for x in pool if x["sid"]==sid]
    chosen=[]
    for lab in ("Supported","Not Supported","Not Addressed"):
        z=[x for x in cand if x["historical_raw"]==lab and x["id"] not in {q["id"] for q in chosen}]
        z.sort(key=lambda x:(c.stable(prefix+lab+":",x["id"]),x["id"]))
        if z and len(chosen)<target:chosen.append(z[0])
    rest=[x for x in cand if x["id"] not in {q["id"] for q in chosen}]
    rest.sort(key=lambda x:(c.stable(prefix+"fill:",x["id"]),x["id"]))
    chosen.extend(rest[:max(0,target-len(chosen))])
    c.require(len(chosen)==target,"control quota failed "+sid)
    return chosen

def main():
    if any(c.OUT.iterdir()):raise RuntimeError("050 output not empty")
    cases044={x["id"]:x for x in c.lines(R044/"planning_001/eval_cases.jsonl")}
    rows=c.read(R044/"results_recovery_001/score_rows.json")
    base=[x for x in rows if x["round"]==0 and x["condition"]=="base" and x.get("Score") and x.get("scores")]
    meta={}
    for r in base:
        x=cases044[r["id"]]
        meta[r["id"]]=dict(id=r["id"],sid=x["sid"],author=x["author"],GT=x["GT"],claim=x["claim"],
          base_reference=x["base"],historical_raw=r["Score"],historical_U2=c.ulabel(r["scores"],2),
          historical_U0=c.ulabel(r["scores"],0),historical_scores=r["scores"])

    f48=c.read(R048/"freeze.json")
    screen_patients=set(f48["screen_patients"]);confirm_patients=set(f48["confirmation_patients"])
    screen_conflict_ids={x["id"] for x in c.lines(R048/"screen_cases.jsonl")}
    confirm_conflict_ids={x["id"] for x in c.lines(R048/"confirmation_cases_frozen.jsonl")}
    c.require(len(screen_conflict_ids)==16 and len(confirm_conflict_ids)==29,"048 conflict counts drift")

    stable=[x for x in meta.values() if x["historical_raw"]==x["historical_U2"]]
    screen_controls=[]
    for sid in sorted(screen_patients):
        screen_controls.extend(choose_controls(stable,sid,4,"050/screen/control/v1:"+sid+":"))
    c.require(len(screen_controls)==16,"screen controls")

    confirm_counts=Counter(meta[i]["sid"] for i in confirm_conflict_ids)
    confirm_controls=[]
    for sid in sorted(confirm_patients):
        confirm_controls.extend(choose_controls(stable,sid,confirm_counts[sid],"050/confirm/control/v1:"+sid+":"))
    c.require(len(confirm_controls)==29,"confirmation controls")

    screen=[dict(meta[i],cohort_type="historical_conflict") for i in sorted(screen_conflict_ids)]
    screen += [dict(x,cohort_type="stable_control") for x in screen_controls]
    confirm=[dict(meta[i],cohort_type="historical_conflict") for i in sorted(confirm_conflict_ids)]
    confirm += [dict(x,cohort_type="stable_control") for x in confirm_controls]
    c.require(len(screen)==32 and len(confirm)==58,"cohort size")
    c.require(not({x["id"] for x in screen}&{x["id"] for x in confirm}),"case overlap")
    c.require({x["sid"] for x in screen}<=screen_patients and {x["sid"] for x in confirm}<=confirm_patients,"patient split")

    jobs=[]
    for x in screen:
        body=c.score_body(x["claim"],x["base_reference"])
        bh=c.digest(body)
        for rnd in range(6):
            jobs.append(dict(request_id=f"050_screen_r{rnd}_"+c.stable("",x["id"])[:24],
              stage="screen_score",kind="judge",model_key="deepseek",id=x["id"],round=rnd,
              body_hash=bh,body=body))
    jobs.sort(key=lambda j:c.stable("050/joborder/v1:",j["request_id"]))
    # Exact same body required across all 6 rounds of each item.
    by=defaultdict(set)
    for j in jobs:by[j["id"]].add(j["body_hash"])
    c.require(all(len(v)==1 for v in by.values()),"body mismatch across repeats")

    c.jsonl(c.OUT/"screen_cases.jsonl",screen)
    c.jsonl(c.OUT/"confirmation_cases_frozen.jsonl",confirm)
    c.jsonl(c.OUT/"screen_score_jobs.jsonl",jobs)
    bound=sum(c.bound(j) for j in jobs);c.require(bound<=c.SCREEN_CAP,"screen bound exceeds cap")
    c.put(c.OUT/"freeze.json",dict(created_utc=c.now(),screen_n=len(screen),confirmation_n=len(confirm),
      screen_patients=sorted(screen_patients),confirmation_patients=sorted(confirm_patients),
      screen_conflict_n=16,screen_control_n=16,confirmation_conflict_n=29,confirmation_control_n=29,
      screen_jobs=len(jobs),screen_bound_cny=bound,screen_cap_cny=c.SCREEN_CAP,total_cap_cny=c.TOTAL_CAP,
      selection_uses_GT=False,GT_not_in_API=True,
      screen_historical_labels=dict(Counter(x["historical_raw"] for x in screen)),
      confirmation_historical_labels=dict(Counter(x["historical_raw"] for x in confirm)),
      protocol_sha256=c.sha(ROOT/"tasks/050_repeated_score_aggregation/protocol.md")))
    print("050 PREPARED",dict(screen=len(screen),confirm=len(confirm),jobs=len(jobs),
      screen_patients=sorted(screen_patients),confirm_patients=sorted(confirm_patients),
      bound=round(bound,4)),flush=True)

if __name__=="__main__":main()
