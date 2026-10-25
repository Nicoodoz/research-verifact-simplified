"""Freeze 047 patient split, 24-case screen and 64-case confirmation sample."""
from pathlib import Path
from collections import Counter,defaultdict
import copy,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/047_mechanism_stratified_validation"))
import common047 as c

def choose_screen(rows):
    counts=Counter();chosen=[]
    for wanted in (False,True):
        pool=[x for x in rows if x["historical_correct"]==wanted]
        groups=defaultdict(list)
        for x in pool:groups[(x["GT"],x["author"])].append(x)
        for g in sorted(groups):
            cand=sorted(groups[g],key=lambda x:(c.stable("047/screen/coverage/v1:",x["id"]),x["id"]))
            z=next((x for x in cand if x["id"] not in {q["id"] for q in chosen} and counts[x["sid"]]<6),None)
            if z and sum(q["historical_correct"]==wanted for q in chosen)<12:
                chosen.append(z);counts[z["sid"]]+=1
        remain=sorted(pool,key=lambda x:(c.stable("047/screen/fill/v1:",x["id"]),x["id"]))
        for z in remain:
            if sum(q["historical_correct"]==wanted for q in chosen)>=12:break
            if z["id"] in {q["id"] for q in chosen} or counts[z["sid"]]>=6:continue
            chosen.append(z);counts[z["sid"]]+=1
    c.require(len(chosen)==24 and sum(not x["historical_correct"] for x in chosen)==12,
              "screen quota failed")
    return chosen,counts

def choose_confirmation(cases,confirm_patients,n=64):
    by=defaultdict(list)
    for x in cases:
        if x["sid"] in confirm_patients:by[x["sid"]].append(x)
    for sid in by:
        by[sid].sort(key=lambda x:(c.stable("047/confirm/case/v1:",x["id"]),x["id"]))
    selected=[];i=0
    order=sorted(confirm_patients,key=lambda s:c.stable("047/confirm/patient/v1:",s))
    while len(selected)<n:
        progressed=False
        for sid in order:
            if i<len(by[sid]) and len(selected)<n:
                selected.append(by[sid][i]);progressed=True
        if not progressed:break
        i+=1
    c.require(len(selected)==n,"not enough confirmation cases")
    return selected

def main():
    if any(c.OUT.iterdir()):raise RuntimeError("047 output not empty")
    train=c.lines(c.R044/"planning_001/train_cases.jsonl")
    oof={x["id"]:x for x in c.lines(c.R044/"model/oof.jsonl")}
    c.require(set(x["id"] for x in train)==set(oof),"044 train/oof mismatch")
    sids=sorted({x["sid"] for x in train},key=lambda s:c.stable("047/patient/v1:",s))
    c.require(len(sids)==10,"expected 10 patients")
    screen_patients=set(sids[:5]);confirm_patients=set(sids[5:])
    avail=[dict(id=x["id"],sid=x["sid"],author=x["author"],GT=x["GT"],
                historical_base=oof[x["id"]]["base"],
                historical_correct=oof[x["id"]]["base"]==x["GT"])
           for x in train if x["sid"] in screen_patients]
    chosen,counts=choose_screen(avail)
    cases={x["id"]:x for x in train}
    candidates={x["proposition_id"]:x for x in c.lines(c.R031/"retrieval_001/candidates.jsonl")}
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}

    screen=[];jobs=[];repeat_ids={x["id"] for x in sorted(chosen,key=lambda z:c.stable("047/repeat/v1:",z["id"]))[:6]}
    for meta in chosen:
        x=cases[meta["id"]];pid=x["id"];base=x["base"]
        focus,focus_order,focus_changed=c.focus_reference(x["claim"],base)
        cids=candidates[pid]["candidate_ids"]["C48"]
        base_text={c.norm(corpus[p]["text"]) for p in x["base_ids"]}
        extras=[p for p in cids if p not in set(x["base_ids"]) and c.norm(corpus[p]["text"]) not in base_text]
        short={f"C{k+1:02d}":p for k,p in enumerate(extras)}
        rendered=[c.candidate_text(s,corpus[p]) for s,p in short.items()]
        row=dict(**meta,claim=x["claim"],base_reference=base,base_ids=x["base_ids"],
                 focus_reference=focus,focus_order=focus_order,focus_changed=focus_changed,
                 extra_short_to_pid=short,extra_candidates=rendered)
        screen.append(row)
        jobs.append(dict(request_id="047_B_"+c.stable("",pid)[:24],stage="screen",route="B",
            kind="judge",model_key="deepseek",id=pid,body=c.score_body(x["claim"],base,"deepseek")))
        jobs.append(dict(request_id="047_J_"+c.stable("",pid)[:24],stage="screen",route="J",
            kind="judge",model_key="qwen",id=pid,body=c.score_body(x["claim"],base,"qwen")))
        jobs.append(dict(request_id="047_P_"+c.stable("",pid)[:24],stage="screen",route="P",
            kind="judge",model_key="deepseek",id=pid,body=c.score_body(x["claim"],focus,"deepseek")))
        jobs.append(dict(request_id="047_Ssel_"+c.stable("",pid)[:24],stage="screen_selector",route="S_selector",
            kind="selector",model_key="qwen",id=pid,body=c.selector_body(x["claim"],base,rendered)))
        if pid in repeat_ids:
            jobs.append(dict(request_id="047_Brep_"+c.stable("",pid)[:24],stage="screen",route="B_repeat",
                kind="judge",model_key="deepseek",id=pid,body=c.score_body(x["claim"],base,"deepseek")))
    confirm=choose_confirmation(train,confirm_patients,64)
    c.jsonl(c.OUT/"screen_cases.jsonl",screen)
    c.jsonl(c.OUT/"screen_stage1_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    c.jsonl(c.OUT/"confirmation_cases_frozen.jsonl",confirm)

    sources=[
      c.R044/"planning_001/train_cases.jsonl",
      c.R044/"model/oof.jsonl",
      c.R031/"retrieval_001/candidates.jsonl",
      c.R031/"materials_001/corpus.jsonl",
      ROOT/"tasks/047_mechanism_stratified_validation/protocol.md"]
    composition=Counter()
    for x in screen:
        key=("correct" if x["historical_correct"] else "error")+"|"+x["GT"]+"|"+x["author"]
        composition[key]+=1
    src_hash={str(p.relative_to(ROOT)):c.sha(p) for p in sources}
    freeze={"created_utc":c.now(),"screen_patients":sorted(screen_patients),"confirmation_patients":sorted(confirm_patients),"screen_n":len(screen),"confirmation_n":len(confirm)}
    freeze["screen_patient_counts"]=dict(counts)
    freeze["screen_historical_composition"]=dict(composition)
    freeze["repeat_ids"]=sorted(repeat_ids)
    freeze["screen_stage1_jobs"]=len(jobs)
    freeze["screen_cap_cny"]=c.SCREEN_CAP
    freeze["total_cap_cny"]=c.TOTAL_CAP
    freeze["confirmation_selection_uses_GT"]=False
    freeze["sources"]=src_hash
    c.put(c.OUT/"freeze.json",freeze)
    print("047 PREPARED",len(screen),len(confirm),len(jobs),dict(counts),flush=True)

if __name__=="__main__":
    main()
