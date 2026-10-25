"""Build S final references after frozen screen selectors."""
from pathlib import Path
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/047_mechanism_stratified_validation"))
import common047 as c
import run047

def main():
    if (c.OUT/"screen_stage2_jobs.jsonl").exists():raise RuntimeError("screen stage2 already built")
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    attempts,terminal=run047.state()
    mapping=[];jobs=[]
    for pid,x in cases.items():
        rid="047_Ssel_"+c.stable("",pid)[:24]
        c.require(rid in terminal,"missing S selector")
        p=terminal[rid]["parsed"];selected_short=[]
        if p.get("status")=="valid":
            obj=p.get("parsed") or {}
            allowed=x["extra_short_to_pid"]
            selected_short=[z for z in obj.get("selected",[]) if z in allowed][:3]
        selected_pids=[x["extra_short_to_pid"][z] for z in selected_short]
        ref,windows,chars=c.append_windows(x["base_reference"],selected_pids,corpus,x["claim"])
        changed=ref!=x["base_reference"]
        final_id=None
        if changed:
            final_id="047_Sfinal_"+c.stable("",pid)[:24]
            jobs.append(dict(request_id=final_id,stage="screen_stage2",route="S",
                kind="judge",model_key="deepseek",id=pid,
                body=c.score_body(x["claim"],ref,"deepseek")))
        mapping.append(dict(id=pid,selector_request_id=rid,selector_status=p.get("status"),
            selected_short=selected_short,selected_pids=selected_pids,
            reference_changed=changed,added_chars=chars,windows=windows,
            final_request_id=final_id))

    c.jsonl(c.OUT/"screen_S_mapping.jsonl",mapping)
    c.jsonl(c.OUT/"screen_stage2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    c.put(c.OUT/"screen_stage2_freeze.json",dict(created_utc=c.now(),
        claims=len(mapping),selectors_valid=sum(x["selector_status"]=="valid" for x in mapping),
        selectors_invalid=sum(x["selector_status"]!="valid" for x in mapping),
        changed_references=sum(x["reference_changed"] for x in mapping),
        final_jobs=len(jobs),selected_none=sum(not x["selected_pids"] for x in mapping),
        prior_cost_cny=sum(a["cost"] for a in attempts)))
    print("047 SCREEN STAGE2",len(jobs),"changed",sum(x["reference_changed"] for x in mapping),
          "selector_invalid",sum(x["selector_status"]!="valid" for x in mapping),flush=True)

if __name__=="__main__":
    main()
