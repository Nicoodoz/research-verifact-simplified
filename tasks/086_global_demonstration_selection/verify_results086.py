"""Independent deterministic post-run checks; no inference or new fitting."""
from __future__ import annotations

import json
import subprocess
from collections import Counter

import prepare086 as p
import run086 as r
import analyze086 as a
import select086 as s

OUT=r.OUT


def main():
    checks=[]
    def ok(value,name):
        if not value:raise AssertionError(name)
        checks.append(name)
    freeze=r.read(OUT/"freeze.json")
    groups=r.read(OUT/"groups.json")
    vjobs=r.check_jobs("V");ejobs=r.check_jobs("E")
    selected=r.read(OUT/"D_star_freeze.json")
    utility=r.read(OUT/"V_utility.json")
    ef=r.read(OUT/"E_jobs_freeze.json")
    ok(selected["name"]==utility["rank"][0]==ef["D_star"],"V_only_selection_frozen")
    ok(selected["V_utility_sha256"]==r.sha(OUT/"V_utility.json"),"V_utility_sha")
    ok(ef["D_star_freeze_sha256"]==r.sha(OUT/"D_star_freeze.json"),"E_choice_sha")
    ok(ef["jobs_sha256"]==r.sha(OUT/"E_jobs.jsonl"),"E_jobs_sha")
    ok(not freeze["E_GT_read"] and not selected["E_GT_read"] and not ef["E_GT_read"],"E_GT_selection_guard")
    v=r.lines(OUT/"V_cases.jsonl");e=r.lines(OUT/"E_cases_blind.jsonl");d=r.lines(OUT/"candidate_pool.jsonl")
    D={x["sid"] for x in d};V={x["sid"] for x in v};E={x["sid"] for x in e}
    ok((len(D),len(V),len(E))==(6,12,22) and not (D&V or D&E or V&E),"patient_separation")
    ok(len(v)==36 and len(e)==110 and all("GT" not in x for x in e),"cohort_freeze")
    ok(len(vjobs)==180 and len(ejobs)==ef["jobs_n"],"job_count")
    attempts,success,_=r.state()
    ok(len(success)==len(vjobs)+len(ejobs),"all_logical_success")
    ok(len({x["request_id"] for x in success.values()})==len(success),"no_duplicate_success")
    for x in attempts:
        req=r.read(r.ROOT/x["request_source"])
        receipt=r.read(r.ROOT/x["receipt_source"])
        ok(receipt["request_sha256"]==r.sha(r.ROOT/x["request_source"]),"receipt_binding")
        ok(abs(r.charge(req,receipt["transport"])-x["cost_or_unknown_cny"])<1e-10,"attempt_charge")
        if x["http_status"]==200:
            ok(json.loads(receipt["transport"]["body_text"])["model"]==r.MODEL,"model_returned")
    cost=r.read(OUT/"cost_ledger.json")
    ok(abs(cost["total_original_or_unknown_cny"]-sum(x["cost_or_unknown_cny"] for x in attempts))<1e-8,"cost_conservation")
    ok(cost["total_original_or_unknown_cny"]<=30+1e-9,"hard_cap")
    pred=r.lines(OUT/"E_predictions.jsonl")
    analysis=r.read(OUT/"E_analysis.json")
    ok(len(pred)==110 and {x["id"] for x in pred}=={x["id"] for x in e},"E_predictions_complete")
    ok(analysis["E_predictions_sha256"]==r.sha(OUT/"E_predictions.jsonl"),"E_predictions_sha")
    for method,table in analysis["summaries"].items():
        for arm,m in table.items():
            independent=sum(x["GT"]==x["labels"][arm][method] for x in pred)
            false_s=sum(x["GT"]!="Supported" and x["labels"][arm][method]=="Supported" for x in pred)
            ok(independent==m["correct"] and false_s==m["false_S"],"independent_correct_falseS")
            ok(abs(independent/110-m["PA"])<1e-12,"independent_PA")
    status=subprocess.check_output(["git","diff","--name-only","--",".gitignore"],cwd=r.ROOT,text=True).strip()
    ok(status=="","gitignore_unchanged")
    result={"status":"PASS","checks":len(checks),"independent_audit":False,
            "new_api_attempts":len(attempts),"original_or_unknown_cny":cost["total_original_or_unknown_cny"]}
    s.put(OUT/"selfcheck.json",result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":main()
