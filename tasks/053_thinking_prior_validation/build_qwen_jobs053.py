from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c
import run053

def main():
    c.require(not (c.OUT/"qwen_jobs.jsonl").exists(),"qwen jobs exist")
    cases={x["id"]:x for x in c.lines(c.OUT/"sample_blind.jsonl")}
    _,term=run053.state();jobs=[];cand=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];p=term["053_N_S_"+h]["parsed"]
        if p.get("status") not in c.VALID or p.get("scores") is None:continue
        u0=c.decision(p["scores"],0);u2=c.decision(p["scores"],2)
        if u0!="Supported" and u2=="Supported":
            cand.append(dict(id=pid,sid=x["sid"],u0=u0,u2=u2,scores=p["scores"]))
            jobs.append(dict(request_id="053_Q_"+h,stage="qwen",condition="Gate_peer",id=pid,sid=x["sid"],
              scored=True,thinking=False,body=c.judge_body(x["claim"],x["reference"],True,False,c.MODEL_Q)))
    jobs.sort(key=lambda j:c.stable("053/qwen/order/v1:",j["request_id"]))
    c.jsonl(c.OUT/"qwen_candidates.jsonl",cand);c.jsonl(c.OUT/"qwen_jobs.jsonl",jobs)
    attempts,_=run053.state();used=sum(a["cost"] for a in attempts);reserve=sum(c.reservation(j) for j in jobs)
    c.require(used+reserve<=c.CAP,"qwen reservation over cap")
    c.put(c.OUT/"qwen_freeze.json",dict(created_utc=c.now(),candidate_n=len(cand),prior_used_cny=used,
      qwen_reservation_cny=reserve,total_reserved_cny=used+reserve,cap_cny=c.CAP,
      candidate_sha256=c.sha(c.OUT/"qwen_candidates.jsonl"),jobs_sha256=c.sha(c.OUT/"qwen_jobs.jsonl"),GT_used=False))
    print("053 QWEN",len(jobs),"used",round(used,3),"reserve",round(reserve,3))
if __name__=="__main__":main()
