"""Deferred four-arm evaluator. Never invoked during 085A preparation."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/085_r1_70b_model_swap"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
from verifact_research.evaluation import evaluate, paired_compare
from common053 import decision
from common066 import priorg

LABELS=("Supported","Not Supported","Not Addressed")
ARMS=("V4-B","V4-F4","R1-B","R1-F4")


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s]


def load_checked(r1_path:Path):
    freeze=json.loads((OUT/"source_manifest.json").read_text(encoding="utf-8"))
    for rel,expected in freeze["source_sha256"].items():
        if sha(ROOT/rel)!=expected: raise RuntimeError(f"Source changed: {rel}")
    profile=OUT/"deferred_preflight/parser_profile_frozen.json"
    if not profile.exists() or json.loads(profile.read_text(encoding="utf-8")).get("status")!="FROZEN_AFTER_AB_NO_GT":
        raise RuntimeError("R1 parser must be frozen from A/B before evaluation")
    manifest=lines(OUT/"frozen_cohort_manifest.jsonl")
    ids={x["id"] for x in manifest}
    if len(manifest)!=180 or len(ids)!=180 or len({x["sid"] for x in manifest})!=21:
        raise RuntimeError("Frozen cohort mismatch")
    r1=lines(r1_path)
    pairs={(x["id"],x["arm"]):x for x in r1}
    if len(pairs)!=360 or set(pairs)!={(pid,arm) for pid in ids for arm in ("B","F4")}:
        raise RuntimeError("R1 predictions must have exactly 360 unique frozen ID/arm rows")
    for x in r1:
        if x.get("sid")!=next(m["sid"] for m in manifest if m["id"]==x["id"]):
            raise RuntimeError("R1 patient mismatch")
        if x.get("valid") and x.get("verdict") not in LABELS:
            raise RuntimeError("Invalid R1 raw verdict")
        if x.get("valid") and not x.get("raw_response_sha256"):
            raise RuntimeError("Every R1 valid prediction needs raw response SHA")
        if x.get("parser_profile_sha256")!=sha(profile):
            raise RuntimeError("R1 row parser profile fingerprint mismatch")
        raw_path=x.get("raw_response_path")
        if not raw_path or not (ROOT/raw_path).is_file() or sha(ROOT/raw_path)!=x.get("raw_response_sha256"):
            raise RuntimeError("R1 raw response missing or SHA mismatch")
    v4=lines(ROOT/"outputs/084_f4_coverage_validation/new_predictions.jsonl")
    if len(v4)!=180 or {x["id"] for x in v4}!=ids:
        raise RuntimeError("V4 cohort mismatch")
    return manifest,pairs,{x["id"]:x for x in v4}


def prediction(row,arm):
    return {"proposition_id":row["id"],"verdict":row["labels"][arm]}


def summary(rows,arm):
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in rows]
    preds=[prediction(x,arm) for x in rows]
    ev=evaluate(cohort,preds,profile="research_patient",missing="error",iterations=1000)
    non_s=sum(x["GT"]!="Supported" for x in rows)
    false_s=sum(x["GT"]!="Supported" and x["labels"][arm]=="Supported" for x in rows)
    return {"n":len(rows),"patients":len({x["sid"] for x in rows}),
        "correct":sum(x["GT"]==x["labels"][arm] for x in rows),
        "PA":ev["percent_agreement"],"MCC":ev["mcc"],"AC1":ev["gwet_ac1"],
        "macro_F1":statistics.mean((ev["per_class"][k]["f1"] or 0) for k in LABELS),
        "false_S":false_s,"non_S":non_s,"false_S_rate_nonS":false_s/non_s if non_s else None,
        "per_class":ev["per_class"],"confusion_matrix":ev["confusion_matrix"],
        "patient_CI95":ev["confidence_intervals"]}


def compare(rows,base,candidate):
    cohort=[{"proposition_id":x["id"],"subject_id":x["sid"],"human_gt":x["GT"]} for x in rows]
    b=[prediction(x,base) for x in rows]
    c=[prediction(x,candidate) for x in rows]
    paired=paired_compare(cohort,b,c,iterations=1000)
    rescue=[x["id"] for x in rows if x["labels"][base]!=x["GT"] and x["labels"][candidate]==x["GT"]]
    harm=[x["id"] for x in rows if x["labels"][base]==x["GT"] and x["labels"][candidate]!=x["GT"]]
    patient=defaultdict(lambda:[0,0])
    for x in rows:
        patient[x["sid"]][0]+=int(x["labels"][base]==x["GT"])
        patient[x["sid"]][1]+=int(x["labels"][candidate]==x["GT"])
    return {"candidate_minus_baseline":paired,"rescued_ids":rescue,"harmed_ids":harm,
        "net_correct":len(rescue)-len(harm),"patient_wins":sum(v[1]>v[0] for v in patient.values()),
        "patient_losses":sum(v[1]<v[0] for v in patient.values()),
        "patient_ties":sum(v[1]==v[0] for v in patient.values())}


def effect_difference(rows):
    def value(sub):
        n=len(sub)
        return (sum(x["GT"]==x["labels"]["R1-F4"] for x in sub)
                -sum(x["GT"]==x["labels"]["R1-B"] for x in sub)
                -sum(x["GT"]==x["labels"]["V4-F4"] for x in sub)
                +sum(x["GT"]==x["labels"]["V4-B"] for x in sub))/n
    groups=defaultdict(list)
    for x in rows: groups[x["sid"]].append(x)
    patients=sorted(groups)
    draws=[]
    for seed in range(1000):
        rng=random.Random(seed)
        sub=[x for sid in rng.choices(patients,k=len(patients)) for x in groups[sid]]
        draws.append(value(sub))
    draws.sort()
    return {"delta_PA_effect_difference":value(rows),"patient_bootstrap_CI95":[draws[24],draws[974]]}


def main():
    p=argparse.ArgumentParser(description="Formal 085 only, never during 085A")
    p.add_argument("--r1-predictions",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--allow-evaluation",action="store_true")
    args=p.parse_args()
    if not args.allow_evaluation:
        raise PermissionError("Formal 085 analysis requires --allow-evaluation")
    manifest,r1,v4=load_checked(args.r1_predictions)
    common=[]; invalid=[]; secondary=[]
    for m in manifest:
        pid=m["id"]; b=r1[pid,"B"]; f=r1[pid,"F4"]; old=v4[pid]
        if not (b.get("valid") and f.get("valid") and old["arms"]["B"]["valid"] and old["arms"]["F4"]["valid"]):
            invalid.append({"id":pid,"sid":m["sid"],"R1_B_valid":bool(b.get("valid")),
                            "R1_F4_valid":bool(f.get("valid")),"V4_B_valid":old["arms"]["B"]["valid"],
                            "V4_F4_valid":old["arms"]["F4"]["valid"]})
            continue
        row={"id":pid,"sid":m["sid"],"GT":old["GT"],"labels":{
            "V4-B":old["arms"]["B"]["raw"],"V4-F4":old["arms"]["F4"]["raw"],
            "R1-B":b["verdict"],"R1-F4":f["verdict"]}}
        if any(v not in LABELS for v in row["labels"].values()): raise RuntimeError("Invalid four-arm verdict")
        common.append(row)
        if b.get("label_scores") and f.get("label_scores"):
            scores={"B":b["label_scores"],"F4":f["label_scores"]}
            secondary.append({"id":pid,"sid":m["sid"],"GT":old["GT"],"labels":{
                f"R1-{a}-{method}":fn(scores[a]) for a in ("B","F4") for method,fn in (
                    ("U0",lambda s:decision(s,0)),("U2",lambda s:decision(s,2)),("FrozenPriorG",priorg))}})
    if not common: raise RuntimeError("No complete common-valid cases")
    result={"status":"FORMAL_085_FUTURE","frozen_n":180,"common_valid_n":len(common),
        "invalid_or_missing":invalid,"primary":{a:summary(common,a) for a in ARMS},
        "comparisons":{f"{c} minus {b}":compare(common,b,c) for b,c in (
            ("V4-B","R1-B"),("R1-B","R1-F4"),("V4-F4","R1-F4"))},
        "F4_cross_model_effect":effect_difference(common),
        "secondary_score_valid_n":len(secondary),
        "secondary_compatibility":{a:summary(secondary,a) for a in secondary[0]["labels"]} if secondary else {},
        "secondary_warning":"Frozen PriorG is V4-trained compatibility only; no R1 fitting"}
    with args.output.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(result,f,ensure_ascii=False,indent=2,sort_keys=True)
        f.write("\n")
    print(json.dumps({"frozen":180,"common_valid":len(common),"secondary":len(secondary)},ensure_ascii=False))


if __name__=="__main__": main()
