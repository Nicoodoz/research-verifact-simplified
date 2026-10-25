"""Post-E analysis with shared evaluator; never used for choosing D*."""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/086_global_demonstration_selection"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
from verifact_research.evaluation import evaluate,paired_compare
from common053 import VALID,parse_response,decision
from common066 import priorg
import run086 as r

LABELS=("Supported","Not Supported","Not Addressed")
METHODS=("raw","U0","U2","PriorG")


def put(path,obj):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write("\n")
def putl(path,rows):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")


def summarize(rows,config,method):
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in rows]
    pred=[{"proposition_id":x["id"],"verdict":x["labels"][config][method]} for x in rows]
    ev=evaluate(cohort,pred,profile="research_patient",missing="error",iterations=1000)
    non_s=sum(x["GT"]!="Supported" for x in rows)
    false_s=sum(x["GT"]!="Supported" and x["labels"][config][method]=="Supported" for x in rows)
    return {"n":len(rows),"patients":len({x["sid"] for x in rows}),
        "correct":sum(x["GT"]==x["labels"][config][method] for x in rows),
        "MCC":ev["mcc"],"PA":ev["percent_agreement"],"AC1":ev["gwet_ac1"],
        "Macro_F1":statistics.mean((ev["per_class"][k]["f1"] or 0) for k in LABELS),
        "false_S":false_s,"non_S":non_s,"false_S_rate_nonS":false_s/non_s if non_s else None,
        "false_S_rate_all":false_s/len(rows),"per_class":ev["per_class"],
        "confusion_matrix":ev["confusion_matrix"],"patient_CI95":ev["confidence_intervals"]}


def compare(rows,base,candidate,method):
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in rows]
    pred=lambda arm:[{"proposition_id":x["id"],"verdict":x["labels"][arm][method]} for x in rows]
    paired=paired_compare(cohort,pred(base),pred(candidate),iterations=1000)
    rescue=[x["id"] for x in rows if x["labels"][base][method]!=x["GT"] and x["labels"][candidate][method]==x["GT"]]
    harm=[x["id"] for x in rows if x["labels"][base][method]==x["GT"] and x["labels"][candidate][method]!=x["GT"]]
    patients=defaultdict(lambda:[0,0])
    for x in rows:
        patients[x["sid"]][0]+=int(x["labels"][base][method]==x["GT"])
        patients[x["sid"]][1]+=int(x["labels"][candidate][method]==x["GT"])
    return {"paired":paired,"rescue_ids":rescue,"harm_ids":harm,"net_correct":len(rescue)-len(harm),
        "patient_wins":sum(z[1]>z[0] for z in patients.values()),
        "patient_losses":sum(z[1]<z[0] for z in patients.values()),
        "patient_ties":sum(z[1]==z[0] for z in patients.values()),
        "patient_correct_base_candidate":dict(sorted(patients.items()))}


def load_e():
    chosen=r.read(OUT/"D_star_freeze.json")
    ef=r.read(OUT/"E_jobs_freeze.json")
    if ef["D_star"]!=chosen["name"] or ef["D_star_freeze_sha256"]!=r.sha(OUT/"D_star_freeze.json"):
        raise RuntimeError("D* changed after E freeze")
    jobs=r.check_jobs("E")
    _,success,_=r.state()
    if any(j["request_id"] not in success for j in jobs):raise RuntimeError("E incomplete")
    source={x["id"]:x for x in r.lines(ROOT/"outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl") if x["cohort"]=="old352"}
    blind=r.lines(OUT/"E_cases_blind.jsonl")
    fb={x["proposition_id"]:LABELS[x["u2"]] for x in r.lines(ROOT/"outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")}
    rows={}
    for x in blind:
        old=source[x["id"]]
        if old["sid"]!=x["sid"]:raise RuntimeError("E source patient mismatch")
        # 082's historical fallback labels come from its own frozen provenance.
        # 032 U2 differs on some IDs; retain both. The old arms on these IDs
        # have valid core answers, so the mismatch does not affect old scores.
        if old["fallback_label"]!=fb[x["id"]] and not (
            old["arms"]["B"]["valid"] and old["arms"]["F4"]["valid"]):
            raise RuntimeError("Consequential historical fallback mismatch")
        rows[x["id"]]={"id":x["id"],"sid":x["sid"],"author":x["author"],"GT":old["GT"],
            "labels":{"Original":{m:old["original_verifact"] for m in METHODS},
                      "B_old":{m:old["methods"]["B"][m] for m in METHODS},
                      "F4_old":{m:old["methods"]["F4"][m] for m in METHODS}},
            "arms":{"B_old":{"valid":old["arms"]["B"]["valid"],"source":old["arms"]["B"]["receipt_source"]},
                    "F4_old":{"valid":old["arms"]["F4"]["valid"],"source":old["arms"]["F4"]["receipt_source"]}},
            "fallback":fb[x["id"]],"historical_fallback":old["fallback_label"],
            "historical_fallback_mismatch":old["fallback_label"]!=fb[x["id"]]}
    for j in jobs:
        match=success[j["request_id"]]
        tr=r.read(ROOT/match["receipt_source"])["transport"]
        parsed=parse_response(tr,True,True)
        if parsed.get("model_returned")!=r.MODEL:raise RuntimeError("Model mismatch")
        valid=parsed["status"] in VALID and parsed.get("scores") is not None
        row=rows[j["id"]];fallback=row["fallback"]
        label={"raw":parsed["verdict"] if valid else fallback,
            "U0":decision(parsed["scores"],0) if valid else fallback,
            "U2":decision(parsed["scores"],2) if valid else fallback,
            "PriorG":priorg(parsed["scores"]) if valid else fallback}
        if any(x not in LABELS for x in label.values()):raise RuntimeError("Invalid result label")
        name=j["arm"]+"_new"
        if name in row["labels"]:raise RuntimeError("Duplicate arm/ID")
        row["labels"][name]=label
        row["arms"][name]={"valid":valid,"status":parsed["status"],
            "raw_verdict":parsed.get("verdict"),"scores":parsed.get("scores"),
            "receipt_source":match["receipt_source"],"body_sha256":j["body_sha256"],
            "usage":parsed.get("usage")}
    result=list(rows.values())
    needed={a+"_new" for a in ef["arms"]}
    if any(not needed.issubset(x["labels"]) for x in result):raise RuntimeError("Missing core E arm")
    return result,ef


