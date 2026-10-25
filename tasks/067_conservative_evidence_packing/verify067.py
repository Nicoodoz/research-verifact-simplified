from pathlib import Path
import json,csv,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/067_conservative_evidence_packing"
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c,run067

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
checks=[]
def ck(n,x,d=""):checks.append({"name":n,"status":"PASS" if x else "FAIL","detail":str(d)})

fr=load(OUT/"freeze.json");an=load(OUT/"analysis_final.json")
for rel,h in fr["source_sha256"].items():
    ck("source_"+rel,sha(ROOT/rel)==h)
ck("head",subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==fr["git_head"])
ck("n236",len(c.lines(OUT/"cases_blind.jsonl"))==236)
ck("mapped227",sum(bool(x["mapped"]) for x in c.lines(OUT/"cases_blind.jsonl"))==227)
s1=c.lines(OUT/"stage1_jobs.jsonl");s2=c.lines(OUT/"stage2_jobs.jsonl")
ck("stage1_227",len(s1)==227)
ck("stage2_226",len(s2)==226)

# GT-blind audit payload.
for j in s1:
    body=j["body"];payload=json.loads(body["messages"][1]["content"])
    ck("audit_payload_"+j["id"],set(payload)=={"proposition","current_pack_ids","C48_candidates"})
    ck("audit_no_gt_"+j["id"],"GT" not in payload and "gold" not in body["messages"][1]["content"].lower())

# Final Judge is exact thinking-scoring shape and sees only proposition/reference.
for j in s2:
    body=j["body"];payload=json.loads(body["messages"][1]["content"])
    ck("judge_payload_"+j["id"],set(payload)=={"proposition","reference"})
    ck("judge_thinking_"+j["id"],body.get("enable_thinking") is True and body.get("reasoning_effort")=="high" and body.get("max_tokens")==8192)

attempts,term=run067.state()
formal={j["request_id"] for j in s1+s2}
fa=[a for a in attempts if a["request_id"] in formal]
sup=[a for a in attempts if a["request_id"] not in formal]
ck("formal_receipts453",len(fa)==453,len(fa))
ck("formal_http200",sum(a["http_status"]==200 for a in fa)==453)
ck("formal_cost",abs(sum(a["cost"] for a in fa)-11.839565999999987)<1e-9,sum(a["cost"] for a in fa))
ck("superseded252",len(sup)==252,len(sup))
ck("superseded_cost",abs(sum(a["cost"] for a in sup)-8.894004)<1e-9,sum(a["cost"] for a in sup))
ck("unique_request_ids",len({a["request_id"] for a in attempts})==len(attempts))

mp=c.lines(OUT/"pack_mapping.jsonl")
ck("mapping236",len(mp)==236)
ck("changed226",sum(bool(x["changed"]) for x in mp)==226)
ck("additions424",sum(len(x.get("added_pids",[])) for x in mp)==424)
ck("drops0",sum(len(x.get("dropped_pids",[])) for x in mp)==0)
ck("fallback_unmapped9",sum(x.get("fallback")=="unmapped_C48" for x in mp)==9)
ck("fallback_invalid1",sum(x.get("fallback")=="invalid_audit" for x in mp)==1)

# Formal results.
b=an["baseline"];n=an["new"]
ck("baseline198",b["correct"]==198)
ck("baseline_mcc",abs(b["MCC"]-0.5946094253723206)<1e-12)
ck("new199",n["correct"]==199)
ck("new_mcc",abs(n["MCC"]-0.5819131470419359)<1e-12)
ck("falseS_6_to_10",b["falseS"]==6 and n["falseS"]==10)
ck("paired14_13",an["paired"]["rescue"]==14 and an["paired"]["harm"]==13 and an["paired"]["net"]==1)
ck("raw_correct_equal",an["raw_baseline"]["correct"]==177 and an["raw_new"]["correct"]==177)
ck("raw_mcc_up",an["raw_new"]["MCC"]>an["raw_baseline"]["MCC"])
ck("raw_falseS_equal",an["raw_baseline"]["falseS"]==3 and an["raw_new"]["falseS"]==3)
ck("patient_6_6_12",an["patient"]["wins"]==6 and an["patient"]["losses"]==6 and an["patient"]["ties"]==12)
ck("advance_false",an["advance"] is False)
ck("formal_accounting_analysis",an["api_attempts"]==453 and an["http200"]==453 and abs(an["cost_cny"]-11.839565999999987)<1e-9)
ck("superseded_accounting_analysis",an["superseded_attempts"]==252 and abs(an["superseded_cost_cny"]-8.894004)<1e-9)
ck("reserved_false",an["reserved_used"] is False and fr["GT_not_in_API"] is True)

status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False,
     "formal_request_scope":"stage1_jobs.jsonl + stage2_jobs.jsonl",
     "superseded_v2_excluded":True}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":status,"n_checks":len(checks),"failed":[x for x in checks if x["status"]!="PASS"]},ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
