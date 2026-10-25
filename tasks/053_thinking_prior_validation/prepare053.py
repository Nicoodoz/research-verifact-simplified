from pathlib import Path
from collections import Counter,defaultdict
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c

def load_pool(dev):
    pool=defaultdict(dict)
    p=ROOT/"outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl"
    for x in c.lines(p):
        sid=str(x["subject_id"])
        if sid in dev:pool[sid][x["proposition_id"]]=dict(id=x["proposition_id"],sid=sid,author=x["author_type"],claim=x["text"],reference=x["reference"],source="019_frozen_C48")
    p=ROOT/"outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl"
    meta={x["proposition_id"]:x for x in csv.DictReader((ROOT/"outputs/024_lambda2_transfer_validation/preparation_001/cohort.csv").open(encoding="utf-8-sig"))}
    for j in c.lines(p):
        if j["model_key"]!="deepseek" or j["arm"]!="S":continue
        pid=j["proposition_id"];sid=str(meta[pid]["subject_id"])
        if sid not in dev:continue
        q=json.loads(j["body"]["messages"][-1]["content"])
        pool[sid][pid]=dict(id=pid,sid=sid,author=meta[pid]["author_type"],claim=q["proposition"],reference=q["reference"],source="024_frozen_C48")
    p=ROOT/"outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl"
    for x in c.lines(p):
        sid=str(x["subject_id"])
        if sid in dev:pool[sid][x["proposition_id"]]=dict(id=x["proposition_id"],sid=sid,author=x["author_type"],claim=x["text"],reference=x["reference"],source="031_frozen_C48")
    return pool

def main():
    c.require(not any(c.OUT.iterdir()),"053 output not empty")
    pg=c.read(ROOT/"outputs/003_error_analysis/patient_groups.json");dev=set(map(str,pg["groups"]["development"]))
    used=set()
    for f in [ROOT/"outputs/051_thinking_mode_validation/screen_cases.jsonl",ROOT/"outputs/051_thinking_mode_validation/confirmation_cases_frozen.jsonl",ROOT/"outputs/052_first_tier_validation/evaluation_cases.jsonl"]:
        for x in c.lines(f):used.add(x.get("id") or x.get("proposition_id"))
    pool=load_pool(dev);c.require(set(pool)==dev,"pool coverage")
    selected=[]
    for sid in sorted(dev,key=lambda s:c.stable("053/patient/v1:",s)):
        avail=[x for pid,x in pool[sid].items() if pid not in used]
        avail.sort(key=lambda x:(c.stable("053/sample/v1:",x["id"]),x["id"]))
        c.require(len(avail)>=6,"insufficient "+sid)
        selected+=avail[:6]
    c.require(len(selected)==240 and len({x["id"] for x in selected})==240,"sample size")
    c.jsonl(c.OUT/"sample_blind.jsonl",selected)
    # Frozen prior source: all usable 031 C48-material claims from the 16 task051 patients.
    p051=set(map(str,c.read(ROOT/"outputs/051_thinking_mode_validation/freeze.json")["patient_pool"]))
    mat031=c.lines(ROOT/"outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl")
    ids031={x["proposition_id"] for x in mat031 if str(x["subject_id"]) in p051}
    cm={r["proposition_id"]:r for r in csv.DictReader((ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv").open(encoding="utf-8-sig"))}
    mother=[cm[i] for i in ids031 if i in cm and cm[i]["invalid"]=="False" and cm[i]["human_gt"] in c.LABELS]
    ref=Counter(r["human_gt"] for r in mother)
    c.require(dict(ref)=={"Supported":1108,"Not Addressed":170,"Not Supported":100},"prior count drift "+str(ref))
    cal=c.read(ROOT/"outputs/052_first_tier_validation/calibration_models.json")
    freeze=dict(created_utc=c.now(),n=240,per_patient=6,patients=sorted(dev),
      excludes_claims_from=["051 screen/confirmation","052 evaluation"],selection_reads_GT=False,
      source_counts=dict(Counter(x["source"] for x in selected)),reference_prior_counts=dict(ref),
      calibration_counts={k:v["GT_counts"] for k,v in cal["training"].items()},
      calibration_theta={cond:{kind:cal["models"][cond][kind]["theta"] for kind in ("G","M")} for cond in ("N-S","T-S")},
      sources={"019":c.sha(ROOT/"outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl"),
               "024":c.sha(ROOT/"outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl"),
               "031":c.sha(ROOT/"outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl"),
               "cohort_master":c.sha(ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv"),
               "calibration":c.sha(ROOT/"outputs/052_first_tier_validation/calibration_models.json"),
               "protocol":c.sha(ROOT/"tasks/053_thinking_prior_validation/protocol.md")},
      cap_cny=c.CAP)
    c.put(c.OUT/"freeze.json",freeze)
    print("053 FROZEN",len(selected),"prior",dict(ref),"sources",freeze["source_counts"])
if __name__=="__main__":main()
