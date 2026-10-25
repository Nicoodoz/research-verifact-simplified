import json
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
OUT=ROOT/"outputs/067_conservative_evidence_packing"
formal=set()
for f in ("stage1_jobs.jsonl","stage2_jobs.jsonl"):
 for l in open(OUT/f,encoding="utf-8"):
  if l.strip():formal.add(json.loads(l)["request_id"])
cost=0;http=0;n=0;other=0;othercost=0
for p in (OUT/"attempts").glob("*/request.json"):
 rq=json.load(open(p,encoding="utf-8"));rid=rq["job"]["request_id"];rp=p.parent/"receipt.json"
 if not rp.exists():continue
 rec=json.load(open(rp,encoding="utf-8"))["transport"]
 # exact charge from response usage
 try:
  body=json.loads(rec["body_text"]);u=body["usage"];mk=rq["job"]["model_key"];prices={"qwen":(3,12),"deepseek":(3,9)};ip,op=prices[mk]
  amt=(int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
 except:amt=float(rq["reservation_cny"])
 if rid in formal:
  n+=1;cost+=amt;http+=rec.get("http_status")==200
 else:
  other+=1;othercost+=amt
print({"formal_requests":len(formal),"formal_receipts":n,"formal_http200":http,"formal_cost":cost,"superseded_receipts":other,"superseded_cost":othercost})
