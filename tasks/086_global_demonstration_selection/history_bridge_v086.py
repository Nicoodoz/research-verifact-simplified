"""Compare exact old/new F4 on V only; a batch-variability diagnostic."""
from __future__ import annotations

import json
import sys

import run086 as r
import select086 as s

ROOT=r.ROOT;OUT=r.OUT
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
from common053 import VALID,decision
from common066 import priorg
from verifact_research.evaluation import evaluate,paired_compare


def main():
    old={x["id"]:x for x in r.lines(ROOT/"outputs/079_f4_priorg_adaptation/calibration_predictions.jsonl")}
    new={x["id"]:x for x in r.lines(OUT/"V_predictions.jsonl") if x["arm"]=="F4"}
    jobs={x["id"]:x for x in r.lines(OUT/"V_jobs.jsonl") if x["arm"]=="F4"}
    fallback=s.fallback_map()
    rows=[]
    for pid,now in new.items():
        original=old[pid]["F4"]
        req=r.read(ROOT/original["request_source"])
        body=req["job"]["body"]
        if r.h(r.canonical(body))!=jobs[pid]["body_sha256"]:raise RuntimeError("Not an exact F4 prompt bridge")
        p=original["parsed"]
        valid=p["status"] in VALID and p.get("scores") is not None
        score=p.get("scores")
        old_label={"raw":p["verdict"] if valid else fallback[pid],
                   "PriorG":priorg(score) if valid else fallback[pid]}
        rows.append({"id":pid,"sid":now["sid"],"GT":now["GT"],"old":old_label,
                     "new":{"raw":now["labels"]["raw"],"PriorG":now["labels"]["PriorG"]},
                     "old_valid":valid,"new_valid":now["valid"]})
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in rows]
    result={"status":"EXACT_BODY_HISTORICAL_V_BRIDGE","n":len(rows),"methods":{}}
    for method in ("raw","PriorG"):
        pred=lambda key:[{"proposition_id":x["id"],"verdict":x[key][method]} for x in rows]
        result["methods"][method]={"old_correct":sum(x["old"][method]==x["GT"] for x in rows),
            "new_correct":sum(x["new"][method]==x["GT"] for x in rows),
            "changed_labels":sum(x["old"][method]!=x["new"][method] for x in rows),
            "paired":paired_compare(cohort,pred("old"),pred("new"),iterations=1000)}
    s.put(OUT/"V_old_new_F4_bridge.json",result)
    print(json.dumps({"n":len(rows),"methods":{k:{x:v[x] for x in ("old_correct","new_correct","changed_labels")}
                                           for k,v in result["methods"].items()}},ensure_ascii=False))


if __name__=="__main__":main()
