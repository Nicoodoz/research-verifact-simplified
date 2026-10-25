"""Freeze 049 screen inputs and fresh baseline jobs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/049_evidence_decision_utilization"))
import common049 as c

def main():
    if (c.OUT/"screen_cases.jsonl").exists():raise RuntimeError("049 screen already prepared")
    src=c.lines(ROOT/"outputs/048_end_to_end_evidence_recovery/screen_cases.jsonl")
    cases=[]
    jobs=[]
    for x in src:
        row={k:x[k] for k in ("id","sid","author","GT","claim","base_reference","base_ids")}
        cases.append(row)
        h=c.stable("",x["id"])[:24]
        jobs.append(dict(request_id="049_B_"+h,stage="screen_stage1",kind="judge",
          model_key="deepseek",condition="B",id=x["id"],body=c.score_body(x["claim"],x["base_reference"])))
    c.jsonl(c.OUT/"screen_cases.jsonl",cases)
    c.jsonl(c.OUT/"screen_stage1_jobs.jsonl",jobs)
    c.put(c.OUT/"freeze.json",dict(created_utc=c.now(),screen_n=len(cases),
      screen_patients=sorted({x["sid"] for x in cases}),screen_stage1_jobs=len(jobs),
      screen_cap_cny=c.SCREEN_CAP,total_cap_cny=c.TOTAL_CAP,
      stage0_sha256=c.sha(c.OUT/"stage0_summary.json"),
      protocol_sha256=c.sha(ROOT/"tasks/049_evidence_decision_utilization/protocol.md"),
      source_sha256={"048_screen_cases":c.sha(ROOT/"outputs/048_end_to_end_evidence_recovery/screen_cases.jsonl"),
                     "048_final_mapping":c.sha(ROOT/"outputs/048_end_to_end_evidence_recovery/screen_final_mapping.jsonl")}))
    print("049 SCREEN PREPARED",len(cases),len(jobs),flush=True)

if __name__=="__main__":main()
