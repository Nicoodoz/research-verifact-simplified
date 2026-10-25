"""Offline integrity verification for completed/stopped 047."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/047_mechanism_stratified_validation"))
import common047 as c
import run047

def clean_block(b):
    return re.sub(r"^\d+\.","#",b,count=1)

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)
    freeze=c.read(c.OUT/"freeze.json")
    screen=c.lines(c.OUT/"screen_cases.jsonl")
    confirm=c.lines(c.OUT/"confirmation_cases_frozen.jsonl")
    sp=set(freeze["screen_patients"]);cp=set(freeze["confirmation_patients"])
    ck("patient_split_disjoint",not(sp&cp),dict(screen=len(sp),confirm=len(cp)))
    ck("screen_patient_membership",all(x["sid"] in sp for x in screen))
    ck("confirmation_patient_membership",all(x["sid"] in cp for x in confirm))
    ck("sample_sizes",len(screen)==24 and len(confirm)==64)
    groups=c.read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]
    dev=set(groups["development"]);reserved=set(groups["reserved_test"])
    ck("development_only",(sp|cp)<=dev and not((sp|cp)&reserved))

    jobs={x["request_id"]:x for x in c.lines(c.OUT/"screen_stage1_jobs.jsonl")}
    for x in screen:
        pid=x["id"];h=c.stable("",pid)[:24]
        b=jobs["047_B_"+h]["body"];j=jobs["047_J_"+h]["body"]
        bb=dict(b);jj=dict(j);bb["model"]=jj["model"]="SAME"
        ck("J_same_body_except_model_"+h,bb==jj)
        _,base_blocks=c.ref_blocks(x["base_reference"])
        _,focus_blocks=c.ref_blocks(x["focus_reference"])
        ck("P_same_evidence_"+h,
           sorted(clean_block(z) for z in base_blocks)==sorted(clean_block(z) for z in focus_blocks),
           dict(base=len(base_blocks),focus=len(focus_blocks)))
    smap=c.lines(c.OUT/"screen_S_mapping.jsonl")
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    for m in smap:
        for w in m["windows"]:
            p=corpus[w["passage_id"]]
            a=w["start"]-p["start"];b=w["end_exclusive"]-p["start"]
            ck("S_raw_substring_"+m["id"][:8]+"_"+w["passage_id"][:8],
               0<=a<b<=len(p["text"]) and p["text"][a:b].strip()==w["text"])

    attempts,terminal=run047.state()
    ck("all_http200",len(attempts)==119 and all(x["http_status"]==200 for x in attempts),len(attempts))
    cost=sum(x["cost"] for x in attempts)
    ck("screen_budget",cost<=c.SCREEN_CAP,cost)
    for rec in terminal.values():
        body=rec["job"]["body"];payload=json.loads(body["messages"][-1]["content"])
        ck("no_label_metadata_"+rec["job"]["request_id"],"GT" not in payload and "gold" not in payload)
    decision=c.read(c.OUT/"screen_decision.json")
    ck("stopped_by_frozen_rule",decision["stop"] is True and decision["promoted"]==[])
    ck("no_confirmation_execution",
       not any(x["stage"].startswith("confirm") for x in attempts))
    analysis=c.read(c.OUT/"screen_analysis.json")
    ck("repeat_count",len(analysis["repeats"])==6)
    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=cost,
        code_sha256={p.name:c.sha(p) for p in [
          ROOT/"tasks/047_mechanism_stratified_validation/common047.py",
          ROOT/"tasks/047_mechanism_stratified_validation/prepare047.py",
          ROOT/"tasks/047_mechanism_stratified_validation/run047.py",
          ROOT/"tasks/047_mechanism_stratified_validation/build_screen_stage2.py",
          ROOT/"tasks/047_mechanism_stratified_validation/analyze_screen047.py",
          ROOT/"tasks/047_mechanism_stratified_validation/protocol.md"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=cost),indent=2),flush=True)

if __name__=="__main__":
    main()
