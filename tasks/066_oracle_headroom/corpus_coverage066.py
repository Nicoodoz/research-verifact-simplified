import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
err=[r for r in pred if r["TS_PriorG"]!=r["GT"]]
corpora=[
("031","outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"),
("020","outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl"),
("016","outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl"),
("009","outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl"),
]
sidsets={}
for name,f in corpora:
 s=set()
 for l in open(ROOT/f,encoding="utf-8-sig"):
  if not l.strip():continue
  x=json.loads(l);s.add(str(x.get("subject_id") or x.get("sid") or ""))
 sidsets[name]=s;print(name,len(s))
miss=[]
for r in err:
 sid=str(r["sid"]);src=[n for n in ("031","020","016","009") if sid in sidsets[n]]
 print(r["id"],sid,src)
 if not src:miss.append((r["id"],sid))
print("missing",miss)
