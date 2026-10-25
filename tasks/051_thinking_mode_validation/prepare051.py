"""Freeze 051 balanced screen/confirmation cohorts and four-condition preflight."""
from pathlib import Path
from collections import defaultdict,Counter
import pandas as pd,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c

SPLIT_SCREEN=['55750','89909','93788','29426','91315','98790','71743','16076']
SPLIT_CONFIRM=['55106','65399','67117','4954','97683','87982','45115','93147']
LABELS=("Supported","Not Supported","Not Addressed")

def round_robin(rows,patients,n,prefix):
    by=defaultdict(list)
    for r in rows:by[r["subject_id"]].append(r)
    for sid in by:by[sid].sort(key=lambda x:(c.stable(prefix+":case:",x["proposition_id"]),x["proposition_id"]))
    order=sorted(patients,key=lambda s:c.stable(prefix+":patient:",s))
    out=[];i=0
    while len(out)<n:
        moved=False
        for sid in order:
            if i<len(by[sid]) and len(out)<n:
                out.append(by[sid][i]);moved=True
        if not moved:break
        i+=1
    c.require(len(out)==n,"insufficient rows "+prefix)
    return out

def build_body(text,reference,scored,thinking):
    b=c.c020.body(text,reference,scored=scored)
    b["model"]=c.MODEL;b["stream"]=False
    if thinking:
        b["enable_thinking"]=True;b["reasoning_effort"]="high";b["max_tokens"]=8192
    else:
        b["enable_thinking"]=False;b.pop("reasoning_effort",None);b["max_tokens"]=2048
    return b

def main():
    if any(c.OUT.iterdir()):raise RuntimeError("051 output not empty")
    mats={x["proposition_id"]:x for x in c.lines(ROOT/"outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl")}
    df=pd.read_csv(ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv",dtype=str,keep_default_na=False)
    df=df[(df.proposition_type=="claim")&(df.invalid=="False")&(df.subject_id.isin(SPLIT_SCREEN+SPLIT_CONFIRM))].copy()
    df=df[df.proposition_id.isin(mats)].copy()
    rows=df[["proposition_id","subject_id","author_type","human_gt"]].to_dict("records")
    for r in rows:
        m=mats[r["proposition_id"]];r["text"]=m["text"];r["reference"]=m["reference"];r["role"]=m["role"]

    # Preflight claim chosen by hash from screen pool and excluded from all science samples.
    screen_pool=[r for r in rows if r["subject_id"] in SPLIT_SCREEN]
    pre=min(screen_pool,key=lambda r:(c.stable("051/preflight/v1:",r["proposition_id"]),r["proposition_id"]))
    scientific=[r for r in rows if r["proposition_id"]!=pre["proposition_id"]]

    screen=[];confirm=[]
    for lab in LABELS:
        screen.extend(round_robin([r for r in scientific if r["subject_id"] in SPLIT_SCREEN and r["human_gt"]==lab],SPLIT_SCREEN,16,"051/screen/"+lab))
        confirm.extend(round_robin([r for r in scientific if r["subject_id"] in SPLIT_CONFIRM and r["human_gt"]==lab],SPLIT_CONFIRM,32,"051/confirm/"+lab))
    c.require(len(screen)==48 and len(confirm)==96,"sample size")
    c.require(Counter(r["human_gt"] for r in screen)==Counter({"Supported":16,"Not Supported":16,"Not Addressed":16}),"screen balance")
    c.require(Counter(r["human_gt"] for r in confirm)==Counter({"Supported":32,"Not Supported":32,"Not Addressed":32}),"confirm balance")
    c.require(set(r["subject_id"] for r in screen)==set(SPLIT_SCREEN),"screen patient coverage")
    c.require(set(r["subject_id"] for r in confirm)==set(SPLIT_CONFIRM),"confirm patient coverage")

    c.jsonl(c.OUT/"screen_cases.jsonl",screen)
    c.jsonl(c.OUT/"confirmation_cases_frozen.jsonl",confirm)
    c.put(c.OUT/"preflight_case.json",pre)
    jobs=[]
    for arm,scored,thinking in (("N-S",True,False),("N-V",False,False),("T-S",True,True),("T-V",False,True)):
        jobs.append(dict(request_id="051_pre_"+arm.replace("-","_"),stage="preflight",arm=arm,scored=scored,thinking=thinking,
          id=pre["proposition_id"],body=build_body(pre["text"],pre["reference"],scored,thinking)))
    c.jsonl(c.OUT/"preflight_jobs.jsonl",jobs)
    c.put(c.OUT/"freeze.json",dict(created_utc=c.now(),screen_patients=SPLIT_SCREEN,confirmation_patients=SPLIT_CONFIRM,
      screen_n=48,confirmation_n=96,screen_label_counts=dict(Counter(r["human_gt"] for r in screen)),
      confirmation_label_counts=dict(Counter(r["human_gt"] for r in confirm)),preflight_id=pre["proposition_id"],
      GT_used_only_for_prespecified_balanced_sampling=True,GT_not_in_API=True,
      protocol_sha256=c.sha(ROOT/"tasks/051_thinking_mode_validation/protocol.md")))
    print("051 PREPARED",dict(preflight=pre["proposition_id"],screen=len(screen),confirm=len(confirm)),flush=True)

if __name__=="__main__":main()
