import csv,json,gzip
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
err={r["id"] for r in pred if r["TS_PriorG"]!=r["GT"]}
files=[
"outputs/036_final_validation/retrieval_001/candidates.jsonl",
"outputs/036_final_validation/candidate_freeze_001/candidates.jsonl",
"outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",
"outputs/031_training_expansion_confirmation/candidate_freeze_001/candidates.jsonl",
"outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl",
"outputs/016_disagreement_triggered_review_validation/stage1/candidates_001/candidates.jsonl",
"outputs/008_retrieval_planning/candidates_001/candidates.jsonl",
"outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl",
]
def ids_jsonl(p):
 out=set()
 if not p.exists(): return out
 for l in open(p,encoding="utf-8-sig"):
  if not l.strip():continue
  try:x=json.loads(l)
  except:continue
  for k in ("proposition_id","id","claim_id"):
   if k in x: out.add(str(x[k]));break
 return out
U=set()
for f in files:
 p=ROOT/f; ids=ids_jsonl(p);hit=err&ids;U|=hit
 print(f,len(ids),"hit",len(hit))
p28=ROOT/"outputs/028_traceable_claim_evidence_verification/preparation_001/candidates.json"
x=json.load(open(p28,encoding="utf-8-sig"));ids28={str(z.get("proposition_id") or z.get("id")) for z in x};hit=err&ids28;U|=hit
print("028",len(ids28),"hit",len(hit))
print("UNION",len(U),"of",len(err))
print("missing",sorted(err-U))
