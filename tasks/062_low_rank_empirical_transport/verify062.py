from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/062_low_rank_empirical_transport"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

fr=loadj(OUT/"freeze.json")
run=loadj(OUT/"run_summary.json")
actual=rows(OUT/"actual_unlabeled.csv")
syn=rows(OUT/"synthetic_summary.csv")
nulls=rows(OUT/"null_summary.csv")
ev=rows(OUT/"actual_evaluation.csv")
checks=[]
def ck(name,ok,detail=""):
    checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})

ck("code_hash",sha(ROOT/"tasks/062_low_rank_empirical_transport/run062.py")==fr["code_sha256"])
for key,meta in fr["inputs"].items():
    ck("input_hash_"+key,sha(ROOT/meta["path"])==meta["sha256"])
ck("blind_actual_hash",sha(OUT/"actual_unlabeled.csv")==run["actual_unlabeled_sha256_before_gt_evaluation"])
ck("actual_no_GT_true",all("GT" not in r and not any(k.startswith("true_") for k in r) for r in actual))
ck("actual_rows",len(actual)==4,len(actual))
ck("synthetic_rows",len(syn)==152,len(syn))
ck("null_rows",len(nulls)==32,len(nulls))
ck("actual_eval_rows",len(ev)==4,len(ev))
ck("pool_sizes",run["pools"]=={"052":236,"053":237},run["pools"])
ck("synthetic_failed",run["synthetic_screen"]["synthetic_rank1_pass"] is False)
ck("actual_rank1_failed",run["actual_rank1_pass"] is False)
ck("rank2_not_formalized",run["rank2_worth_formalizing"] is False)
ck("advance_false",run["advance_to_dynamic_decision"] is False)
ck("diagnosis",run["diagnosis"]=="rank1_empirical_transport_fails_synthetic_screen",run["diagnosis"])
ck("zero_api",run["new_api_calls"]==0)
ck("no_reserved",run["reserved_used"] is False)
ck("rate_bounds",all(0<=float(r.get("accept_rate","0"))<=1 for r in syn if r.get("accept_rate","")!=""))

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
