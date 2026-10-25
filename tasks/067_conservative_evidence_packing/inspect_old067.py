import json
from pathlib import Path
A=Path(r"D:\Research-VeriFact\outputs\067_conservative_evidence_packing\attempts")
for stage in ("stage1v2","stage2v2","stage1","stage2"):
 vals=[]
 for p in A.glob("*/request.json"):
  x=json.load(open(p,encoding="utf-8"))
  if x.get("stage")==stage:vals.append(x.get("created_utc"))
 print(stage,len(vals),min(vals) if vals else None,max(vals) if vals else None)