def main():
    rows,ef=load_e()
    putl(OUT/"E_predictions.jsonl",rows)
    main_names=["Original","B_old","F4_old"]+[a+"_new" for a in ef["arms"]]
    summaries={m:{arm:summarize(rows,arm,m) for arm in main_names} for m in METHODS}
    selected=ef["D_star"]+"_new";control=ef["nonutility_control"]+"_new"
    pairs=(("F4_new",selected),(control,selected),("B_old",selected),("F4_old","F4_new"))
    comparisons={m:{f"{cand} minus {base}":compare(rows,base,cand,m) for base,cand in pairs if base!=cand}
                 for m in METHODS}
    bridge=[x for x in rows if "B_new" in x["labels"]]
    assert len(bridge)==12
    bridge_table={m:{a:summarize(bridge,a,m) for a in ("B_old","B_new","F4_old","F4_new")}
                  for m in METHODS}
    author_strata={author:{method:{arm:summarize([x for x in rows if x["author"]==author],arm,method)
             for arm in ("F4_new",selected,control)} for method in ("raw","PriorG")}
             for author in sorted({x["author"] for x in rows})}
    new_core=[x for x in rows if all(x["arms"][a+"_new"]["valid"] for a in ef["arms"])]
    core_metrics={m:{a+"_new":summarize(new_core,a+"_new",m) for a in ef["arms"]} for m in METHODS} if new_core else {}
    attempts,_,_=r.state()
    charges=defaultdict(float); statuses=Counter()
    for x in attempts:
        charges[x["phase"]+"/"+x["arm"]]+=x["cost_or_unknown_cny"]
        statuses[str(x["http_status"])]+=1
    cost={"cap_original_cny":30,"total_original_or_unknown_cny":sum(x["cost_or_unknown_cny"] for x in attempts),
          "attempts":len(attempts),"http_status":dict(statuses),"by_phase_arm_cny":dict(charges),
          "unknown_reserved_cny":sum(x["cost_or_unknown_cny"] for x in attempts if x["http_status"] in (0,None)),
          "attempt_ledger":attempts}
    put(OUT/"cost_ledger.json",cost)
    put(OUT/"E_analysis.json",{"status":"E_COMPLETE","D_star":ef["D_star"],
        "nonutility_control":ef["nonutility_control"],"n":len(rows),"new_core_valid_n":len(new_core),
        "historical_fallback_mismatch_n":sum(x["historical_fallback_mismatch"] for x in rows),
        "summaries":summaries,"comparisons":comparisons,"bridge":bridge_table,
        "by_author":author_strata,"new_core_sensitivity":core_metrics,
        "E_predictions_sha256":r.sha(OUT/"E_predictions.jsonl"),
        "cost_ledger_sha256":r.sha(OUT/"cost_ledger.json")})
    print(json.dumps({"E_n":len(rows),"D_star":ef["D_star"],"control":ef["nonutility_control"],
        "G_correct":{a:summaries["PriorG"][a]["correct"] for a in main_names},
        "G_MCC":{a:round(summaries["PriorG"][a]["MCC"],4) for a in main_names},
        "cost":round(cost["total_original_or_unknown_cny"],6)},ensure_ascii=False))


if __name__=="__main__":main()
