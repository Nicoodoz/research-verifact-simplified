from pathlib import Path
import sys,json,copy
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"));import common053 as c53,run053
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"));import common052 as c52,run052
def lines(p):
 return [json.loads(s) for s in Path(p).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
def putj(p,rows):
 with Path(p).open("x",encoding="utf-8",newline="\n") as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def main():
 jobs=[];reuse=[];counts={}
 for pool,c,run in [("052",c52,run052),("053",c53,run053)]:
  dname=f"{pool}_"+("first_tier_validation" if pool=="052" else "thinking_prior_validation")
  mains=[j for j in lines(ROOT/"outputs"/dname/"main_jobs.jsonl") if j.get("condition")=="N-S"]
  assert len(mains)==240,(pool,len(mains))
  _,term=run.state()
  existing={}
  for qid,t in term.items():
   if qid.startswith(pool+"_Q_") and t["parsed"].get("status") in c53.VALID and t["parsed"].get("scores") is not None:
    existing[t["job"]["id"]]=t
  new=0;re=0
  for j in mains:
   body=copy.deepcopy(j["body"]);body["model"]=c53.MODEL_Q;body["enable_thinking"]=False;body["max_tokens"]=2048;body["temperature"]=0
   if j["id"] in existing:
    old=existing[j["id"]]["job"]["body"]
    assert c53.canonical(body)==c53.canonical(old),(pool,j["id"],"body mismatch")
    reuse.append(dict(pool=pool,id=j["id"],sid=j["sid"],existing_request_id=existing[j["id"]]["job"]["request_id"],body_sha256=c53.digest(body)));re+=1
   else:
    rid=f"055_QALL_{pool}_"+c53.stable("",j["id"])[:24]
    jobs.append(dict(request_id=rid,id=j["id"],sid=j["sid"],pool=pool,stage="qwen_full",condition="Qwen_full",scored=True,thinking=False,body=body));new+=1
  counts[pool]=dict(total=240,reuse=re,new=new)
 putj(OUT/"qwen_full_jobs.jsonl",jobs);putj(OUT/"qwen_full_reuse.jsonl",reuse)
 reservation=len(jobs)*.022
 freeze=dict(created_utc=c53.now(),counts=counts,new_calls=len(jobs),reused=len(reuse),reservation_cny=reservation,cap_cny=10.5,
  jobs_sha256=c53.sha(OUT/"qwen_full_jobs.jsonl"),reuse_sha256=c53.sha(OUT/"qwen_full_reuse.jsonl"),GT_used=False)
 c53.put(OUT/"qwen_full_freeze.json",freeze)
 print(json.dumps(freeze,indent=2))
if __name__=="__main__":main()
