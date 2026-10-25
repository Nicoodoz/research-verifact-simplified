"""Select one global four-example group using only frozen V results and GT."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/086_global_demonstration_selection"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
from verifact_research.evaluation import evaluate
from common053 import VALID,decision,parse_response
from common066 import priorg
import run086

LABELS=("Supported","Not Supported","Not Addressed")


def put(path,obj):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write("\n")
def putl(path,rows):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")


def fallback_map():
    rows=run086.lines(ROOT/"outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")
    return {x["proposition_id"]:LABELS[x["u2"]] for x in rows}


def materialize(jobs,success,cases):
    fallback=fallback_map()
    byid={x["id"]:x for x in cases}
    rows=[]
    for job in jobs:
        match=success.get(job["request_id"])
        if match is None:raise RuntimeError("Incomplete V; no utility selection")
        receipt=run086.read(ROOT/match["receipt_source"])
        tr=receipt["transport"]
        parsed=parse_response(tr,True,True)
        if parsed.get("model_returned")!=run086.MODEL:raise RuntimeError("Judge model mismatch")
        valid=parsed["status"] in VALID and parsed.get("scores") is not None
        fb=fallback[job["id"]]
        labels={"raw":parsed["verdict"] if valid else fb,
                "U0":decision(parsed["scores"],0) if valid else fb,
                "U2":decision(parsed["scores"],2) if valid else fb,
                "PriorG":priorg(parsed["scores"]) if valid else fb}
        if any(v not in LABELS for v in labels.values()):raise RuntimeError("Bad label")
        rows.append({"id":job["id"],"sid":job["sid"],"arm":job["arm"],
                     "GT":byid[job["id"]]["GT"],"labels":labels,"valid":valid,
                     "status":parsed["status"],"scores":parsed.get("scores"),
                     "raw_verdict":parsed.get("verdict"),"fallback":fb,
                     "receipt_source":match["receipt_source"],"body_sha256":job["body_sha256"],
                     "usage":parsed.get("usage")})
    return rows


def metrics(rows,arm,method):
    sub=[x for x in rows if x["arm"]==arm]
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in sub]
    pred=[{"proposition_id":x["id"],"verdict":x["labels"][method]} for x in sub]
    ev=evaluate(cohort,pred,profile="none",missing="error")
    patient=defaultdict(list)
    for x in sub:patient[x["sid"]].append(x)
    patient_pa=sum(sum(x["labels"][method]==x["GT"] for x in z)/len(z) for z in patient.values())/len(patient)
    false_s=sum(x["GT"]!="Supported" and x["labels"][method]=="Supported" for x in sub)
    return {"n":len(sub),"patients":len(patient),"correct":sum(x["GT"]==x["labels"][method] for x in sub),
            "PA":ev["percent_agreement"],"MCC":ev["mcc"],"AC1":ev["gwet_ac1"],
            "patient_equal_PA":patient_pa,"false_S":false_s,
            "per_class":ev["per_class"],"confusion_matrix":ev["confusion_matrix"],
            "core_valid_n":sum(x["valid"] for x in sub)}


def main():
    freeze=run086.read(OUT/"freeze.json")
    if freeze["E_GT_read"] is not False:raise RuntimeError("E GT guard")
    jobs=run086.check_jobs("V")
    _,success,_=run086.state()
    cases=run086.lines(OUT/"V_cases.jsonl")
    rows=materialize(jobs,success,cases)
    groups=run086.read(OUT/"groups.json")
    utility={a:{m:metrics(rows,a,m) for m in ("raw","U0","U2","PriorG")} for a in groups}
    rank=sorted(groups,key=lambda a:(-utility[a]["PriorG"]["MCC"],
        -utility[a]["PriorG"]["patient_equal_PA"],utility[a]["PriorG"]["false_S"],
        groups[a]["system_chars"],a))
    winner=rank[0]
    putl(OUT/"V_predictions.jsonl",rows)
    put(OUT/"V_utility.json",{"status":"V_COMPLETE","metrics":utility,"rank":rank,
        "selection_rule":freeze["selection_rule"],"V_GT_only":True,"E_GT_read":False})
    put(OUT/"D_star_freeze.json",{"status":"FROZEN_BEFORE_E_NEW_API_AND_E_GT","name":winner,
        "rank":rank,"ordered_candidate_ids":groups[winner]["ordered_candidate_ids"],
        "V_predictions_sha256":run086.sha(OUT/"V_predictions.jsonl"),
        "V_utility_sha256":run086.sha(OUT/"V_utility.json"),
        "V_jobs_sha256":freeze["V_jobs_sha256"],"E_sample_sha256":freeze["E_cases_blind_sha256"],
        "E_GT_read":False})
    print(json.dumps({"D_star":winner,"rank":rank,"V_MCC":{a:utility[a]["PriorG"]["MCC"] for a in groups},
                      "E_GT_read":False},ensure_ascii=False))


if __name__=="__main__":main()
