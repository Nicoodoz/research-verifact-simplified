"""Post hoc descriptive F4 vs pre-frozen R1 control; no reselection."""
from __future__ import annotations

import json

import analyze086 as a
import run086 as r
import select086 as s


def main():
    e=r.read(r.OUT/"E_jobs_freeze.json")
    rows=r.lines(r.OUT/"E_predictions.jsonl")
    control=e["nonutility_control"]+"_new"
    result={"status":"FROZEN_CONTROL_DESCRIPTIVE","control":control,
            "methods":{m:a.compare(rows,"F4_new",control,m) for m in ("raw","PriorG")}}
    s.put(r.OUT/"control_comparison.json",result)
    print(json.dumps({m:{"net":v["net_correct"],"delta_MCC":v["paired"]["metrics"]["mcc"]["delta"]}
                      for m,v in result["methods"].items()},ensure_ascii=False))


if __name__=="__main__":main()
