import csv,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(r"D:\Research-VeriFact"); OUT=ROOT/"outputs/067_conservative_evidence_packing"
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c,run067
R=list(csv.DictReader(open(OUT/"results_v2.csv",encoding="utf-8")))
cases={x["id"]:x for x in c.lines(OUT/"cases_blind_v2.jsonl")}
maps={x["id"]:x for x in c.lines(OUT/"pack_mapping_v2.jsonl")}
_,term=run067.state()
res=[r for r in R if r["rescue"]=="True"]; harms=[r for r in R if r["harm"]=="True"]
raw_res=[r for r in R if r["baseline_raw"]!=r["GT"] and r["final_raw"]==r["GT"]]
raw_harm=[r for r in R if r["baseline_raw"]==r["GT"] and r["final_raw"]!=r["GT"]]
print("FINAL rescues",len(res),"harms",len(harms))
for r in res:
 print("\nRESCUE",r["id"],"sid",r["sid"],"GT",r["GT"],"baseline",r["baseline"],"final",r["final"],"raw",r["baseline_raw"],"->",r["final_raw"])
 print("CLAIM",cases[r["id"]]["claim"]); print("roles",r["roles"],"add/drop",r["added_n"],r["dropped_n"])
print("\nRAW rescues",len(raw_res),"harms",len(raw_harm))
for r in raw_res: print("RAW+",r["id"],r["GT"],r["baseline_raw"],"->",r["final_raw"],"PriorG",r["baseline"],"->",r["final"])
# audit invalid error reasons
errs=Counter()
for rid,z in term.items():
 if not rid.startswith("067v2_audit_"):continue
 p=z["parsed"]
 if p.get("status")!="valid":
  for e in p.get("errors",[]):errs[e]+=1
print("\nINVALID AUDIT",sum(errs.values()),errs.most_common(20))
# final-label transitions among changed
print("changed transitions",Counter((r["baseline"],r["final"],r["GT"]) for r in R if r["changed"]=="True"))
