"""After all DeepSeek main outputs, freeze candidate-only Qwen jobs for patient-out Gate A."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
import run052
def main():
    if (c.OUT/"qwen_jobs.jsonl").exists():raise RuntimeError("qwen jobs exist")
    cases={x["id"]:x for x in c.lines(c.OUT/"sample_blind.jsonl")}
    _,term=run052.state();jobs=[];candidates=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];rid="052_N_S_"+h
        c.require(rid in term,"main incomplete "+pid);p=term[rid]["parsed"]
        if p.get("status") not in c.VALID or p.get("scores") is None:continue
        u0=c.c020.decision(p["scores"],0);u2=c.c020.decision(p["scores"],2)
        if u0!="Supported" and u2=="Supported":
            candidates.append(dict(id=pid,sid=x["sid"],u0=u0,u2=u2,scores=p["scores"]))
            jobs.append(dict(request_id="052_Q_"+h,stage="qwen",condition="Gate_peer",id=pid,sid=x["sid"],
              scored=True,thinking=False,body=c.judge_body(x["claim"],x["reference"],True,False,c.MODEL_Q)))
    jobs.sort(key=lambda j:c.stable("052/qwen/order/v1:",j["request_id"]))
    c.jsonl(c.OUT/"qwen_candidates.jsonl",candidates);c.jsonl(c.OUT/"qwen_jobs.jsonl",jobs)
    attempts,_=run052.state();used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.CAP,"Qwen bound exceeds remaining cap")
    c.put(c.OUT/"qwen_freeze.json",dict(created_utc=c.now(),candidate_n=len(candidates),jobs=len(jobs),
      prior_used_cny=used,qwen_bound_cny=bound,total_bound_cny=used+bound,cap_cny=c.CAP,
      candidates_sha256=c.sha(c.OUT/"qwen_candidates.jsonl"),jobs_sha256=c.sha(c.OUT/"qwen_jobs.jsonl"),
      GT_used=False,main_jobs_sha256=c.sha(c.OUT/"main_jobs.jsonl")))
    print("052 QWEN BUILT",dict(candidates=len(candidates),used=round(used,3),bound=round(bound,3),total=round(used+bound,3)),flush=True)
if __name__=="__main__":main()
