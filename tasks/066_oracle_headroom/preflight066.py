import csv,json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
cases={x["id"]:x for x in (json.loads(l) for l in open(ROOT/"outputs/053_thinking_prior_validation/evaluation_cases.jsonl",encoding="utf-8-sig") if l.strip())}
cand={x["proposition_id"]:x for x in (json.loads(l) for l in open(ROOT/"outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",encoding="utf-8-sig") if l.strip())}
inp={x["proposition_id"]:x for x in (json.loads(l) for l in open(ROOT/"outputs/031_training_expansion_confirmation/materials_001/inputs.jsonl",encoding="utf-8-sig") if l.strip())}
err=[r for r in pred if r["TS_PriorG"]!=r["GT"]]
print("errors",len(err))
print("byGT", {g:sum(r["GT"]==g for r in err) for g in ("Supported","Not Supported","Not Addressed")})
print("missing_cases",sum(r["id"] not in cases for r in err))
print("missing_cand",sum(r["id"] not in cand for r in err))
print("missing_inputs",sum(r["id"] not in inp for r in err))
print("c48 sizes",sorted(set(len(cand[r["id"]]["candidate_ids"]["C48"]) for r in err if r["id"] in cand)))
