"""Build K/G final raw-EHR references and fixed DeepSeek jobs after audit."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c
import run048

def main():
    if (c.OUT/"screen_stage3_jobs.jsonl").exists():raise RuntimeError("screen stage3 already built")
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    audits=c.lines(c.OUT/"screen_stage2_jobs.jsonl")
    attempts,terminal=run048.state()
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    amap={(x["id"],x["condition"]):x for x in audits}
    mappings=[];unique={}
    final_ref={}
    for pid,x in cases.items():
        for cond in ("K","G"):
            job=amap[(pid,cond)]
            c.require(job["request_id"] in terminal,"missing audit")
            parsed=terminal[job["request_id"]]["parsed"]
            cited=c.cited_external_passages(parsed,job,max_items=12)
            ref,kept=c.append_passages(x["base_reference"],cited,corpus)
            changed=ref!=x["base_reference"]
            rid=None
            if changed:
                body=c.score_body(x["claim"],ref)
                bh=c.digest(body);rid="048_final_"+bh[:32]
                unique.setdefault(rid,dict(request_id=rid,stage="screen_stage3",kind="judge",
                    model_key="deepseek",condition="shared_final",id=pid,body=body))
            final_ref[(pid,cond)]=ref
            mappings.append(dict(id=pid,condition=cond,audit_request_id=job["request_id"],
                audit_status=parsed.get("status"),audit_label=parsed.get("audit_label"),
                audit_coverage=parsed.get("coverage"),citations_valid=parsed.get("citations_valid"),
                cited_external_pids=cited,kept_external_pids=kept,reference_changed=changed,
                final_request_id=rid))

    repeat_ids=set(c.read(c.OUT/"freeze.json")["repeat_ids"])
    repeats=[]
    for pid in sorted(repeat_ids):
        ref=final_ref[(pid,"G")]
        rid="048_Grep_"+c.stable("",pid)[:24]
        unique[rid]=dict(request_id=rid,stage="screen_stage3",kind="judge",
            model_key="deepseek",condition="G_repeat",id=pid,body=c.score_body(cases[pid]["claim"],ref))
        repeats.append(dict(id=pid,request_id=rid,G_reference_changed=ref!=cases[pid]["base_reference"]))
    jobs=sorted(unique.values(),key=lambda z:z["request_id"])
    c.jsonl(c.OUT/"screen_final_mapping.jsonl",mappings)
    c.jsonl(c.OUT/"screen_G_repeats.jsonl",repeats)
    c.jsonl(c.OUT/"screen_stage3_jobs.jsonl",jobs)
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.SCREEN_CAP+1e-9,"screen stage3 conservative bound exceeds cap")
    c.put(c.OUT/"screen_stage3_freeze.json",dict(created_utc=c.now(),logical_conditions=len(mappings),
      K_changed=sum(x["condition"]=="K" and x["reference_changed"] for x in mappings),
      G_changed=sum(x["condition"]=="G" and x["reference_changed"] for x in mappings),
      unique_final_jobs=len(jobs)-len(repeats),G_repeat_jobs=len(repeats),
      current_used_cny=used,stage3_bound_cny=bound,total_bound_cny=used+bound))
    print("048 FINALS BUILT",len(jobs),"K_changed",sum(x["condition"]=="K" and x["reference_changed"] for x in mappings),
      "G_changed",sum(x["condition"]=="G" and x["reference_changed"] for x in mappings),
      "bound",round(bound,4),"total",round(used+bound,4),flush=True)

if __name__=="__main__":main()
