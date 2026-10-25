"""Persist bridge-pair discrepancies before any 009 development Judge calls."""
import study009 as s
from io009 import stage,rerank_scores

if __name__=="__main__":
    values,_=stage("dev_rerank")
    pairs=[]
    for item in s.pilot.jsonl(s.OUT/"development_001/preparation/inputs.jsonl"):
        if not item["sentinel_ids"]:
            continue
        value=values["dev_rerank:"+item["proposition_id"]]
        scores=rerank_scores(value)
        for key in item["sentinel_ids"]:
            pairs.append(dict(case_id=item["case_id"],proposition_id=item["proposition_id"],passage_id=key,old=item["cached_scores"][key],new=scores[key],
                absolute_difference=abs(item["cached_scores"][key]-scores[key])))
    out=s.OUT/"rerank_drift_001"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(out/"pairs.json",pairs)
    summary=dict(pairs=len(pairs),over_1e_6=sum(x["absolute_difference"]>1e-6 for x in pairs),max_difference=max(x["absolute_difference"] for x in pairs),
        development_Judge_calls=0,action="Do not mix cached and fresh pair scores; freeze a refresh under an unused existing budget slot",cause="Uncertain: batch numeric behavior or service changes are not distinguishable here")
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[s.OUT/"development_001/preparation/manifest.json",s.OUT/"live/dev_rerank/state.json"],[s.TASK/"inspect_rerank_drift.py",s.TASK/"io009.py"])
    print(s.pilot.canonical(summary))
    print(s.pilot.canonical(pairs))
