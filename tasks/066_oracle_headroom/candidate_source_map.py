import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
errs=[r for r in pred if r["TS_PriorG"]!=r["GT"]]
corpus={json.loads(l)["passage_id"] for l in open(ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",encoding="utf-8-sig") if l.strip()}
files=[
("031f","outputs/031_training_expansion_confirmation/candidate_freeze_001/candidates.jsonl"),
("031r","outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl"),
("020","outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl"),
("016","outputs/016_disagreement_triggered_review_validation/stage1/candidates_001/candidates.jsonl"),
("009","outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl"),
("008","outputs/008_retrieval_planning/candidates_001/candidates.jsonl"),
]
maps={}
for name,f in files:
 m={}
 for l in open(ROOT/f,encoding="utf-8-sig"):
  if not l.strip():continue
  x=json.loads(l);pid=str(x.get("proposition_id") or x.get("id") or "")
  if pid:m[pid]=x
 maps[name]=m
x28=json.load(open(ROOT/"outputs/028_traceable_claim_evidence_verification/preparation_001/candidates.json",encoding="utf-8-sig"))
maps["028"]={str(x.get("proposition_id") or x.get("id")):x for x in x28}
order=["031f","031r","020","016","009","008","028"]
ok=0
for r in errs:
 pid=r["id"];src=next((n for n in order if pid in maps[n]),None)
 x=maps[src][pid]
 cids=(x.get("candidate_ids") or {}).get("C48") or x.get("C48") or x.get("candidate_pids") or []
 present=sum(z in corpus for z in cids)
 print(pid,src,"c48",len(cids),"in031corpus",present)
 ok+=int(len(cids)>0 and present==len(cids))
print("all C48 fully recoverable",ok,"of",len(errs))
