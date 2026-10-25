"""GT-blind claim text overlap check across D/V/E."""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/"outputs/086_global_demonstration_selection"


def lines(name):return [json.loads(s) for s in (OUT/name).read_text(encoding="utf-8").splitlines() if s]
def norm(s):return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()


def main():
    d=lines("candidate_pool.jsonl");v=lines("V_cases.jsonl");e=lines("E_cases_blind.jsonl")
    result={}
    for name,targets in (("D_vs_V",v),("D_vs_E",e)):
        scored=[]
        for x in d:
            for y in targets:
                ratio=SequenceMatcher(None,norm(x["claim"]),norm(y["claim"]),autojunk=False).ratio()
                scored.append((ratio,x["candidate_id"],y["id"],x["sid"],y["sid"]))
        scored.sort(reverse=True)
        result[name]={"max_ratio":scored[0][0],"over_0_85":sum(z[0]>=.85 for z in scored),
                      "top_10":[{"ratio":z[0],"candidate_id":z[1],"target_id":z[2],
                                  "candidate_sid":z[3],"target_sid":z[4]} for z in scored[:10]]}
    result["uses_E_GT"]=False
    with (OUT/"claim_overlap_check.json").open("x",encoding="utf-8",newline="\n") as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
    print(json.dumps({k:{"max_ratio":v["max_ratio"],"over_0_85":v["over_0_85"]}
                     for k,v in result.items() if k!="uses_E_GT"},ensure_ascii=False))


if __name__=="__main__":main()
