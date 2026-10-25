from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/058_unlabeled_batch_scaling"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

fr=loadj(OUT/"freeze.json")
run=loadj(OUT/"run_summary.json")
sc=rows(OUT/"scaling_summary.csv")
agg=rows(OUT/"aggregate.csv")
checks=[]
def ck(name,ok,detail=""): checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})

ck("protocol_hash", sha(ROOT/"tasks/058_unlabeled_batch_scaling/protocol.md")==fr["protocol_sha256"])
ck("code_hash", sha(ROOT/"tasks/058_unlabeled_batch_scaling/run058.py")==fr["code_sha256"])
ck("run057_hash", sha(ROOT/"tasks/057_soft_shift_detection/run057.py")==fr["run057_sha256"])
ck("features052_hash", sha(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl")==fr["features_052_sha256"])
ck("features053_hash", sha(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl")==fr["features_053_sha256"])
ck("scaling_rows", len(sc)==60, len(sc))
ck("aggregate_rows", len(agg)==10, len(agg))
ck("pool_sizes", run["pools"]=={"052":236,"053":237}, run["pools"])
ck("zero_api", run["new_api_calls"]==0)
ck("no_reserved", run["reserved_used"] is False)
ck("rates_in_bounds", all(0<=float(r["h0_false_alarm"])<=1 and 0<=float(r["h1_detection"])<=1 for r in sc))
ck("mean90_both", run["mean90_both_directions"] is True)

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
