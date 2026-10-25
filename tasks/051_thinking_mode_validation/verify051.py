"""Offline integrity verification for completed 051."""
from pathlib import Path
from collections import Counter
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)

    freeze=c.read(c.OUT/"freeze.json")
    screen=c.lines(c.OUT/"screen_cases.jsonl");confirm=c.lines(c.OUT/"confirmation_cases_frozen.jsonl")
    ck("sample_sizes",len(screen)==48 and len(confirm)==96)
    ck("screen_balance",Counter(x["GT"] for x in screen)==Counter({"Supported":16,"Not Supported":16,"Not Addressed":16}))
    ck("confirm_balance",Counter(x["GT"] for x in confirm)==Counter({"Supported":32,"Not Supported":32,"Not Addressed":32}))
    sp=set(freeze["screen_patients"]);cp=set(freeze["confirmation_patients"])
    ck("patient_disjoint",not(sp&cp))
    ck("screen_coverage",{x["sid"] for x in screen}==sp)
    ck("confirm_coverage",{x["sid"] for x in confirm}==cp)
    ck("case_disjoint",not({x["id"] for x in screen}&{x["id"] for x in confirm}))
    ck("current_protocol_matches_screen_freeze",c.sha(ROOT/"tasks/051_thinking_mode_validation/protocol.md")==c.read(c.OUT/"screen_freeze.json")["current_protocol_sha256"])

    jobs=c.lines(c.OUT/"preflight_jobs.jsonl")+c.lines(c.OUT/"screen_jobs.jsonl")+c.lines(c.OUT/"confirmation_jobs.jsonl")
    ck("job_total",len(jobs)==652,len(jobs))
    byid={j["request_id"]:j for j in jobs};ck("job_ids_unique",len(byid)==652)
    attempts,term=run051.state()
    ck("attempt_total",len(attempts)==652,len(attempts))
    ck("terminal_total",len(term)==652,len(term))
    ck("all_http200",all(a["http_status"]==200 for a in attempts))
    ck("no_duplicate_attempts",len({a["request_id"] for a in attempts})==652)

    stage_counts=Counter(j["stage"] for j in jobs)
    ck("stage_counts",stage_counts==Counter({"preflight":4,"screen":264,"confirmation":384}),dict(stage_counts))

    # Validate frozen request bodies and GT whitelist.
    for j in jobs:
        b=j["body"]
        ck("model_"+j["request_id"],b.get("model")==c.MODEL)
        payload=json.loads(b["messages"][-1]["content"])
        ck("payload_whitelist_"+j["request_id"],set(payload)=={"proposition","reference"},sorted(payload))
        ck("no_gt_payload_"+j["request_id"],"GT" not in payload and "gold" not in payload)
        if j["thinking"]:
            ck("thinking_true_"+j["request_id"],b.get("enable_thinking") is True)
            ck("reasoning_high_"+j["request_id"],b.get("reasoning_effort")=="high")
            ck("thinking_tokens_"+j["request_id"],b.get("max_tokens")==8192)
        else:
            ck("thinking_false_"+j["request_id"],b.get("enable_thinking") is False)
            ck("no_reasoning_effort_"+j["request_id"],"reasoning_effort" not in b)
            ck("nonthinking_tokens_"+j["request_id"],b.get("max_tokens")==2048)

    # Bind every durable request to its frozen job and receipt.
    for a in attempts:
        rq=c.read(ROOT/a["path"]);jid=rq["job"]["request_id"]
        ck("attempt_job_known_"+jid,jid in byid)
        ck("attempt_job_exact_"+jid,c.canonical(rq["job"])==c.canonical(byid[jid]))
        ck("attempt_body_hash_"+jid,rq["body_sha256"]==c.digest(byid[jid]["body"]))
        rp=(ROOT/a["path"]).parent/"receipt.json"
        ck("receipt_exists_"+jid,rp.exists())
        rec=c.read(rp);ck("receipt_binding_"+jid,rec["request_sha256"]==c.sha(ROOT/a["path"]))

    think_jobs=[j for j in jobs if j["thinking"]];nonthink=[j for j in jobs if not j["thinking"]]
    ck("all_thinking_have_reasoning",all(term[j["request_id"]]["parsed"].get("reasoning_present") is True for j in think_jobs))
    ck("nonthinking_no_reasoning",all(not term[j["request_id"]]["parsed"].get("reasoning_present") for j in nonthink))
    ck("returned_models",all(json.loads(term[j["request_id"]]["transport"]["body_text"]).get("model")==c.MODEL for j in jobs))

    decision=c.read(c.OUT/"screen_decision.json")
    ck("screen_promoted_TV",decision.get("promoted")==["T-V"])
    conf_freeze=c.read(c.OUT/"confirmation_freeze.json")
    ck("confirmation_bound_to_screen",conf_freeze["screen_analysis_sha256"]==c.sha(c.OUT/"screen_analysis.json"))
    ck("confirmation_bound_to_cases",conf_freeze["confirmation_cases_sha256"]==c.sha(c.OUT/"confirmation_cases_frozen.jsonl"))
    ck("confirmation_jobs_hash",conf_freeze["jobs_sha256"]==c.sha(c.OUT/"confirmation_jobs.jsonl"))
    ck("confirmation_after_screen",conf_freeze["created_utc"]>c.read(c.OUT/"screen_analysis.json")["created_utc"])

    conf_status=Counter(term[j["request_id"]]["parsed"]["status"] for j in c.lines(c.OUT/"confirmation_jobs.jsonl"))
    ck("only_one_core_invalid_confirmation",conf_status["invalid_core_fields"]==1,dict(conf_status))
    bad=[j for j in c.lines(c.OUT/"confirmation_jobs.jsonl") if term[j["request_id"]]["parsed"]["status"]=="invalid_core_fields"]
    ck("invalid_is_TS_only",len(bad)==1 and bad[0]["condition"]=="T-S")

    cost=sum(a["cost"] for a in attempts)
    ck("total_budget",cost<=c.TOTAL_CAP,cost)
    ck("confirmation_analysis_exists",(c.OUT/"confirmation_analysis.json").exists())
    analysis=c.read(c.OUT/"confirmation_analysis.json")
    ck("analysis_attempts",analysis["api_attempts"]==652 and analysis["http200"]==652)

    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=cost,
      note="Frozen jobs/receipts are the scientific source of truth; current code is post-run support/analysis code.",
      code_sha256={p.name:c.sha(p) for p in [
        ROOT/"tasks/051_thinking_mode_validation/protocol.md",
        ROOT/"tasks/051_thinking_mode_validation/common051.py",
        ROOT/"tasks/051_thinking_mode_validation/run051.py",
        ROOT/"tasks/051_thinking_mode_validation/analyze_screen051.py",
        ROOT/"tasks/051_thinking_mode_validation/analyze_confirmation051.py"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=cost,confirmation_status=dict(conf_status)),indent=2))

if __name__=="__main__":main()
