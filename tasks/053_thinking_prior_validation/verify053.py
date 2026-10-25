from pathlib import Path
from collections import Counter
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c,run053

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name+" "+str(detail))
    blind=c.lines(c.OUT/"sample_blind.jsonl");fr=c.read(c.OUT/"freeze.json")
    ck("sample240",len(blind)==240);ck("patients40",len({x["sid"] for x in blind})==40)
    ck("six_each",Counter(x["sid"] for x in blind)==Counter({p:6 for p in fr["patients"]}))
    used=set()
    for f in [ROOT/"outputs/051_thinking_mode_validation/screen_cases.jsonl",ROOT/"outputs/051_thinking_mode_validation/confirmation_cases_frozen.jsonl",ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl"]:
        for x in c.lines(f):used.add(x.get("id") or x.get("proposition_id"))
    ck("claim_disjoint_051_052",not({x["id"] for x in blind}&used))
    ck("prior",fr["reference_prior_counts"]=={"Supported":1108,"Not Supported":100,"Not Addressed":170})
    main=c.lines(c.OUT/"main_jobs.jsonl");q=c.lines(c.OUT/"qwen_jobs.jsonl")
    ck("main480",len(main)==480);ck("main_counts",Counter(j["condition"] for j in main)==Counter({"N-S":240,"T-S":240}))
    for j in main:
        payload=json.loads(j["body"]["messages"][-1]["content"]);ck("payload_"+j["request_id"],set(payload)=={"proposition","reference"})
        if j["condition"]=="T-S":ck("think_"+j["request_id"],j["body"].get("enable_thinking") is True and j["body"].get("reasoning_effort")=="high" and j["body"].get("max_tokens")==8192)
        else:ck("nonthink_"+j["request_id"],j["body"].get("enable_thinking") is False and "reasoning_effort" not in j["body"] and j["body"].get("max_tokens")==2048)
    attempts,term=run053.state();allj={j["request_id"]:j for j in main+q}
    ck("attempts",len(attempts)==len(allj),(len(attempts),len(allj)));ck("http200",all(a["http_status"]==200 for a in attempts));ck("terminal",set(term)==set(allj))
    ck("unique",len({a["request_id"] for a in attempts})==len(attempts))
    cases={x["id"]:x for x in blind};rec=set()
    for pid in cases:
        h=c.stable("",pid)[:24];p=term["053_N_S_"+h]["parsed"]
        if p.get("status") in c.VALID and p.get("scores") and c.decision(p["scores"],0)!="Supported" and c.decision(p["scores"],2)=="Supported":rec.add(pid)
    ck("q_candidates",rec=={j["id"] for j in q},(len(rec),len(q)))
    ck("cap",sum(a["cost"] for a in attempts)<=c.CAP,sum(a["cost"] for a in attempts))
    ck("analysis",(c.OUT/"analysis.json").exists())
    result=dict(status="PASS",checks=checks,cost_cny=sum(a["cost"] for a in attempts),attempts=len(attempts),created_utc=c.now())
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=result["cost_cny"],attempts=len(attempts)),indent=2))
if __name__=="__main__":main()
