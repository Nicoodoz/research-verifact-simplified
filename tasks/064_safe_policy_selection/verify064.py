from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/064_safe_policy_selection"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def loadj(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

f0=loadj(OUT/"freeze.json")
r0=loadj(OUT/"run_summary.json")
f2=loadj(OUT/"future_v2_freeze.json")
r2=loadj(OUT/"future_v2_run_summary.json")
checks=[]

def ck(name,ok,detail=""):
    checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})

ck("main_code_hash",sha(ROOT/"tasks/064_safe_policy_selection/run064.py")==f0["code_sha256"])
for k,m in f0["inputs"].items():
    ck("main_input_"+k,sha(ROOT/m["path"])==m["sha256"])
ck("main_blind_hash",sha(OUT/"actual_unlabeled.csv")==r0["actual_unlabeled_sha256_before_gt_evaluation"])
ck("main_rows",len(rows(OUT/"replicate_results.csv"))==802,len(rows(OUT/"replicate_results.csv")))
ck("main_summary_rows",len(rows(OUT/"summary.csv"))==18,len(rows(OUT/"summary.csv")))
ck("oracle_rows",len(rows(OUT/"oracle_policy.csv"))==12,len(rows(OUT/"oracle_policy.csv")))
ck("oracle_policies",r0["oracle_policy"]=={"052->053":"R90","053->052":"BASE"},r0["oracle_policy"])
ck("main_not_closed",r0["missing_link_closed"] is False)
ck("main_zero_api",r0["new_api_calls"]==0)
ck("main_no_reserved",r0["reserved_used"] is False)

ck("v2_code_hash",sha(ROOT/"tasks/064_safe_policy_selection/run064_future_v2.py")==f2["code_sha256"])
for k,m in f2["inputs"].items():
    ck("v2_input_"+k,sha(ROOT/m["path"])==m["sha256"])
ck("v2_rows",len(rows(OUT/"future_v2_replicate_results.csv"))==900,len(rows(OUT/"future_v2_replicate_results.csv")))
ck("v2_summary_rows",len(rows(OUT/"future_v2_summary.csv"))==18,len(rows(OUT/"future_v2_summary.csv")))
ck("v2_oracle_policies",r2["oracle_policy"]=={"052->053":"R90","053->052":"BASE"},r2["oracle_policy"])
ck("v2_not_closed",r2["missing_link_closed"] is False)
ck("v2_zero_api",r2["new_api_calls"]==0)
ck("v2_no_reserved",r2["reserved_used"] is False)
ck("same_head",f0["git_head"]==f2["git_head"],(f0["git_head"],f2["git_head"]))

sv=rows(OUT/"future_v2_summary.csv")
def pick(src,tgt,strategy,budget):
    return next(r for r in sv if r["source"]==src and r["target"]==tgt
                and r["strategy"]==strategy and int(r["budget"])==budget)

a=pick("052","053","active_policy",10)
b=pick("053","052","active_policy",20)
ck("forward_active10_safe",float(a["unsafe_switch_rate"])==0.0,a["unsafe_switch_rate"])
ck("forward_active10_select58",abs(float(a["beneficial_nonbase_select_rate"])-.58)<1e-12,a["beneficial_nonbase_select_rate"])
ck("reverse_active20_fallback90",abs(float(b["base_fallback_rate"])-.90)<1e-12,b["base_fallback_rate"])
ck("reverse_active20_unsafe10",abs(float(b["unsafe_switch_rate"])-.10)<1e-12,b["unsafe_switch_rate"])

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={
    "status":status,
    "n_checks":len(checks),
    "checks":checks,
    "independent_audit":False,
    "future_v1_status":"superseded_by_amendment_002_exposure_fix",
}
(OUT/"verification_001.json").write_text(
    json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
