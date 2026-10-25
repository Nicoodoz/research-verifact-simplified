"""Freeze D/V/E, full-set proposals and paired V jobs before any 086 Judge output.

E labels/predictions are intentionally never opened in this module.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/"tasks/086_global_demonstration_selection"
OUT=ROOT/"outputs/086_global_demonstration_selection"
SOURCE_POOL=ROOT/"outputs/073_clinical_example_matching/example_pool.jsonl"
CAL=ROOT/"outputs/079_f4_priorg_adaptation/calibration_cases.jsonl"
E_BLIND=ROOT/"outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl"
F4_SOURCE=ROOT/"outputs/071_judge_icl_feasibility/examples.jsonl"
TEMPLATE=ROOT/"outputs/085_r1_70b_model_swap/prompt_semantics.json"
LABELS=("Supported","Not Supported","Not Addressed")
MODEL="deepseek-v4-flash-0731"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def h(value): return hashlib.sha256(value.encode("utf-8")).hexdigest()
def lines(path): return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s]
def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def put(path,obj):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write("\n")
def putl(path,items):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        for x in items:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")


def render(base,header,examples):
    assert len(examples)==4 and [x["physician_label"] for x in examples]==[
        "Supported","Not Supported","Supported","Not Addressed"]
    docs=[{"proposition":x["claim"],"reference":x["reference"],
           "physician_label":x["physician_label"]} for x in examples]
    return base+header+"".join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for x in docs)


def new_body(template,system,claim,reference):
    body=copy.deepcopy(template)
    body["messages"][0]["content"]=system
    body["messages"][1]["content"]=json.dumps({"proposition":claim,"reference":reference},
                                                   ensure_ascii=False,separators=(",",":"))
    assert body["model"]==MODEL and body["enable_thinking"] is True and body["reasoning_effort"]=="high"
    assert body["temperature"]==0 and body["max_tokens"]==8192
    return body


def select_v(cal,d_patients,e_patients):
    groups=defaultdict(list)
    for x in cal:
        if x["sid"] not in d_patients and x["sid"] not in e_patients:
            groups[x["sid"]].append(x)
    assert len(groups)==12
    chosen=[]
    for sid in sorted(groups):
        pool=groups[sid]
        assert len(pool)>=3
        selected=[]
        for label in LABELS:
            matches=sorted((x for x in pool if x["GT"]==label),key=lambda x:h("086V/label/"+x["id"]))
            if matches:selected.append(matches[0])
        for x in sorted(pool,key=lambda x:h("086V/fill/"+x["id"])):
            if len(selected)==3:break
            if x not in selected:selected.append(x)
        assert len(selected)==3
        chosen.extend(selected)
    assert len(chosen)==36 and len({x["id"] for x in chosen})==36
    return sorted(chosen,key=lambda x:(x["sid"],h("086V/order/"+x["id"])))


def select_e(blind,d_patients,v_patients):
    groups=defaultdict(list)
    for x in blind:
        if x["sid"] in d_patients or x["sid"] in v_patients:raise ValueError("D/V/E overlap")
        groups[x["sid"]].append(x)
    assert len(groups)==22 and all(len(v)>=5 for v in groups.values())
    out=[]
    for sid in sorted(groups):
        out.extend(sorted(groups[sid],key=lambda x:h("086E/"+x["id"]))[:5])
    assert len(out)==110 and len({x["id"] for x in out})==110
    return sorted(out,key=lambda x:(x["sid"],h("086E/order/"+x["id"])))


def main():
    if OUT.exists():raise FileExistsError("086 freeze already exists; never overwrite")
    source=lines(SOURCE_POOL); cal=lines(CAL); e_blind=lines(E_BLIND); originals=lines(F4_SOURCE)
    assert len(source)==25 and len(originals)==4 and len(cal)==114 and len(e_blind)==352
    e_patients={x["sid"] for x in e_blind}
    pool=[x for x in source if x["sid"] not in e_patients]
    assert len(pool)==12 and len({x["sid"] for x in pool})==6
    d_patients={x["sid"] for x in pool}
    assert [x["proposition_id"] for x in pool[:4]]==[x["proposition_id"] for x in originals]
    assert all(x["annotation"]["initial_agreement"]=="3" and
               x["annotation"]["second_round_anomaly"]=="False" and
               x["annotation"]["time_metadata_conflict"]=="False" for x in pool)
    v=select_v(cal,d_patients,e_patients)
    v_patients={x["sid"] for x in v}
    assert not (d_patients&v_patients or d_patients&e_patients or v_patients&e_patients)
    e=select_e(e_blind,d_patients,v_patients)
    candidate=[]
    for i,x in enumerate(pool,1):
        candidate.append({**x,"candidate_id":f"C{i:02d}","source_pool_sha256":sha(SOURCE_POOL),
                          "reference_chars":len(x["reference"]),"claim_sha256":h(x["claim"]),
                          "reference_sha256":h(x["reference"]),"quality_status":"existing_073_screen_kept_no_new_clinician_adjudication"})
    bynum={i+1:candidate[i] for i in range(len(candidate))}
    # Three comparable one-slot NA substitutions. A deterministic hash rank
    # chooses two no-utility controls before any V result exists.
    na_rank=sorted((7,11,12),key=lambda i:h("086/random_controls/v1/"+bynum[i]["proposition_id"]))
    assignments={"F4":(1,2,3,4),"R1":(1,2,3,na_rank[0]),
                 "R2":(1,2,3,na_rank[1]),"REP":(1,10,3,7),
                 "N1":(1,2,3,na_rank[2])}
    assert len({tuple(v) for v in assignments.values()})==5
    semantics=read(TEMPLATE)
    base=semantics["B_system_content"]
    appendix=semantics["F4_appendix_exact"]
    header=appendix[:appendix.index('{"physician_label"')]
    assert render(base,header,[bynum[i] for i in assignments["F4"]])==semantics["F4_system_content"]
    bodies={name:render(base,header,[bynum[i] for i in assignment]) for name,assignment in assignments.items()}
    original_chars=len(bodies["F4"])
    assert all(abs(len(s)-original_chars)/original_chars<0.02 for s in bodies.values())
    groups={name:{"ordered_candidate_ids":[bynum[i]["candidate_id"] for i in idx],
                  "ordered_proposition_ids":[bynum[i]["proposition_id"] for i in idx],
                  "ordered_sids":[bynum[i]["sid"] for i in idx],
                  "labels":[bynum[i]["physician_label"] for i in idx],
                  "system_sha256":h(bodies[name]),"system_chars":len(bodies[name]),
                  "example_reference_chars":sum(len(bynum[i]["reference"]) for i in idx),
                  "proposal":"original" if name=="F4" else "hash_random_one_slot" if name in ("R1","R2") else "two_boundary_slots" if name=="REP" else "remaining_one_slot"}
            for name,idx in assignments.items()}
    for x in groups.values():assert len(set(x["ordered_sids"]))==4
    base_body=copy.deepcopy(v[0]["B"]["body"])
    assert base_body["messages"][0]["content"]==base
    v_rows=[]; jobs=[]
    for x in v:
        input_=json.loads(x["B"]["body"]["messages"][1]["content"])
        assert set(input_)=={"proposition","reference"}
        row={"id":x["id"],"sid":x["sid"],"author":None,"GT":x["GT"],
             "claim":input_["proposition"],"reference":input_["reference"],
             "source_079_body_sha256":h(json.dumps(x["B"]["body"],ensure_ascii=False,sort_keys=True,separators=(",",":")))}
        v_rows.append(row)
        for arm in assignments:
            body=new_body(base_body,bodies[arm],row["claim"],row["reference"])
            if arm=="F4":
                # F4 is re-called on V for same-batch selection comparison.
                pass
            canonical=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            jobs.append({"phase":"V","id":x["id"],"sid":x["sid"],"arm":arm,"body":body,
                         "body_sha256":h(canonical),"request_id":h("086/V/"+arm+"/"+x["id"]+"/"+h(canonical))[:24]})
    e_rows=[]
    for x in e:
        req=read(ROOT/x["arms"]["F4"]["request_source"])
        body=req["job"]["body"]
        assert body["messages"][0]["content"]==bodies["F4"]
        content=json.loads(body["messages"][1]["content"])
        assert set(content)=={"proposition","reference"}
        e_rows.append({"id":x["id"],"sid":x["sid"],"author":x["author"],
                       "claim":content["proposition"],"reference":content["reference"],
                       "source_F4_request":x["arms"]["F4"]["request_source"],
                       "source_F4_body_sha256":h(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")))})
    assert len({x["id"] for x in e_rows})==110
    OUT.mkdir(parents=True)
    putl(OUT/"candidate_pool.jsonl",candidate)
    put(OUT/"groups.json",groups)
    putl(OUT/"V_cases.jsonl",v_rows)
    putl(OUT/"E_cases_blind.jsonl",e_rows)
    putl(OUT/"V_jobs.jsonl",jobs)
    files=(SOURCE_POOL,CAL,E_BLIND,F4_SOURCE,TEMPLATE,
           ROOT/"outputs/079_f4_priorg_adaptation/evaluation_apply_freeze.json",
           ROOT/"outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl",
           ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv")
    freeze={"status":"FROZEN_BEFORE_086_NEW_API_AND_E_GT","task_cap_original_cny":30.0,
        "attachment_internal_budget_superseded_cny":20.0,"model":MODEL,
        "price_busy_original_cny_per_million":{"input":3,"output":9},
        "price_source":"https://help.aliyun.com/en/model-studio/model-pricing",
        "roles":{"D_sids":sorted(d_patients),"V_sids":sorted(v_patients),"E_sids":sorted(e_patients)},
        "V_n":36,"E_n":110,"V_label_counts":dict(Counter(x["GT"] for x in v)),
        "candidate_n":len(candidate),"measured_groups":list(assignments),
        "selection_rule":"V full 36 common ID Frozen PriorG MCC highest; ties patient-equal PA, lower false-S, shorter system chars, lexical group name; no E access",
        "E_rule":"always new F4, selected D*, and no-utility R1; if D*=R1, use R2 instead; share identical bodies; new B bridge on 12 E IDs SHA-ranked, paired with new F4",
        "invalid_rule":"HTTP200 core invalid: fixed historical U2 fallback for every arm on same ID; also common-core-valid sensitivity; never retry content-invalid",
        "V_stage_spend_target_cny":8.0,"E_reserved_target_cny":16.0,"unknown_retry_reserve_cny":6.0,
        "max_attempts_per_job":3,"max_workers":3,
        "V_jobs_sha256":sha(OUT/"V_jobs.jsonl"),"groups_sha256":sha(OUT/"groups.json"),
        "V_cases_sha256":sha(OUT/"V_cases.jsonl"),"E_cases_blind_sha256":sha(OUT/"E_cases_blind.jsonl"),
        "candidate_pool_sha256":sha(OUT/"candidate_pool.jsonl"),
        "source_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in files},
        "E_GT_read":False,"new_api_calls":0}
    put(OUT/"freeze.json",freeze)
    print(json.dumps({"D":len(d_patients),"V":len(v_patients),"E":len(e_patients),
        "V_n":36,"E_n":110,"V_GT":freeze["V_label_counts"],"groups":groups,
        "E_GT_read":False},ensure_ascii=False))


if __name__=="__main__":main()
