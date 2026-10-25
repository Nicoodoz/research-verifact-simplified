"""Offline V leave-one-patient-out rank stability; never reselects official D*."""
from __future__ import annotations

import json
from collections import Counter

import run086 as r
import select086 as s

OUT=r.OUT


def main():
    official=r.read(OUT/"D_star_freeze.json")
    rows=r.lines(OUT/"V_predictions.jsonl")
    groups=r.read(OUT/"groups.json")
    patients=sorted({x["sid"] for x in rows})
    folds=[]
    for held in patients:
        subset=[x for x in rows if x["sid"]!=held]
        m={a:s.metrics(subset,a,"PriorG") for a in groups}
        rank=sorted(groups,key=lambda a:(-m[a]["MCC"],-m[a]["patient_equal_PA"],
            m[a]["false_S"],groups[a]["system_chars"],a))
        folds.append({"held_out_sid":held,"rank":rank,"winner":rank[0],
                      "MCC":{a:m[a]["MCC"] for a in rank},
                      "official_D_star_rank":rank.index(official["name"])+1})
    result={"status":"OFFLINE_V_SENSITIVITY_NOT_INDEPENDENT_API",
            "official_D_star":official["name"],"folds":folds,
            "winner_counts":dict(Counter(x["winner"] for x in folds)),
            "D_star_top1":sum(x["winner"]==official["name"] for x in folds),
            "D_star_top2":sum(x["official_D_star_rank"]<=2 for x in folds),
            "selection_unchanged":True}
    s.put(OUT/"V_LOPO_sensitivity.json",result)
    print(json.dumps({"official":official["name"],"winner_counts":result["winner_counts"]},ensure_ascii=False))


if __name__=="__main__":main()
