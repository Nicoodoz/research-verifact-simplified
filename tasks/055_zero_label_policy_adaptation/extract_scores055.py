"""Extract frozen N-S + T-S scores for 051/052/053. No API."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
LABS=("Supported","Not Supported","Not Addressed")
def write(name,rows,invalid):
 p=OUT/f"features_{name}.jsonl"
 with p.open("w",encoding="utf-8",newline="\n") as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
 (OUT/f"features_{name}_meta.json").write_text(json.dumps(dict(valid=len(rows),invalid=invalid),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(name,len(rows),"GT",{k:sum(r["GT"]==k for r in rows) for k in LABS},"invalid",len(invalid))
def get_scores(p,valid):
 return p.get("scores") if p.get("status") in valid and p.get("scores") is not None else None
def ex051():
 sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"));import run051,common051 as c
 cases={}
 for fn in ("screen_cases.jsonl","confirmation_cases_frozen.jsonl"):
  for x in c.lines(ROOT/"outputs/051_thinking_mode_validation"/fn):cases[x["id"]]=x
 _,term=run051.state();by={}
 for jf in ("screen_jobs.jsonl","confirmation_jobs.jsonl"):
  for j in c.lines(ROOT/"outputs/051_thinking_mode_validation"/jf):
   if j.get("condition") not in ("N-S","T-S") or j.get("kind")!="judge":continue
   by.setdefault(j["id"],{})[j["condition"]]=term[j["request_id"]]["parsed"]
 rows=[];bad=[]
 for pid,x in cases.items():
  ns=get_scores(by.get(pid,{}).get("N-S",{}),c.VALID);ts=get_scores(by.get(pid,{}).get("T-S",{}),c.VALID)
  if ns is None or ts is None:bad.append(pid);continue
  rows.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],ns_scores=ns,ts_scores=ts))
 return rows,bad
def ex052():
 for m in ["run051","common051"]:sys.modules.pop(m,None)
 sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"));import run052,common052 as c
 cases={x["id"]:x for x in c.lines(ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl")};_,term=run052.state()
 rows=[];bad=[]
 for pid,x in cases.items():
  h=c.stable("",pid)[:24];ns=get_scores(term["052_N_S_"+h]["parsed"],c.VALID);ts=get_scores(term["052_T_S_"+h]["parsed"],c.VALID)
  if ns is None or ts is None:bad.append(pid);continue
  rows.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],ns_scores=ns,ts_scores=ts))
 return rows,bad
def ex053():
 for m in ["run052","common052"]:sys.modules.pop(m,None)
 sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"));import run053,common053 as c
 cases={x["id"]:x for x in c.lines(ROOT/"outputs/053_thinking_prior_validation/evaluation_cases.jsonl")};_,term=run053.state()
 rows=[];bad=[]
 for pid,x in cases.items():
  h=c.stable("",pid)[:24];ns=get_scores(term["053_N_S_"+h]["parsed"],c.VALID);ts=get_scores(term["053_T_S_"+h]["parsed"],c.VALID)
  if ns is None or ts is None:bad.append(pid);continue
  rows.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],ns_scores=ns,ts_scores=ts))
 return rows,bad
def main():
 for name,fn in (("051",ex051),("052",ex052),("053",ex053)):
  r,b=fn();write(name,r,b)
if __name__=="__main__":main()
