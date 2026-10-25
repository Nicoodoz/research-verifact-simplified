"""Freeze 052 24-patient, 240-claim GT-blind sample from existing C48 materials."""
from pathlib import Path
from collections import Counter
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"))
import common052 as c

P019=ROOT/"outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl"
P024=ROOT/"outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl"
P031=ROOT/"outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl"
SPLIT051=ROOT/"outputs/051_thinking_mode_validation/freeze.json"
GROUPS=ROOT/"outputs/003_error_analysis/patient_groups.json"

def load_materials():
    mats={}
    for x in c.lines(P019):
        mats[x["proposition_id"]]=dict(id=x["proposition_id"],sid=str(x["subject_id"]),author=x["author_type"],
          claim=x["text"],reference=x["reference"],source="019_frozen_C48")
    for j in c.lines(P024):
        if j["model_key"]!="deepseek" or j["arm"]!="S":continue
        payload=json.loads(j["body"]["messages"][-1]["content"])
        pid=j["proposition_id"]
        # cohort supplies sid/author without physician GT.
        mats[pid]=dict(id=pid,claim=payload["proposition"],reference=payload["reference"],source="024_frozen_C48")
    cohort=list(csv.DictReader((ROOT/"outputs/024_lambda2_transfer_validation/preparation_001/cohort.csv").open(encoding="utf-8-sig")))
    meta={r["proposition_id"]:r for r in cohort}
    for pid in list(mats):
        if mats[pid]["source"]=="024_frozen_C48":
            mats[pid]["sid"]=str(meta[pid]["subject_id"]);mats[pid]["author"]=meta[pid]["author_type"]
    for x in c.lines(P031):
        mats[x["proposition_id"]]=dict(id=x["proposition_id"],sid=str(x["subject_id"]),author=x["author_type"],
          claim=x["text"],reference=x["reference"],source="031_frozen_C48")
    return mats

def main():
    if any(c.OUT.iterdir()):raise RuntimeError("052 output not empty")
    dev=set(map(str,c.read(GROUPS)["groups"]["development"]))
    used051=set(map(str,c.read(SPLIT051)["patient_pool"]))
    evalpts=sorted(dev-used051,key=lambda s:c.stable("052/patient/v1:",s))
    c.require(len(dev)==40 and len(used051)==16 and len(evalpts)==24,"patient partition mismatch")
    mats=load_materials()
    by={sid:[] for sid in evalpts}
    for x in mats.values():
        if x.get("sid") in by:by[x["sid"]].append(x)
    selected=[]
    for sid in evalpts:
        pool=sorted(by[sid],key=lambda x:(c.stable("052/sample/v1:",x["id"]),x["id"]))
        c.require(len(pool)>=10,f"insufficient frozen C48 for {sid}: {len(pool)}")
        selected.extend(pool[:10])
    c.require(len(selected)==240 and all(sum(x["sid"]==sid for x in selected)==10 for sid in evalpts),"sample quota")
    # No GT field exists in selected.
    c.require(all("GT" not in x and "human_gt" not in x for x in selected),"GT leaked into blind sample")
    c.jsonl(c.OUT/"cases_blind.jsonl",selected)
    c.put(c.OUT/"freeze.json",dict(created_utc=c.now(),evaluation_patients=evalpts,n=240,per_patient=10,
      selection="first10 ascending SHA256('052/sample/v1:'+proposition_id) within each fixed evaluation patient",
      selection_reads_GT=False,GT_not_in_API=True,source_counts=dict(Counter(x["source"] for x in selected)),
      sources={str(p.relative_to(ROOT)):c.sha(p) for p in (P019,P024,P031,SPLIT051,GROUPS)},
      protocol_sha256=c.sha(ROOT/"tasks/052_first_tier_validation/protocol.md"),cap_cny=c.CAP))
    print("052 SAMPLE FROZEN",len(selected),evalpts,dict(Counter(x["source"] for x in selected)),flush=True)
if __name__=="__main__":main()
