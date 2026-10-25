import json,re
from pathlib import Path
from collections import Counter
ROOT=Path(r"D:\Research-VeriFact")
F=[json.loads(x) for x in (ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
C={x["id"]:x for x in (json.loads(l) for l in open(ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl",encoding="utf-8-sig") if l.strip())}
SRC={
"031":("outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl","outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"),
"020":("outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl","outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl"),
"009":("outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl","outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl")}
def loadcand(p):
 m={}
 for l in open(ROOT/p,encoding="utf-8-sig"):
  if not l.strip():continue
  x=json.loads(l);ids=(x.get("candidate_ids") or {}).get("C48")
  if isinstance(ids,list) and ids:m[x["proposition_id"]]=ids
 return m
def norm(s):return re.sub(r"\s+"," ",s).strip().lower()
CM={};COR={}
for n,(cp,co) in SRC.items():
 CM[n]=loadcand(cp);COR[n]={x["passage_id"]:x for x in (json.loads(l) for l in open(ROOT/co,encoding="utf-8-sig") if l.strip())}
stats=Counter();matches=[]
for f in F:
 pid=f["id"];ref=norm(C[pid]["reference"]);best=None
 for n in SRC:
  if pid not in CM[n]:continue
  ids=CM[n][pid];m=sum(1 for z in ids if z in COR[n] and norm(COR[n][z]["text"]) in ref)
  score=(m,-["031","020","009"].index(n))
  if best is None or score>best[0]:best=(score,n,m,len(ids))
 if best:
  stats[best[1]]+=1;matches.append(best[2])
 else:stats["missing"]+=1
print(stats)
print("mapped",len(matches),"mean baseline-contained C48",sum(matches)/len(matches),"zero_match",sum(m==0 for m in matches),"max",max(matches) if matches else None)
print("match hist",Counter(matches))
