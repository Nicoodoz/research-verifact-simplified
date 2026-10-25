import csv,json,collections,sys,numpy as np
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
OUT=ROOT/"outputs/067_conservative_evidence_packing"
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c,run067
rows=list(csv.DictReader(open(OUT/"results.csv",encoding="utf-8")))
packs={x["id"]:x for x in c.lines(OUT/"pack_mapping.jsonl")}
feats={x["id"]:x for x in c.lines(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl")}
_,term=run067.state()
def paired(a,b):
 res=collections.Counter();bygt=collections.Counter()
 for r in rows:
  ac=r[a]==r["GT"];bc=r[b]==r["GT"]
  k="rescue" if (not ac and bc) else "harm" if (ac and not bc) else "same"
  res[k]+=1
  if k!="same":bygt[(k,r["GT"],r[a],r[b])]+=1
 return res,bygt
for a,b in [("baseline_raw","new_raw"),("baseline_pg","new_pg"),("new_raw","new_pg"),("baseline_raw","baseline_pg")]:
 print("\n",a,"->",b,paired(a,b))
role_gt=collections.Counter();add_gt=collections.Counter()
for r in rows:
 mp=packs[r["id"]]
 gt=r["GT"]
 for role in mp.get("addition_roles",[]):role_gt[(gt,role)]+=1
 add_gt[gt]+=len(mp.get("added_pids",[]))
print("\nrole_by_gt")
for k,v in sorted(role_gt.items()):print(k,v)
print("add_by_gt",add_gt)
# score deltas on valid changed final judges
sd=collections.defaultdict(list)
for r in rows:
 mp=packs[r["id"]];rid=mp.get("judge_request_id")
 if not rid or rid not in term:continue
 z=term[rid]["parsed"]
 if not (z.get("status") in ("valid","valid_with_format_anomaly") and z.get("scores")):continue
 old=feats[r["id"]]["ts_scores"];new=z["scores"]
 for lab in c.LABELS:sd[(r["GT"],lab)].append(float(new[lab])-float(old[lab]))
print("\nmean score deltas by GT")
for gt in c.LABELS:
 print(gt,{lab:round(float(np.mean(sd[(gt,lab)])),3) for lab in c.LABELS})
# new false-S IDs
print("\nnew falseS")
for r in rows:
 if r["GT"]!="Supported" and r["new_pg"]=="Supported":
  print(r["id"],r["GT"],"base",r["baseline_pg"],"raw",r["new_raw"],"roles",packs[r["id"]].get("addition_roles"))
