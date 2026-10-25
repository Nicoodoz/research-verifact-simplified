import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
err=[r for r in pred if r["TS_PriorG"]!=r["GT"]]
c31={x["proposition_id"] for x in (json.loads(l) for l in open(ROOT/"outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",encoding="utf-8-sig") if l.strip())}
c28=json.load(open(ROOT/"outputs/028_traceable_claim_evidence_verification/preparation_001/candidates.json",encoding="utf-8-sig"))
if isinstance(c28,list):
 ids28={str(x.get("proposition_id") or x.get("id")) for x in c28}
elif isinstance(c28,dict):
 ids28=set(c28.keys())
else: ids28=set()
print("err",len(err),"031",sum(r["id"] in c31 for r in err),"028",sum(r["id"] in ids28 for r in err),"union",sum(r["id"] in c31 or r["id"] in ids28 for r in err))
print("missing", [r["id"] for r in err if r["id"] not in c31 and r["id"] not in ids28])
print("c28type",type(c28).__name__,"n",len(c28))
