from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/059_joint_prior_judge_drift"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

fr=loadj(OUT/"freeze.json")
run=loadj(OUT/"run_summary.json")
actual=rows(OUT/"actual_unlabeled.csv")
syn=rows(OUT/"synthetic_summary.csv")
ev=rows(OUT/"actual_evaluation.csv")
checks=[]
def ck(name,ok,detail=""):
    checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})

ck("code_hash",sha(ROOT/"tasks/059_joint_prior_judge_drift/run059.py")==fr["code_sha256"])
for key,meta in fr["inputs"].items():
    ck("input_hash_"+key,sha(ROOT/meta["path"])==meta["sha256"])
ck("blind_actual_hash",sha(OUT/"actual_unlabeled.csv")==run["actual_unlabeled_sha256_before_gt_evaluation"])
ck("actual_rows",len(actual)==2,len(actual))
ck("synthetic_rows",len(syn)==240,len(syn))
ck("actual_eval_rows",len(ev)==2,len(ev))
ck("pool_sizes",run["pools"]=={"052":236,"053":237},run["pools"])
ck("synthetic_pass",run["synthetic_recovery_pass"] is True)
ck("actual_r2_fail",run["actual_common_shift_r2_pass"] is False)
ck("advance_false",run["advance_to_060"] is False)
ck("zero_api",run["new_api_calls"]==0)
ck("no_reserved",run["reserved_used"] is False)
ck("metric_bounds",all(0<=float(r["prior_l1_mean"])<=2 and 0<=float(r["theta_mae_mean"]) for r in syn))

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(
    json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
