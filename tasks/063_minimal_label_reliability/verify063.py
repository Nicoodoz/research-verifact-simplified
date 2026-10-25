from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/063_minimal_label_reliability"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

f1=loadj(OUT/"freeze.json")
r1=loadj(OUT/"run_summary.json")
f2=loadj(OUT/"soft_freeze.json")
r2=loadj(OUT/"soft_run_summary.json")
checks=[]
def ck(name,ok,detail=""):
    checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":str(detail)})
ck("primary_code_hash",sha(ROOT/"tasks/063_minimal_label_reliability/run063.py")==f1["code_sha256"])
for key,meta in f1["inputs"].items():
    ck("primary_input_"+key,sha(ROOT/meta["path"])==meta["sha256"])
ck("soft_code_hash",sha(ROOT/"tasks/063_minimal_label_reliability/run063_soft.py")==f2["code_sha256"])
for key,meta in f2["inputs"].items():
    ck("soft_input_"+key,sha(ROOT/meta["path"])==meta["sha256"])

pr=rows(OUT/"replicate_results.csv")
ps=rows(OUT/"summary.csv")
sr=rows(OUT/"soft_replicate_results.csv")
ss=rows(OUT/"soft_summary.csv")
ck("primary_replicate_rows",len(pr)==1202,len(pr))
ck("primary_summary_rows",len(ps)==26,len(ps))
ck("soft_replicate_rows",len(sr)==1202,len(sr))
ck("soft_summary_rows",len(ss)==26,len(ss))
ck("primary_zero_api",r1["new_api_calls"]==0)
ck("primary_no_reserved",r1["reserved_used"] is False)
ck("soft_zero_api",r2["new_api_calls"]==0)
ck("soft_no_reserved",r2["reserved_used"] is False)
ck("primary_not_closed",r1["missing_link_closed"] is False,r1["diagnosis"])
ck("soft_not_closed",r2["missing_link_closed"] is False,r2["diagnosis"])
ck("primary_oracle_no_pass",r1["minimum_passing_budget"]["oracle_balanced"] is None)
ck("soft_oracle_no_pass",r2["minimum_passing_budget"]["oracle_balanced"] is None)
ck("same_head",f1["git_head"]==f2["git_head"],(f1["git_head"],f2["git_head"]))
ck("pool_sizes",r1["pools"]=={"052":236,"053":237} and r2["pools"]=={"052":236,"053":237})

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
