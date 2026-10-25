from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051
def main():
    c.require((c.OUT/"screen_jobs.jsonl").exists(),"missing frozen jobs")
    c.require(not (c.OUT/"screen_freeze.json").exists(),"screen freeze exists")
    attempts,_=run051.state()
    jobs=c.lines(c.OUT/"screen_jobs.jsonl");sem=c.lines(c.OUT/"semantic_cases.jsonl")
    clinical=c.lines(c.OUT/"screen_cases.jsonl")
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(len(attempts)==4 and all(a["stage"]=="preflight" for a in attempts),"scientific call occurred before freeze")
    c.require(used+bound<=c.SCREEN_CAP+1e-9,"amended cap insufficient")
    c.put(c.OUT/"screen_freeze.json",dict(created_utc=c.now(),clinical_n=len(clinical),
      semantic_n=len(sem),jobs=len(jobs),preflight_attempts=len(attempts),preflight_used_cny=used,
      screen_bound_cny=bound,total_bound_cny=used+bound,screen_cap_cny=c.SCREEN_CAP,total_cap_cny=c.TOTAL_CAP,
      current_protocol_sha256=c.sha(ROOT/"tasks/051_thinking_mode_validation/protocol.md"),
      budget_amendment_sha256=c.sha(c.OUT/"budget_amendment_001.json"),
      jobs_sha256=c.sha(c.OUT/"screen_jobs.jsonl"),semantic_sha256=c.sha(c.OUT/"semantic_cases.jsonl")))
    print("051 SCREEN FREEZE FINAL",len(jobs),round(used,6),round(bound,6),round(used+bound,6))
if __name__=="__main__":main()
