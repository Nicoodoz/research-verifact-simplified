from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[2]
O=ROOT/"outputs/065_verification_evidence_construction"
cases={x["id"]:x for x in [json.loads(s) for s in (ROOT/"outputs/044_incremental_evidence_recovery/planning_001/eval_cases.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]}
R=list(csv.DictReader(open(O/"results.csv",encoding="utf-8-sig")))
M={(x["id"],x["condition"]):x for x in [json.loads(s) for s in (O/"final_mapping.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]}
for arm in ("B","C"):
 print("\n",arm,"CHANGES")
 for r in R:
  if r[arm] and r[arm]!=r["A"]:
   status=("RESCUE" if r["A"]!=r["GT"] and r[arm]==r["GT"] else
           "HARM" if r["A"]==r["GT"] and r[arm]!=r["GT"] else "CHANGE")
   m=M[(r["id"],arm)]
   print(status,r["id"],"sid",r["sid"],r["type"],r["author"],"GT",r["GT"],"A",r["A"],arm,r[arm],
         "passages",m["passage_n"],"external",m["external_kept"])
   print(" claim:",cases[r["id"]]["claim"][:300])
   print(" selected:",m["selected_ids"])
