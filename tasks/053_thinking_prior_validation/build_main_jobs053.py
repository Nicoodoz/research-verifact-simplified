from pathlib import Path
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c

def main():
    cases=c.lines(c.OUT/"sample_blind.jsonl");jobs=[]
    for x in cases:
        h=c.stable("",x["id"])[:24]
        jobs.append(dict(request_id="053_N_S_"+h,stage="main",condition="N-S",id=x["id"],sid=x["sid"],
          scored=True,thinking=False,body=c.judge_body(x["claim"],x["reference"],True,False,c.MODEL_DS)))
        jobs.append(dict(request_id="053_T_S_"+h,stage="main",condition="T-S",id=x["id"],sid=x["sid"],
          scored=True,thinking=True,body=c.judge_body(x["claim"],x["reference"],True,True,c.MODEL_DS)))
    jobs.sort(key=lambda j:c.stable("053/main/order/v1:",j["request_id"]))
    c.jsonl(c.OUT/"main_jobs.jsonl",jobs)
    exp=240*(2.996931/240)+240*(6.267072/240)
    c.put(c.OUT/"main_freeze.json",dict(created_utc=c.now(),cases=len(cases),jobs=len(jobs),
      condition_counts=dict(Counter(j["condition"] for j in jobs)),expected_cny_from_052=exp,
      target_total_cny=12.0,hard_cap_cny=c.CAP,sample_sha256=c.sha(c.OUT/"sample_blind.jsonl"),
      jobs_sha256=c.sha(c.OUT/"main_jobs.jsonl"),protocol_sha256=c.sha(ROOT/"tasks/053_thinking_prior_validation/protocol.md"),
      GT_used=False))
    print("053 JOBS",len(jobs),"expected",round(exp,3),"cap",c.CAP)
if __name__=="__main__":main()
