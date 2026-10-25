"""Freeze 051 confirmation jobs after T-V passed prespecified screen risk lane."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051
CONDS=(("N-S",True,False),("N-V",False,False),("T-S",True,True),("T-V",False,True))
def main():
    if (c.OUT/"confirmation_jobs.jsonl").exists():raise RuntimeError("confirmation already built")
    decision=c.read(c.OUT/"screen_decision.json")
    c.require(decision.get("promoted")==["T-V"],"T-V was not sole promoted screen method")
    cases=c.lines(c.OUT/"confirmation_cases_frozen.jsonl")
    c.require(len(cases)==96,"confirmation cohort drift")
    jobs=[]
    for x in cases:
        h=c.stable("",x["id"])[:24]
        for cond,scored,thinking in CONDS:
            jobs.append(dict(request_id="051_conf_"+cond.replace("-","_")+"_"+h,stage="confirmation",
              kind="judge",condition=cond,id=x["id"],scored=scored,thinking=thinking,
              body=c.judge_body(x["claim"],x["reference"],scored,thinking)))
    jobs.sort(key=lambda z:c.stable("051/confirm/order/v1:",z["request_id"]))
    c.jsonl(c.OUT/"confirmation_jobs.jsonl",jobs)
    attempts,_=run051.state();used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.TOTAL_CAP+1e-9,f"confirmation bound {used+bound:.3f}>{c.TOTAL_CAP}")
    c.put(c.OUT/"confirmation_freeze.json",dict(created_utc=c.now(),cases=len(cases),jobs=len(jobs),
      promoted_from_screen=decision["promoted"],prior_cost_cny=used,confirmation_bound_cny=bound,
      total_bound_cny=used+bound,total_cap_cny=c.TOTAL_CAP,
      jobs_sha256=c.sha(c.OUT/"confirmation_jobs.jsonl"),
      screen_analysis_sha256=c.sha(c.OUT/"screen_analysis.json"),
      confirmation_cases_sha256=c.sha(c.OUT/"confirmation_cases_frozen.jsonl")))
    print("051 CONFIRMATION BUILT",len(jobs),"prior",round(used,4),"bound",round(bound,4),"total",round(used+bound,4),flush=True)
if __name__=="__main__":main()
