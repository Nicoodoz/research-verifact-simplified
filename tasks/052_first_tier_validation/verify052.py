"""Offline integrity verification for completed 052. Run after analysis."""
from pathlib import Path
from collections import Counter
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c
import run052

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)
    sf=c.read(c.OUT/"sample_freeze.json");cases=c.lines(c.OUT/"evaluation_cases.jsonl");blind=c.lines(c.OUT/"sample_blind.jsonl")
    ck("sample_n",len(cases)==240 and len(blind)==240)
    ep=set(sf["evaluation_patients"]);ck("patients24",len(ep)==24 and {x["sid"] for x in cases}==ep)
    ck("ten_per_patient",Counter(x["sid"] for x in cases)==Counter({p:10 for p in ep}))
    p051=set(c.read(ROOT/"outputs/051_thinking_mode_validation/freeze.json")["patient_pool"])
    reserved=set(map(str,c.read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]["reserved_test"]))
    ck("disjoint_051",not(ep&p051));ck("disjoint_reserved",not(ep&reserved))
    ck("blind_ids_match",[x["id"] for x in blind]==[x["id"] for x in cases])
    ck("GT_not_in_blind",all("GT" not in x for x in blind))
    ck("sample_hash",sf["sources"]["protocol"]==c.sha(ROOT/"tasks/052_first_tier_validation/protocol.md"))

    cal=c.read(c.OUT/"calibration_models.json")
    trainp=set(cal["training"]["N-S"]["patients"])|set(cal["training"]["T-S"]["patients"])
    ck("calibration_16_patients",len(trainp)==16)
    ck("calibration_disjoint_eval",not(trainp&ep))
    ck("calibration_grad_checks",all(cal["checks"][cond][kind]["finite_difference_max_abs"]<1e-6 for cond in ("N-S","T-S") for kind in ("G","M")))
    gate=c.read(c.OUT/"gate_patient_out_mapping.json")["models"]
    ck("gate_mapping24",set(gate)==ep)
    for sid,z in gate.items():
        model=c.read(ROOT/z["source"])
        ck("gate_excludes_"+sid,sid not in set(model["final_fit"]["training_patients"]))
        ck("gate_hash_"+sid,c.sha(ROOT/z["source"])==z["sha256"])

    main=c.lines(c.OUT/"main_jobs.jsonl");qjobs=c.lines(c.OUT/"qwen_jobs.jsonl")
    ck("main_jobs1008",len(main)==1008)
    ck("main_unique",len({j["request_id"] for j in main})==1008)
    ck("main_counts",Counter(j["condition"] for j in main)==Counter({"N-S":240,"N-V":240,"T-S":240,"T-V":240,
      "N-S_repeat":12,"N-V_repeat":12,"T-S_repeat":12,"T-V_repeat":12}))
    # Every main request contains only proposition/reference patient data and exact configured mode.
    for j in main:
        payload=json.loads(j["body"]["messages"][-1]["content"])
        ck("payload_keys_"+j["request_id"],set(payload)=={"proposition","reference"})
        ck("model_"+j["request_id"],j["body"]["model"]==c.MODEL_DS)
        if j["thinking"]:
            ck("thinking_"+j["request_id"],j["body"].get("enable_thinking") is True and j["body"].get("reasoning_effort")=="high" and j["body"].get("max_tokens")==8192)
        else:
            ck("nonthinking_"+j["request_id"],j["body"].get("enable_thinking") is False and "reasoning_effort" not in j["body"] and j["body"].get("max_tokens")==2048)

    attempts,term=run052.state()
    alljobs={j["request_id"]:j for j in main+qjobs}
    ck("attempts_match_jobs",len(attempts)==len(alljobs),(len(attempts),len(alljobs)))
    ck("all_http200",all(a["http_status"]==200 for a in attempts))
    ck("unique_http200",len({a["request_id"] for a in attempts})==len(attempts))
    ck("terminal_all",set(term)==set(alljobs))
    for a in attempts:
        rq=c.read(ROOT/a["path"]);jid=rq["job"]["request_id"];rp=(ROOT/a["path"]).parent/"receipt.json"
        ck("known_"+jid,jid in alljobs)
        ck("jobexact_"+jid,c.canonical(rq["job"])==c.canonical(alljobs[jid]))
        ck("bodyhash_"+jid,rq["body_sha256"]==c.digest(alljobs[jid]["body"]))
        ck("receipt_"+jid,rp.exists() and c.read(rp)["request_sha256"]==c.sha(ROOT/a["path"]))
    # Qwen set must equal fresh N-S candidate set and preserve claim/reference.
    cand=c.lines(c.OUT/"qwen_candidates.jsonl");ck("q_count",len(cand)==len(qjobs))
    candids={x["id"] for x in cand};ck("q_ids",candids=={j["id"] for j in qjobs})
    blindby={x["id"]:x for x in blind}
    for j in qjobs:
        ck("q_model_"+j["request_id"],j["body"]["model"]==c.MODEL_Q and not j["thinking"] and j["scored"])
        payload=json.loads(j["body"]["messages"][-1]["content"]);x=blindby[j["id"]]
        ck("q_payload_"+j["request_id"],payload=={"proposition":x["claim"],"reference":x["reference"]})
    # Recompute candidate set from main fresh N-S.
    rec=set()
    for x in blind:
        h=c.stable("",x["id"])[:24];p=term["052_N_S_"+h]["parsed"]
        if p.get("status") in c.VALID and p.get("scores"):
            if c.c020.decision(p["scores"],0)!="Supported" and c.c020.decision(p["scores"],2)=="Supported":rec.add(x["id"])
    ck("candidate_recompute",rec==candids,(len(rec),len(candids)))
    ck("task_cap",sum(a["cost"] for a in attempts)<=c.CAP,sum(a["cost"] for a in attempts))
    ck("analysis_exists",(c.OUT/"analysis.json").exists())
    if (c.OUT/"analysis.json").exists():
        an=c.read(c.OUT/"analysis.json");ck("analysis_attempts",an["attempts"]==len(attempts) and an["http200"]==len(attempts))
    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=sum(a["cost"] for a in attempts),
      attempts=len(attempts),main_jobs=len(main),qwen_jobs=len(qjobs),
      code_sha256={p.name:c.sha(p) for p in [
        ROOT/"tasks/052_first_tier_validation/protocol.md",ROOT/"tasks/052_first_tier_validation/common052.py",
        ROOT/"tasks/052_first_tier_validation/run052.py",ROOT/"tasks/052_first_tier_validation/analyze052.py"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=result["cost_cny"],attempts=len(attempts)),indent=2))
if __name__=="__main__":main()
