import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
P=list(csv.DictReader(open(ROOT/"outputs/052_first_tier_validation/predictions.csv",encoding="utf-8-sig")))
ids={r["id"] for r in P}
print("052",len(P),"patients",len(set(r["sid"] for r in P)))
files=[
("031","outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl"),
("020","outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl"),
("016","outputs/016_disagreement_triggered_review_validation/stage1/candidates_001/candidates.jsonl"),
("009","outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl"),
("008","outputs/008_retrieval_planning/candidates_001/candidates.jsonl"),
]
U=set()
for name,f in files:
 hit=set()
 for l in open(ROOT/f,encoding="utf-8-sig"):
  if not l.strip():continue
  x=json.loads(l);pid=str(x.get("proposition_id") or x.get("id") or "")
  c=(x.get("candidate_ids") or {}).get("C48") or x.get("C48")
  if pid in ids and isinstance(c,list) and c:hit.add(pid)
 U|=hit;print(name,len(hit))
print("union",len(U),"of",len(ids))
print("missing",len(ids-U))
