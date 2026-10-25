"""Offline executor verification for 045. Not an independent audit."""
from pathlib import Path
import json,hashlib
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/045_semantic_recovery_screen"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/045_semantic_recovery_screen"))
import run045
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p)
    with p.open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")

def main():
    checks={};freeze=read(OUT/"freeze.json")
    for rel,h in freeze["sources"].items():assert sha(ROOT/rel)==h
    assert sha(ROOT/"tasks/045_semantic_recovery_screen/protocol.md")==freeze["protocol_sha"]
    checks["frozen_sources_and_protocol"]=True
    cohort=lines(OUT/"cohort.jsonl");assert len(cohort)==16 and len({x["id"] for x in cohort})==16
    q=Counter((x["base_correct"],x["GT"],x["author"]) for x in cohort)
    assert sum(not x["base_correct"] for x in cohort)==8 and sum(x["base_correct"] for x in cohort)==8
    assert max(Counter(x["sid"] for x in cohort).values())<=3
    checks["cohort"]=dict(n=16,patients=len({x["sid"] for x in cohort}),strata={str(k):v for k,v in q.items()})
    groups=read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]
    assert {x["sid"] for x in cohort}<=set(map(str,groups["development"]))
    assert not ({x["sid"] for x in cohort}&set(map(str,groups["reserved_test"])))
    checks["reserved_overlap"]=0
    attempts,term=run045.state()
    assert len(attempts)==76 and len(term)==76 and all(a["http_status"]==200 for a in attempts)
    assert all(v["parsed"]["status"] in ("valid","valid_with_format_anomaly") for v in term.values())
    cost=sum(a["cost"] for a in attempts);assert cost<8
    checks["api"]=dict(attempts=76,http200=76,cost_cny=cost,cap_cny=8,
      by_stage=dict(Counter(a["stage"] for a in attempts)),by_model=dict(Counter(v["job"]["model_key"] for v in term.values())))
    for j in lines(OUT/"stage1_jobs.jsonl")+lines(OUT/"stage2_jobs.jsonl"):
        user=json.loads(j["body"]["messages"][1]["content"])
        assert "GT" not in user and "gold_label" not in user
    checks["GT_not_in_API_user_payload"]=True

    s2=read(OUT/"stage2_freeze.json")
    assert s2["B_choices"]=={"none":15,"complement":1} and s2["C_changed"]==7 and s2["jobs"]==8
    checks["stage2"]=s2
    ana=read(OUT/"analysis_summary.json");routes={x["route"]:x for x in ana["routes"]}
    assert routes["A"]["net"]==0 and routes["B"]["net"]==0 and routes["C"]["net"]==0
    assert routes["D"]["rescued"]==2 and routes["D"]["harmed"]==0 and routes["D"]["net"]==2
    assert sum(x["changed"] for x in ana["repeats"])==0
    checks["route_recount"]={k:routes[k] for k in ("A","B","C","D")}
    checks["baseline_repeat"]=ana["repeats"]
    changed=[x for x in ana["changed_cases"] if x["route"]=="D"]
    assert len(changed)==2 and all(x["new_correct"] and not x["base_correct"] for x in changed)
    bad_format=0
    for x in changed:
        rid="045_D_"+hashlib.sha256(x["id"].encode()).hexdigest()[:24]
        obj=term[rid]["parsed"]["parsed"]
        for chk in obj.get("checks",[]):
            if any(not isinstance(e,int) for e in chk.get("evidence_ids",[])):bad_format+=1
    assert bad_format>0
    checks["D_changed_cases"]=dict(n=2,rescued=2,harmed=0)
    checks["D_citation_format_warning"]="Changed D outputs used note-ID strings rather than numbered reference IDs in checks; label comparison remains usable but citation-format compliance failed."

    result=dict(status="pass_with_D_citation_format_warning",
      checked_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      independent_audit=False,checks=checks,
      interpretation="First-batch development route screen only; not a population performance estimate or final validation.")
    put(OUT/"verification_001.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
