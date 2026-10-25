from pathlib import Path
from collections import Counter
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c

SOURCES={
 "031":dict(candidates=ROOT/"outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",corpus=ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"),
 "020":dict(candidates=ROOT/"outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl",corpus=ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl"),
 "009":dict(candidates=ROOT/"outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl",corpus=ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl")}
ORDER=("031","020","009")
def load_candidates(path):
 out={}
 for x in c.lines(path):
  pid=str(x.get("proposition_id") or x.get("id") or "");ids=(x.get("candidate_ids") or {}).get("C48") or x.get("C48")
  if pid and isinstance(ids,list) and ids:out[pid]=ids
 return out
def match_baseline(blocks,c48_ids,corpus):
 used=set();mapped=[]
 for b in blocks:
  found=None
  for pid in c48_ids:
   if pid in used or pid not in corpus:continue
   t=c.norm(corpus[pid].get("text",""))
   if b==t or b in t or t in b:found=pid;break
  if found is None:return None
  used.add(found);mapped.append(found)
 return mapped

def main():
 for n in ("cases_blind_v2.jsonl","stage1v2_jobs.jsonl","freeze_v2.json"):
  if (c.OUT/n).exists():raise RuntimeError("v2 output exists: "+n)
 feats=[json.loads(x) for x in (ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
 cases={x["id"]:x for x in c.lines(ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl")}
 cm={n:load_candidates(v["candidates"]) for n,v in SOURCES.items()}
 corp={n:{x["passage_id"]:x for x in c.lines(v["corpus"])} for n,v in SOURCES.items()}
 rows=[];jobs=[]
 for f in feats:
  pid=f["id"];case=cases[pid];blocks=c.reference_blocks(case["reference"]);c.require(blocks,"empty parsed baseline blocks "+pid)
  best=None
  for name in ORDER:
   if pid not in cm[name]:continue
   mapped=match_baseline(blocks,cm[name][pid],corp[name])
   if mapped is None:continue
   score=(len(mapped),-ORDER.index(name))
   if best is None or score>best[0]:best=(score,name,mapped)
  if best is None:
   rows.append(dict(id=pid,sid=str(f["sid"]),author=f["author"],claim=case["claim"],baseline_reference=case["reference"],mapped=False,source=None,baseline_pids=[],c48_pids=[]))
   continue
  _,source,baseline_pids=best;c.require(len(baseline_pids)==len(blocks) and len(baseline_pids)>0,"baseline mapping incomplete "+pid)

  c48=cm[source][pid];lookup={f"C{i+1:02d}":z for i,z in enumerate(c48)};reverse={v:k for k,v in lookup.items()}
  baseline_short=[reverse[z] for z in baseline_pids]
  c.require(baseline_short and len(baseline_short)==len(blocks),"empty baseline_short "+pid)
  rendered=[c.candidate_line(s,corp[source][z]) for s,z in lookup.items() if z in corp[source]]
  c.require(len(rendered)==len(c48),"missing corpus passage "+pid)
  rows.append(dict(id=pid,sid=str(f["sid"]),author=f["author"],claim=case["claim"],baseline_reference=case["reference"],mapped=True,source=source,baseline_pids=baseline_pids,c48_pids=c48,candidate_short_to_pid=lookup,baseline_short_ids=baseline_short))
  h=c.stable("",pid)[:24]
  jobs.append(dict(request_id="067v2_audit_"+h,stage="stage1v2",kind="audit",model_key="qwen",id=pid,body=c.audit_body(case["claim"],baseline_short,rendered),candidate_lookup=lookup,baseline_short_ids=baseline_short))
 c.require(len(rows)==236,"unexpected v2 row count");print("V2 COUNTS",len(rows),len(jobs),Counter(x["source"] for x in rows if x["mapped"]),flush=True)
 c.require(all((not x["mapped"]) or x["baseline_pids"] for x in rows),"mapped row missing baseline pids")
 c.jsonl(c.OUT/"cases_blind_v2.jsonl",rows);c.jsonl(c.OUT/"stage1v2_jobs.jsonl",sorted(jobs,key=lambda x:x["request_id"]))
 deps=[ROOT/"tasks/067_conservative_evidence_packing/protocol.md",ROOT/"tasks/067_conservative_evidence_packing/protocol_amendment_001.md",ROOT/"tasks/067_conservative_evidence_packing/common067.py",Path(__file__)]
 mapped_n=sum(x["mapped"] for x in rows);fr=dict(created_utc=c.now(),git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),n=236,mapped=mapped_n,unmapped=236-mapped_n,stage1v2_jobs=len(jobs),baseline_blocks=sum(len(x["baseline_pids"]) for x in rows),min_baseline_blocks=min(len(x["baseline_pids"]) for x in rows if x["mapped"]),max_baseline_blocks=max(len(x["baseline_pids"]) for x in rows if x["mapped"]),source_counts=dict(Counter(x["source"] for x in rows if x["mapped"])),v1_status="implementation_invalid_superseded",prior_cost_cny=sum(a["cost"] for a in __import__("run067").state()[0]),cap_cny=c.CAP,source_sha256={str(q.relative_to(ROOT)):c.sha(q) for q in deps})
 c.put(c.OUT/"freeze_v2.json",fr);print("067 V2 PREPARED",fr,flush=True)
if __name__=="__main__":main()
