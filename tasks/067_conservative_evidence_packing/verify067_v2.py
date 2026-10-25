from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(r"D:\Research-VeriFact")
OUT=ROOT/"outputs/067_conservative_evidence_packing"
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[];warnings=[]
def ck(n,x,d=""): checks.append({"name":n,"status":"PASS" if x else "FAIL","detail":str(d)})
def warn(n,d=""): warnings.append({"name":n,"detail":str(d)})
fr=loadj(OUT/"freeze.json");an=loadj(OUT/"analysis_final.json")
for rel,h in fr["source_sha256"].items():
    actual=sha(ROOT/rel)
    if rel.replace("\\","/")=="tasks/067_conservative_evidence_packing/common067.py":
        if actual!=h: warn("common067_postfreeze_hash_mismatch",{"frozen":h,"current":actual})
        else: ck("source_"+rel,True)
    else: ck("source_"+rel,actual==h,actual)
ck("head",subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==fr["git_head"])
cases={x["id"]:x for x in lines(OUT/"cases_blind.jsonl")}
packs={x["id"]:x for x in lines(OUT/"pack_mapping.jsonl")}
s1=lines(OUT/"stage1_jobs.jsonl");s2=lines(OUT/"stage2_jobs.jsonl")
ck("cases236",len(cases)==236);ck("mapped227",sum(bool(x["mapped"]) for x in cases.values())==227)
ck("stage1_227",len(s1)==227);ck("stage2_226",len(s2)==226)
attempt_by_rid={}
for p in (OUT/"attempts").glob("*/request.json"):
    rq=loadj(p);rid=rq["job"]["request_id"];rp=p.parent/"receipt.json"
    if rp.exists():attempt_by_rid[rid]=(rq,loadj(rp)["transport"])
formal_ids={j["request_id"] for j in s1+s2}
ck("formal_all_receipts",all(r in attempt_by_rid for r in formal_ids))
ck("formal_453",len(formal_ids)==453)
ck("formal_http200",sum(attempt_by_rid[r][1].get("http_status")==200 for r in formal_ids)==453)
for j in s1:
    payload=json.loads(j["body"]["messages"][1]["content"])
    ck("audit_payload_"+j["id"],set(payload)=={"proposition","current_pack_ids","C48_candidates"})
    ck("audit_no_label_fields_"+j["id"],not any(k.lower() in {"gt","gold","gold_label","label","verdict"} for k in payload))
audit_obj={}
for j in s1:
    tr=attempt_by_rid[j["request_id"]][1]
    outer=json.loads(tr["body_text"])
    txt=outer["choices"][0]["message"]["content"].strip()
    try:
        o=json.loads(txt)
    except Exception:
        try:
            lo,hi=txt.find("{"),txt.rfind("}")
            o=json.loads(txt[lo:hi+1])
        except Exception:
            o=None
    audit_obj[j["id"]]=(j,o)
for pid,mp in packs.items():
    case=cases[pid]
    if not case["mapped"]:
        ck("unmapped_unchanged_"+pid,not mp["changed"] and mp["final_reference"]==case["baseline_reference"])
        continue
    j,o=audit_obj[pid]
    if mp.get("fallback")=="invalid_audit":
        ck("invalid_audit_unchanged_"+pid,o is None and not mp["changed"] and mp["final_reference"]==case["baseline_reference"])
        continue
    ck("audit_parse_"+pid,o is not None)
    lookup=j["candidate_lookup"];rec=set()
    for z in o.get("additions",[]):
        cid=str(z.get("id"))
        if cid in lookup:rec.add(lookup[cid])
    adds=set(mp.get("added_pids",[]))
    ck("adds_recommended_"+pid,adds.issubset(rec),(adds,rec))
    ck("adds_in_c48_"+pid,adds.issubset(set(case["c48_pids"])))
    ck("adds_not_baseline_"+pid,adds.isdisjoint(set(case["baseline_pids"])))
    ck("max2_adds_"+pid,len(adds)<=2);ck("no_drops_"+pid,len(mp.get("dropped_pids",[]))==0)
    if mp["changed"]:ck("judge_id_present_"+pid,bool(mp.get("judge_request_id")))
s2_by_id={j["id"]:j for j in s2}
for pid,mp in packs.items():
    if not mp["changed"]:continue
    j=s2_by_id[pid];payload=json.loads(j["body"]["messages"][1]["content"])
    ck("judge_payload_"+pid,set(payload)=={"proposition","reference"})
    ck("judge_claim_"+pid,payload["proposition"]==cases[pid]["claim"])
    ck("judge_reference_exact_"+pid,payload["reference"]==mp["final_reference"])
    ck("judge_thinking_"+pid,j["body"].get("enable_thinking") is True and j["body"].get("reasoning_effort")=="high" and j["body"].get("max_tokens")==8192)
sf=loadj(OUT/"stage2_freeze.json")
ck("build_stage2_hash",sha(ROOT/"tasks/067_conservative_evidence_packing/build_stage2_067.py")==sf["code_sha256"])
prices={"qwen":(3,12),"deepseek":(3,9)}
def amount(rid):
    rq,tr=attempt_by_rid[rid]
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=prices[rq["job"]["model_key"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return float(rq["reservation_cny"])
formal_cost=sum(amount(r) for r in formal_ids);sup_ids=set(attempt_by_rid)-formal_ids;sup_cost=sum(amount(r) for r in sup_ids)
ck("formal_cost",abs(formal_cost-11.839565999999987)<1e-9,formal_cost)
ck("superseded252",len(sup_ids)==252,len(sup_ids));ck("superseded_cost",abs(sup_cost-8.894004)<1e-9,sup_cost)
b=an["baseline"];n=an["new"]
ck("baseline198",b["correct"]==198);ck("baseline_mcc",abs(b["MCC"]-0.5946094253723206)<1e-12)
ck("new199",n["correct"]==199);ck("new_mcc",abs(n["MCC"]-0.5819131470419359)<1e-12)
ck("falseS",b["falseS"]==6 and n["falseS"]==10)
ck("paired",an["paired"]["rescue"]==14 and an["paired"]["harm"]==13 and an["paired"]["net"]==1)
ck("raw",an["raw_baseline"]["correct"]==177 and an["raw_new"]["correct"]==177 and an["raw_new"]["MCC"]>an["raw_baseline"]["MCC"])
ck("patient",an["patient"]["wins"]==6 and an["patient"]["losses"]==6 and an["patient"]["ties"]==12)
ck("advance_false",an["advance"] is False);ck("formal_analysis_account",an["api_attempts"]==453 and abs(an["cost_cny"]-formal_cost)<1e-9)
ck("reserved_false",an["reserved_used"] is False and fr["selection_uses_GT"] is False and fr["GT_not_in_API"] is True)
status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"warnings":warnings,"checks":checks,"independent_audit":False,
"verification_001_status":"superseded_false_positive_checks","formal_scope":"stage1 + stage2 only","superseded_v2_excluded":True}
(OUT/"verification_002.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":status,"n_checks":len(checks),"warnings":warnings,"failed":[x for x in checks if x["status"]!="PASS"]},ensure_ascii=False,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
