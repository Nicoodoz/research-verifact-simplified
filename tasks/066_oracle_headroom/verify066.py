from pathlib import Path
import csv,json,hashlib,sys,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/066_oracle_headroom"
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c
import run066

def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
checks=[]
def ck(n,x,d=""):checks.append({"name":n,"status":"PASS" if x else "FAIL","detail":str(d)})

fr=load(OUT/"freeze.json");an=load(OUT/"analysis.json")
for rel,h in fr["source_sha256"].items():
    ck("source_"+rel,sha(ROOT/rel)==h)
ck("head",subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==fr["git_head"])
ck("error_cases39",len(c.lines(OUT/"error_cases.jsonl"))==39)
ck("c48_reconstructable36",sum(bool(x["c48_reconstructable"]) for x in c.lines(OUT/"error_cases.jsonl"))==36)
ck("stage1_jobs39",len(c.lines(OUT/"stage1_jobs.jsonl"))==39)
ck("stage2_jobs39",len(c.lines(OUT/"stage2_jobs.jsonl"))==39)
ck("stage3_jobs35",len(c.lines(OUT/"stage3_jobs.jsonl"))==35)

attempts,term=run066.state()
ck("attempts113",len(attempts)==113,len(attempts))
ck("http200_113",sum(x["http_status"]==200 for x in attempts)==113)
ck("cost_cap",sum(x["cost"] for x in attempts)<20,sum(x["cost"] for x in attempts))

for j in c.lines(OUT/"stage3_jobs.jsonl"):
    b=j["body"]
    ck("judge_thinking_"+j["id"],b.get("enable_thinking") is True and b.get("reasoning_effort")=="high" and b.get("max_tokens")==8192)
    payload=json.loads(b["messages"][1]["content"])
    ck("judge_payload_"+j["id"],set(payload)=={"proposition","reference"})
    ck("judge_no_gt_"+j["id"],"gold" not in b["messages"][1]["content"].lower() and "GT" not in payload)

ck("baseline201",an["baseline"]["correct"]==201)
ck("baseline_mcc",abs(an["baseline"]["MCC"]-0.5606605667086403)<1e-12)
ck("reasoning215",an["reasoning_oracle_observed"]["correct"]==215)
ck("reasoning_mcc",abs(an["reasoning_oracle_observed"]["MCC"]-0.7100934368058003)<1e-12)
ck("evidence212",an["evidence_oracle"]["correct"]==212)
ck("evidence_mcc",abs(an["evidence_oracle"]["MCC"]-0.6679633112323553)<1e-12)
ck("combined223",an["combined_oracle"]["correct"]==223)
ck("combined_mcc",abs(an["combined_oracle"]["MCC"]-0.7967707199969657)<1e-12)
ck("partition",an["error_partition"]=={"neither":17,"reasoning_only":11,"evidence_only":8,"both":3},an["error_partition"])
ck("evidence_fix11",an["evidence_fixed_errors"]==11)
ck("reasoning_fix14",an["reasoning_fixed_errors"]==14)
ck("combined_fix22",an["combined_fixed_errors"]==22)
ck("evidence_localization",an["evidence_localization"]=={"C48_selection_composition":10,"retrieval_or_mixed":1},an["evidence_localization"])
ck("reserved_false",an["reserved_used"] is False and fr["reserved_used"] is False)

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":status,"n_checks":len(checks),"failed":[x for x in checks if x["status"]!="PASS"]},ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
