from pathlib import Path
from collections import Counter
import sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c
import run067

CORPUS={
 "031":ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
 "020":ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
 "009":ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl",
}

def choose_additions(adds):
    ordered=sorted(enumerate(adds),key=lambda z:(int(z[1]["priority"]),z[0]))
    out=[];seen=set()
    for _,a in ordered:
        key=c.norm(a.get("requirement","")) or ("id:"+a["id"])
        if key in seen:continue
        seen.add(key);out.append(a)
        if len(out)>=2:break
    return out

def main():
    if (c.OUT/"stage2v2_jobs.jsonl").exists():raise RuntimeError("stage2 already built")
    rows=c.lines(c.OUT/"cases_blind_v2.jsonl")
    attempts,term=run067.state()
    corp={n:{x["passage_id"]:x for x in c.lines(p)} for n,p in CORPUS.items()}
    mapping=[];jobs=[]

    for x in rows:
        pid=x["id"];baseline=x["baseline_reference"]
        if not x["mapped"]:
            mapping.append(dict(id=pid,changed=False,fallback="unmapped_C48",audit_status="not_run",
                                final_reference=baseline,added_pids=[],dropped_pids=[],addition_roles=[],
                                baseline_body_chars=None,final_body_chars=None,judge_request_id=None))
            continue
        h=c.stable("",pid)[:24];rid="067v2_audit_"+h
        if rid not in term or term[rid]["parsed"].get("status")!="valid":
            mapping.append(dict(id=pid,changed=False,fallback="invalid_audit",audit_status=term.get(rid,{}).get("parsed",{}).get("status","missing"),
                                final_reference=baseline,added_pids=[],dropped_pids=[],addition_roles=[],
                                baseline_body_chars=None,final_body_chars=None,judge_request_id=None))
            continue
        au=term[rid]["parsed"];lookup=x["candidate_short_to_pid"];reverse={v:k for k,v in lookup.items()}
        corpus=corp[x["source"]];base=list(x["baseline_pids"]);current=list(base)
        must={lookup[s] for s in au["must_keep_baseline"] if s in lookup}
        safe=[lookup[s] for s in au["safe_drop_baseline"] if s in lookup]
        protected=set(must)
        for z in base:
            if z in corpus and c.text_is_hard_protected(corpus[z].get("text","")):protected.add(z)
        added=[];dropped=[];roles=[]

        for a in choose_additions(au["additions"]):
            addpid=lookup[a["id"]]
            if addpid in current or addpid not in corpus:continue
            trial=current+[addpid]
            trial_drops=[]
            if c.pack_size(trial,corpus)>8000:
                for z in safe:
                    if z not in trial or z not in base or z in protected or z in trial_drops:continue
                    trial.remove(z);trial_drops.append(z)
                    if c.pack_size(trial,corpus)<=8000:break
                    if len(trial_drops)>=2:break
            if c.pack_size(trial,corpus)<=8000:
                current=trial;added.append(addpid);roles.append(a["role"]);dropped.extend(trial_drops)
        changed=bool(added)
        if changed:
            final_ref=c.build_reference_from_ids(current,corpus,baseline)
            c.require(c.pack_size(current,corpus)<=8000,"pack cap violation")
            c.require(all(z in safe for z in dropped),"non-safe drop")
            c.require(all(z not in protected for z in dropped),"protected drop")
            jrid="067v2_judge_"+h
            jobs.append(dict(request_id=jrid,stage="stage2v2",kind="judge",model_key="deepseek",
                             id=pid,body=c.score_body(x["claim"],final_ref)))
            fallback=None
        else:
            final_ref=baseline;jrid=None;fallback="no_safe_addition"
        mapping.append(dict(
            id=pid,changed=changed,fallback=fallback,audit_status="valid",
            final_reference=final_ref,added_pids=added,dropped_pids=list(dict.fromkeys(dropped)),
            addition_roles=roles,requirements=au["requirements"],unresolved=au["unresolved"],
            must_keep_n=len(must),safe_drop_n=len(safe),hard_protected_n=len(protected),
            baseline_body_chars=c.pack_size(base,corpus),
            final_body_chars=c.pack_size(current,corpus) if changed else c.pack_size(base,corpus),
            judge_request_id=jrid))

    c.jsonl(c.OUT/"pack_mapping_v2.jsonl",mapping)
    c.jsonl(c.OUT/"stage2v2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts)
    c.put(c.OUT/"stage2v2_freeze.json",dict(
        created_utc=c.now(),audited=sum(x["audit_status"]=="valid" for x in mapping),
        changed=sum(x["changed"] for x in mapping),judge_jobs=len(jobs),
        fallbacks=dict(Counter(x["fallback"] for x in mapping if x["fallback"])),
        additions=sum(len(x["added_pids"]) for x in mapping),
        drops=sum(len(x["dropped_pids"]) for x in mapping),
        roles=dict(Counter(r for x in mapping for r in x["addition_roles"])),
        current_used_cny=used,
        stage2_conservative_bound_cny=sum(c.bound(j) for j in jobs),
        code_sha256=c.sha(Path(__file__))))
    print("067 STAGE2 V2 BUILT","changed",len(jobs),"used",round(used,4),
          "bound",round(sum(c.bound(j) for j in jobs),4),flush=True)

if __name__=="__main__":main()
