"""Offline integrity verification for 048 stopped screen."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c
import run048

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)
    freeze=c.read(c.OUT/"freeze.json")
    screen=c.lines(c.OUT/"screen_cases.jsonl")
    confirm=c.lines(c.OUT/"confirmation_cases_frozen.jsonl")
    sp=set(freeze["screen_patients"]);cp=set(freeze["confirmation_patients"])
    ck("patient_split_disjoint",not(sp&cp))
    ck("sample_sizes",len(screen)==16 and len(confirm)==29)
    ck("screen_four_each",all(sum(x["sid"]==sid for x in screen)==4 for sid in sp))
    ck("screen_membership",all(x["sid"] in sp for x in screen))
    ck("confirm_membership",all(x["sid"] in cp for x in confirm))
    ck("trigger_definition",all(x["historical_raw"]!="Supported" and x["historical_U2"]=="Supported" for x in screen+confirm))

    groups=c.read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]
    dev=set(groups["development"]);reserved=set(groups["reserved_test"])
    ck("development_only",(sp|cp)<=dev and not((sp|cp)&reserved))
    contexts={x["id"]:x for x in c.lines(c.OUT/"screen_search_contexts.jsonl")}
    cases={x["id"]:x for x in screen}
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    for pid,x in cases.items():
        ctx=contexts[pid]
        ck("K_subset_D48_"+pid,set(ctx["K_candidate_pids"])<=set(x["d48_extra_ids"]))
        ck("G_max32_"+pid,len(ctx["G_candidate_pids"])<=32)
        ck("G_excludes_base_"+pid,not(set(ctx["G_candidate_pids"])&set(x["base_ids"])))
        ck("G_same_subject_"+pid,all(str(corpus[p]["subject_id"])==str(x["sid"]) for p in ctx["G_candidate_pids"]))

    all_jobs=c.lines(c.OUT/"screen_stage1_jobs.jsonl")+c.lines(c.OUT/"screen_stage2_jobs.jsonl")+c.lines(c.OUT/"screen_stage3_jobs.jsonl")
    for job in all_jobs:
        payload=json.loads(job["body"]["messages"][-1]["content"])
        if job["kind"]=="query":allowed={"proposition"}
        elif job["kind"]=="audit":allowed={"proposition","C48","additional_EHR"}
        else:allowed={"proposition","reference"}
        ck("payload_keys_"+job["request_id"],set(payload)==allowed,sorted(payload))
    mappings=c.lines(c.OUT/"screen_final_mapping.jsonl")
    final_jobs={x["request_id"]:x for x in c.lines(c.OUT/"screen_stage3_jobs.jsonl")}
    for m in mappings:
        ck("audit_parsed_"+m["id"]+"_"+m["condition"],m["audit_status"]=="valid")
        if not m["reference_changed"]:continue
        job=final_jobs[m["final_request_id"]]
        ref=json.loads(job["body"]["messages"][-1]["content"])["reference"]
        for pid in m["kept_external_pids"]:
            p=corpus[pid]
            ck("raw_passage_"+m["id"]+"_"+m["condition"]+"_"+pid[:8],p["text"] in ref)

    attempts,terminal=run048.state()
    ck("attempt_count",len(attempts)==90,len(attempts))
    ck("all_http200",all(x["http_status"]==200 for x in attempts))
    cost=sum(x["cost"] for x in attempts)
    ck("screen_budget",cost<=c.SCREEN_CAP,cost)
    ck("no_confirmation_calls",not any(x["stage"].startswith("confirmation") for x in attempts))
    decision=c.read(c.OUT/"screen_decision.json")
    ck("stopped_by_rule",decision["stop"] is True and decision["promoted"]==[])
    analysis=c.read(c.OUT/"screen_analysis.json")
    ck("repeat_count",len(analysis["repeats"])==6)
    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=cost,
      code_sha256={p.name:c.sha(p) for p in [
        ROOT/"tasks/048_end_to_end_evidence_recovery/common048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/prepare048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/run048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/build_screen_audits048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/build_screen_finals048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/analyze_screen048.py",
        ROOT/"tasks/048_end_to_end_evidence_recovery/protocol.md"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=cost),indent=2),flush=True)

if __name__=="__main__":main()
