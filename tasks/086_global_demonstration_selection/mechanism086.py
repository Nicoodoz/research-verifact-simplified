"""Offline attribution ledger for D* vs same-batch F4; output-level facts only."""
from __future__ import annotations

import json
from collections import Counter,defaultdict
from statistics import mean

import run086 as r
import select086 as s

OUT=r.OUT


def main():
    analysis=r.read(OUT/"E_analysis.json")
    rows=r.lines(OUT/"E_predictions.jsonl")
    chosen=analysis["D_star"]+"_new"
    control=analysis["nonutility_control"]+"_new"
    cases=[]
    for x in rows:
        f=x["labels"]["F4_new"];d=x["labels"][chosen]
        fc=x["arms"]["F4_new"]["valid"];dc=x["arms"][chosen]["valid"]
        raw_flip=(f["raw"]!=d["raw"])
        final_flip=(f["PriorG"]!=d["PriorG"])
        if not final_flip and not raw_flip:kind="unchanged_raw_and_final"
        elif final_flip and raw_flip:kind="raw_and_final_change"
        elif final_flip:kind="final_only_score_boundary_change"
        else:kind="raw_only_no_final_change"
        cases.append({"id":x["id"],"sid":x["sid"],"GT":x["GT"],"F4_raw":f["raw"],
            "D_raw":d["raw"],"F4_final":f["PriorG"],"D_final":d["PriorG"],
            "F4_valid":fc,"D_valid":dc,"kind":kind,
            "rescued_final":f["PriorG"]!=x["GT"] and d["PriorG"]==x["GT"],
            "harmed_final":f["PriorG"]==x["GT"] and d["PriorG"]!=x["GT"],
            "rescued_raw":f["raw"]!=x["GT"] and d["raw"]==x["GT"],
            "harmed_raw":f["raw"]==x["GT"] and d["raw"]!=x["GT"]})
    usage={}
    for arm in ("F4_new",chosen,control):
        arr=[x["arms"][arm]["usage"] for x in rows if x["arms"][arm].get("usage")]
        usage[arm]={"n":len(arr),"prompt_tokens_mean":mean(z["prompt_tokens"] for z in arr) if arr else None,
                    "completion_tokens_mean":mean(z["completion_tokens"] for z in arr) if arr else None}
    summaries={"kind_counts":dict(Counter(x["kind"] for x in cases)),
        "final_rescue_by_kind":{k:sum(x["rescued_final"] for x in cases if x["kind"]==k)
                                for k in sorted({x["kind"] for x in cases})},
        "final_harm_by_kind":{k:sum(x["harmed_final"] for x in cases if x["kind"]==k)
                              for k in sorted({x["kind"] for x in cases})},
        "final_rescue_GT":dict(Counter(x["GT"] for x in cases if x["rescued_final"])),
        "final_harm_GT":dict(Counter(x["GT"] for x in cases if x["harmed_final"])),
        "raw_rescue":sum(x["rescued_raw"] for x in cases),
        "raw_harm":sum(x["harmed_raw"] for x in cases),
        "final_rescue":sum(x["rescued_final"] for x in cases),
        "final_harm":sum(x["harmed_final"] for x in cases),
        "core_valid_both_n":sum(x["F4_valid"] and x["D_valid"] for x in cases),
        "usage":usage,
        "warning":"Output-level label/score changes cannot establish the Judge's internal mechanism or new clinical GT."}
    s.putl(OUT/"mechanism_cases.jsonl",cases)
    s.put(OUT/"mechanism_summary.json",summaries)
    print(json.dumps({k:summaries[k] for k in ("kind_counts","raw_rescue","raw_harm","final_rescue","final_harm")},ensure_ascii=False))


if __name__=="__main__":main()
