from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/065_verification_evidence_construction"
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding="utf-8-sig"))
lines=lambda p:[json.loads(x) for x in Path(p).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
freeze=read(OUT/"freeze.json");a=read(OUT/"analysis.json");s3=read(OUT/"stage3_freeze.json")
checks=[]
def ck(n,x,d=""):checks.append({"name":n,"status":"PASS" if x else "FAIL","detail":str(d)})
for rel,h in freeze["source_sha256"].items():ck("source_"+rel,sha(ROOT/rel)==h)
cases=lines(OUT/"screen_cases_blind.jsonl");j1=lines(OUT/"stage1_jobs.jsonl");j2=lines(OUT/"stage2_jobs.jsonl");j3=lines(OUT/"stage3_jobs.jsonl")
ck("screen24",len(cases)==24);ck("blind_no_GT",all("GT" not in x for x in cases))
ck("types",sum(x["type"]=="boundary" for x in cases)==8 and sum(x["type"]=="stable" for x in cases)==16)
ck("patients8",len({x["sid"] for x in cases})==8 and all(sum(y["sid"]==x for y in cases)==3 for x in {z["sid"] for z in cases}))
ck("stage1_48",len(j1)==48);ck("stage2_48",len(j2)==48);ck("stage3_46",len(j3)==46)
ck("composer_missing2",s3["composer_invalid"]==2 and s3["B_valid"]==23 and s3["C_valid"]==23)
ck("common23",a["common_n"]==23);ck("http200",a["api_attempts"]==142 and a["http200"]==142)
ck("cost_cap",a["cost_cny"]<=15,a["cost_cny"])
ck("paired_B",a["B_vs_A"]["rescue"]==3 and a["B_vs_A"]["harm"]==2 and a["B_vs_A"]["net"]==1)
ck("paired_C",a["C_vs_A"]["rescue"]==2 and a["C_vs_A"]["harm"]==1 and a["C_vs_A"]["net"]==1)
ck("retrieval_no_increment",a["C_vs_B"]["rescue"]==1 and a["C_vs_B"]["harm"]==1)
ck("decision",not a["decision"]["B_pass"] and not a["decision"]["C_pass"] and not a["decision"]["C_incremental_retrieval"])
status="PASS" if all(x["status"]=="PASS" for x in checks) else "FAIL"
out={"status":status,"n_checks":len(checks),"checks":checks,"independent_audit":False}
(OUT/"verification_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if status=="PASS" else 1)
