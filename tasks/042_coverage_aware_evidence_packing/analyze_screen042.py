"""Connect GT only after screen prediction freeze, evaluate selectors and apply preregistered gate."""
from collections import Counter,defaultdict
import common042 as c
import api042

PLAN=c.OUT/"planning_001";OUT=c.OUT/"screen_analysis_001"
GTFILE=c.ROOT/"outputs/033_gate_training_subset/evaluation_001/full_rows.jsonl"

def main():
    c.require(not OUT.exists(),"screen analysis exists");OUT.mkdir(parents=True)
    attempts,terminal=api042.state();jobs=c.lines(PLAN/"screen_jobs.jsonl")
    c.require(len(terminal)==len(jobs) and all(terminal[j["request_id"]]["parsed"]["status"] in c.VALID for j in jobs),"screen incomplete/invalid")
    logical=c.lines(PLAN/"screen_logical.jsonl");blind={r["id"]:r for r in c.lines(PLAN/"screen_cohort_blind.jsonl")}
    gt={r["proposition_id"]:r for r in c.lines(GTFILE)}
    c.require(set(blind)<=set(gt),"GT coverage")
    rows=[]
    for x in logical:
        p=terminal[x["request_id"]]["parsed"];g=gt[x["id"]]
        scores=p["scores"];u0=c.ulabel(scores,0);u2=c.ulabel(scores,2)
        rows.append(dict(**x,GT=g["human_gt"],score_verdict=p["verdict"],U0=u0,U2=u2,
          score_Supported=scores["Supported"],score_Not_Supported=scores["Not Supported"],score_Not_Addressed=scores["Not Addressed"],
          U2_reason_mismatch=(u2!=p["verdict"]),reason=p["parsed"].get("reason")))
    c.csvwrite(OUT/"predictions.csv",rows)
    mets=[]
    for cond in ("baseline","softnote","covmmr"):
        rr=[r for r in rows if r["condition"]==cond]
        for pred in ("score_verdict","U0","U2"):
            m=c.metrics(rr,pred);m.update(condition=cond,prediction=pred,
              U2_reason_mismatch=sum(r["U2_reason_mismatch"] for r in rr))
            mets.append(m)
    c.csvwrite(OUT/"metrics.csv",mets)
    by={(r["id"],r["condition"]):r for r in rows}
    base=[by[(pid,"baseline")] for pid in blind]
    base_correct=sum(r["U2"]==r["GT"] for r in base);base_false=sum(r["GT"]!="Supported" and r["U2"]=="Supported" for r in base)
    base_mismatch=sum(r["U2_reason_mismatch"] for r in base)
    decisions=[]
    for cond in ("softnote","covmmr"):
        cand=[by[(pid,cond)] for pid in blind]
        correct=sum(r["U2"]==r["GT"] for r in cand);false=sum(r["GT"]!="Supported" and r["U2"]=="Supported" for r in cand)
        mismatch=sum(r["U2_reason_mismatch"] for r in cand)
        author={}
        for a in ("human","llm"):
            ids=[pid for pid,z in blind.items() if z["author"]==a]
            author[a]=sum(by[(pid,cond)]["U2"]==by[(pid,cond)]["GT"] for pid in ids)-sum(by[(pid,"baseline")]["U2"]==by[(pid,"baseline")]["GT"] for pid in ids)
        d=dict(condition=cond,net_correct=correct-base_correct,false_S_delta=false-base_false,
               mismatch_delta=mismatch-base_mismatch,author_net=author)
        d["pass"]=d["net_correct"]>=5 and d["false_S_delta"]<=3 and all(v>=-2 for v in author.values()) and d["mismatch_delta"]<=0
        decisions.append(d)
    passed=[d for d in decisions if d["pass"]]
    winner=None
    if passed:
        passed=sorted(passed,key=lambda d:(-d["net_correct"],d["false_S_delta"],d["mismatch_delta"],0 if d["condition"]=="softnote" else 1))
        winner=passed[0]["condition"]
    decision=dict(created_utc=c.now(),screen_n=len(blind),baseline=dict(correct=base_correct,false_S=base_false,U2_reason_mismatch=base_mismatch),
                  candidates=decisions,winner=winner,proceed_confirmation=winner is not None,
                  GT_connected_after_prediction_freeze=True,screen_attempt_cost_cny=sum(a["charge_cny"] for a in attempts))
    c.put(OUT/"decision.json",decision)
    c.put(OUT/"GT_connection.json",dict(source=str(GTFILE.relative_to(c.ROOT)).replace("\\","/"),sha256=c.sha(GTFILE),
      connected_utc=c.now(),blind_screen_sha256=c.sha(PLAN/"screen_cohort_blind.jsonl"),screen_jobs_sha256=c.sha(PLAN/"screen_jobs.jsonl")))
    print(__import__("json").dumps(decision,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
