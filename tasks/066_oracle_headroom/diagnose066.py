import csv,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(r"D:\Research-VeriFact")
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c, run066
OUT=ROOT/"outputs/066_oracle_headroom"
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
byid={r["id"]:r for r in pred};errors={r["id"] for r in pred if r["TS_PriorG"]!=r["GT"]}
maps={x["id"]:x for x in c.lines(OUT/"final_mapping.jsonl")}
ev={r["id"]:r for r in csv.DictReader(open(OUT/"evidence_cases.csv",encoding="utf-8"))}
qrows={x["id"]:x for x in c.lines(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl")}
_,term=run066.state()
reasonfix={}
for r in pred:
 cand=[r["TS_PriorG"]]
 if r.get("NS_U0") in c.LABELS:cand.append(r["NS_U0"])
 if r.get("TS_status")=="valid" and r.get("TS_raw") in c.LABELS:cand.append(r["TS_raw"])
 if r["id"] in qrows:
  q=qrows[r["id"]]["qwen_scores"];cand.append(max(c.LABELS,key=lambda k:float(q[k])))
 reasonfix[r["id"]]=r["GT"] in cand
rawfix=0;pgfix=0;raw_only=0;pg_only=0
neither=Counter();neither_gt=Counter()
for pid in sorted(errors):
 mp=maps[pid];rid=mp.get("judge_request_id");raw=None;pg=None
 if rid and rid in term:
  z=term[rid]["parsed"]
  if z.get("status") in ("valid","valid_with_format_anomaly") and z.get("verdict") in c.LABELS and z.get("scores"):
   raw=z["verdict"];pg=c.priorg(z["scores"])
 rf=raw==byid[pid]["GT"];pf=pg==byid[pid]["GT"]
 rawfix+=rf;pgfix+=pf;raw_only+=rf and not pf;pg_only+=pf and not rf
 if not reasonfix[pid] and not pf:
  decisive=bool(mp.get("composer_decisive"))
  valid=bool(rid and rid in term)
  key=("decisive" if decisive else "nondecisive")+("_judge" if valid else "_nojudge")
  neither[key]+=1;neither_gt[byid[pid]["GT"]]+=1
print("Evidence raw fix",rawfix,"PriorG fix",pgfix,"raw_only",raw_only,"pg_only",pg_only)
print("Neither diagnostic",neither,"GT",neither_gt)
