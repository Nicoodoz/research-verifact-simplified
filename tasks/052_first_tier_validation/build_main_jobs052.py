"""Freeze all 052 DeepSeek main/repeat jobs from GT-blind sample."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
CONDS=(("N-S",True,False),("N-V",False,False),("T-S",True,True),("T-V",False,True))

def main():
    if (c.OUT/"main_jobs.jsonl").exists():raise RuntimeError("main jobs exist")
    cases=c.lines(c.OUT/"sample_blind.jsonl")
    repeat_ids={x["id"] for x in sorted(cases,key=lambda z:c.stable("052/repeat/v1:",z["id"]))[:12]}
    jobs=[]
    for x in cases:
        h=c.stable("",x["id"])[:24]
        for cond,scored,thinking in CONDS:
            body=c.judge_body(x["claim"],x["reference"],scored,thinking,c.MODEL_DS)
            jobs.append(dict(request_id="052_"+cond.replace("-","_")+"_"+h,stage="main",condition=cond,
              id=x["id"],sid=x["sid"],scored=scored,thinking=thinking,body=body))
            if x["id"] in repeat_ids:
                jobs.append(dict(request_id="052_"+cond.replace("-","_")+"_rep_"+h,stage="main",condition=cond+"_repeat",
                  id=x["id"],sid=x["sid"],scored=scored,thinking=thinking,body=body))
    jobs.sort(key=lambda j:c.stable("052/main/order/v1:",j["request_id"]))
    c.jsonl(c.OUT/"main_jobs.jsonl",jobs)
    bound=sum(c.bound(j) for j in jobs)
    c.require(bound<=c.CAP,"main full reservation exceeds task cap")
    c.put(c.OUT/"main_freeze.json",dict(created_utc=c.now(),cases=len(cases),jobs=len(jobs),repeat_ids=sorted(repeat_ids),
      conservative_bound_cny=bound,task_cap_cny=c.CAP,GT_used_for_jobs=False,
      sample_sha256=c.sha(c.OUT/"sample_blind.jsonl"),protocol_sha256=c.sha(ROOT/"tasks/052_first_tier_validation/protocol.md"),
      calibration_sha256=c.sha(c.OUT/"calibration_models.json"),gate_mapping_sha256=c.sha(c.OUT/"gate_patient_out_mapping.json")))
    print("052 MAIN BUILT",dict(cases=len(cases),jobs=len(jobs),repeat=len(repeat_ids),bound=round(bound,4),cap=c.CAP),flush=True)
if __name__=="__main__":main()
