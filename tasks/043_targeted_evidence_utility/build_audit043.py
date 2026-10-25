"""Freeze reason-audit jobs after DeepSeek outputs; no GT in audit inputs."""
import common043 as c
import api043

PLAN=c.OUT/"planning_001";OUT=c.OUT/"audit_001"

def main():
    c.require(not OUT.exists(),"audit exists")
    attempts,terminal=api043.state()
    score_jobs=c.lines(PLAN/"score_jobs.jsonl")
    c.require(all(j["request_id"] in terminal for j in score_jobs),"score terminal incomplete")
    cases={x["id"]:x for x in c.lines(PLAN/"cases.jsonl")}
    jobs=[];logical=[];invalid=[]
    for j in score_jobs:
        if j["round"]!=0:continue
        t=terminal[j["request_id"]];p=t["parsed"]
        if p["status"] not in c.VALID:
            invalid.append(dict(id=j["proposition_id"],condition=j["condition"],status=p["status"],errors=p.get("errors")))
            continue
        x=cases[j["proposition_id"]];cond=j["condition"];ref=x[cond+"_reference"]
        added=[] if cond=="A" else x[cond+"_added_ids"]
        body=c.audit_body(x["claim"],ref,p["verdict"],p["parsed"].get("reason"),p["parsed"].get("checks"),added)
        rid=f"043_audit_{cond}_{x['id']}"
        jobs.append(dict(request_id=rid,kind="audit",model_key="qwen",proposition_id=x["id"],condition=cond,body=body))
        logical.append(dict(id=x["id"],condition=cond,request_id=rid,score_request_id=j["request_id"],added_ids=added))
    bound=sum(c.bound(j) for j in jobs)
    used=sum(a["charge_cny"] for a in attempts)
    c.require(used+bound<c.CAP,"audit total bound exceeds cap")
    OUT.mkdir(parents=True);c.jsonl(OUT/"jobs.jsonl",jobs);c.jsonl(OUT/"logical.jsonl",logical)
    c.put(OUT/"freeze.json",dict(created_utc=c.now(),jobs=len(jobs),invalid_score_round0=invalid,
      score_cost_so_far_cny=used,audit_bound_cny=bound,total_bound_cny=used+bound,
      GT_in_audit_input=False,condition_name_in_audit_input=False))
    print("043 audit frozen",len(jobs),"jobs","invalid",len(invalid),"total bound",round(used+bound,3),flush=True)

if __name__=="__main__":main()
