from pathlib import Path
import sys,json,csv,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation";TASK=ROOT/"tasks/055_zero_label_policy_adaptation"
sys.path.insert(0,str(TASK));import run_qwen_full055
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"));import common053 as c53
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
def csvrows(p):
 with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 checks=[]
 def ck(name,v,d=None):
  checks.append(dict(name=name,ok=bool(v),detail=d))
  if not v:raise RuntimeError(name+" "+str(d))
 fr=json.loads((OUT/"qwen_full_freeze.json").read_text(encoding="utf-8"))
 ex=json.loads((OUT/"qwen_full_execution.json").read_text(encoding="utf-8"))
 attempts,term=run_qwen_full055.state()
 ck("qwen_new_count",fr["new_calls"]==429,fr["new_calls"]);ck("reuse_count",fr["reused"]==51,fr["reused"])
 ck("execution_planned",ex["planned"]==429,ex);ck("execution_completed",ex["completed_now"]==429,ex)
 ck("attempt_count",len(attempts)==429,len(attempts));ck("terminal_count",len(term)==429,len(term))
 ck("all_http200",all(x["http_status"]==200 for x in attempts))
 ck("unique_new_ids",len({x["request_id"] for x in attempts})==429)
 ck("cost",abs(ex["cumulative_cost_cny"]-7.451753999999996)<1e-9,ex["cumulative_cost_cny"])
 ck("under_cap",ex["cumulative_cost_cny"]<=fr["cap_cny"],(ex["cumulative_cost_cny"],fr["cap_cny"]))
 ck("no_live_lock",not (OUT/"qwen_full.live.lock").exists())
 for pool,n in (("052",236),("053",237)):
  q=lines(OUT/f"features_qwen_{pool}.jsonl");ck("qfeat_"+pool,len(q)==n,len(q))
  ck("q_scores_"+pool,all(set(x["qwen_scores"])=={"Supported","Not Supported","Not Addressed"} for x in q))
 safe=csvrows(OUT/"source_cv_qwen_nb_actual.csv")
 ck("safe_selector_two",len(safe)==2,len(safe))
 ck("safe_selector_fallback",all(x["used"]=="FrozenPriorG" for x in safe),[(x["target"],x["used"]) for x in safe])
 # Ensure final report records the extension rather than claiming all-zero API.
 report=(OUT/"report.md").read_text(encoding="utf-8")
 ck("report_qwen_cost","7.451754" in report)
 ck("amendment_exists",(TASK/"protocol_amendment_001.md").exists())
 ck("no_reserved_reference","reserved" not in "\n".join(str(x.get("condition","")) for x in attempts).lower())
 result=dict(status="PASS",checks=checks,new_API_calls=429,reused_Qwen=51,new_cost_cny=ex["cumulative_cost_cny"],
  hashes={str(p.relative_to(ROOT)):sha(p) for p in [
   TASK/"protocol.md",TASK/"protocol_amendment_001.md",TASK/"build_full_qwen055.py",TASK/"run_qwen_full055.py",
   OUT/"qwen_full_freeze.json",OUT/"qwen_full_execution.json",OUT/"qwen_full_raw_summary.csv",
   OUT/"source_cv_qwen_labelmodel_actual.csv",OUT/"source_cv_qwen_nb_actual.csv",OUT/"report.md"]})
 (OUT/"verification_001.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(dict(status="PASS",checks=len(checks),new_API_calls=429,cost=ex["cumulative_cost_cny"]),indent=2))
if __name__=="__main__":main()
