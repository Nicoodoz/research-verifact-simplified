"""Build 049 E/C/R/control/repeat DeepSeek jobs after fresh baseline trigger."""
from pathlib import Path
import copy,json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/049_evidence_decision_utilization"))
import common049 as c
import run049
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c48
import run048

ALIGN_SYS="""The user payload may include verification_index.
verification_index is only a navigation aid that links material claim requirements to exact quotes and evidence numbers in the supplied reference. It is not a gold label and may be incomplete or fallible.
Use the original EHR reference as the source of truth. Judge the complete proposition at its stated strength, time, event status, and qualifiers. Do not strengthen the proposition or treat missing evidence as contradiction."""

REL_SYS="""The user payload may include verification_index with fallible relation annotations from an independent evidence audit.
These relation annotations are not gold labels. Re-check every relation against the quoted text and the complete original EHR reference before deciding. The EHR reference is the source of truth."""

def index_body(claim,reference,index,relation=False):
    b=c.score_body(claim,reference)
    payload=json.loads(b["messages"][1]["content"])
    payload["verification_index"]=index
    b["messages"][1]["content"]=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
    b["messages"][0]["content"]+="\n\n"+(REL_SYS if relation else ALIGN_SYS)
    return b

def map_index(parsed,audit_job,kept_pids,base_reference,with_relation):
    nums=[int(z) for z in re.findall(r"(?m)^(\d+)\. Date:",base_reference)]
    base_max=max(nums) if nums else 0
    pid_to_num={pid:base_max+i+1 for i,pid in enumerate(kept_pids)}
    out=[]
    for row in parsed.get("requirements",[]):
        z={"claim_requirement":row.get("claim_requirement")}
        if with_relation:z["relation"]=row.get("relation")
        evs=[]
        for ev in row.get("evidence",[]):
            if not ev.get("valid"):continue
            eid=str(ev.get("id",""))
            num=None
            if eid.startswith("C") and eid[1:].isdigit():num=int(eid[1:])
            elif eid in audit_job["evidence_lookup"]:
                pid=audit_job["evidence_lookup"][eid].get("passage_id")
                num=pid_to_num.get(pid)
            if num is not None:evs.append({"evidence_id":num,"quote":ev.get("quote","")})
        z["evidence"]=evs
        out.append(z)
    return out

def main():
    if (c.OUT/"screen_stage2_jobs.jsonl").exists():raise RuntimeError("049 stage2 already built")
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    attempts,term=run049.state()
    # Load frozen 048 K audit and evidence mapping only; no new Qwen calls in screen.
    jobs48={(x["id"],x["condition"]):x for x in c48.lines(c48.OUT/"screen_stage2_jobs.jsonl")}
    map48={(x["id"],x["condition"]):x for x in c48.lines(c48.OUT/"screen_final_mapping.jsonl")}
    _,term48=run048.state()
    corpus={x["passage_id"]:x for x in c48.lines(c48.R031/"materials_001/corpus.jsonl")}

    triggered=[];records=[];jobs=[];details={}
    for pid,x in cases.items():
        h=c.stable("",pid)[:24]
        bp=term["049_B_"+h]["parsed"];sc=bp.get("scores")
        valid=bp.get("status") in c.VALID and sc is not None
        c.require(valid,"fresh B invalid")
        raw=bp.get("verdict");u2=c.ulabel(sc,2)
        trig=raw!="Supported" and u2=="Supported"
        rec=dict(id=pid,sid=x["sid"],trigger=trig,B_raw=raw,B_U2=u2,B_scores=sc)
        if trig:
            triggered.append(pid)
            aj=jobs48[(pid,"K")];ap=term48[aj["request_id"]]["parsed"];m=map48[(pid,"K")]
            kept=m["kept_external_pids"]
            ref,_=c48.append_passages(x["base_reference"],kept,corpus)
            idxC=map_index(ap,aj,kept,x["base_reference"],False)
            idxR=map_index(ap,aj,kept,x["base_reference"],True)
            details[pid]=(ref,idxC,idxR)
            rec.update(K_audit_status=ap.get("status"),K_audit_label=ap.get("audit_label"),
              K_citations_valid=ap.get("citations_valid"),kept_external_pids=kept,
              reference_changed=ref!=x["base_reference"],index_requirements=len(idxC))
            jobs.append(dict(request_id="049_E_"+h,stage="screen_stage2",kind="judge",model_key="deepseek",condition="E",id=pid,body=c.score_body(x["claim"],ref)))
            jobs.append(dict(request_id="049_C_"+h,stage="screen_stage2",kind="judge",model_key="deepseek",condition="C",id=pid,body=index_body(x["claim"],ref,idxC,False)))
            jobs.append(dict(request_id="049_R_"+h,stage="screen_stage2",kind="judge",model_key="deepseek",condition="R",id=pid,body=index_body(x["claim"],ref,idxR,True)))
        records.append(rec)

    # Fixed control eligibility uses only audit structure, never GT.
    eligible=[]
    for pid in triggered:
        idx=details[pid][1]
        if len(idx)>=2 and sum(bool(z.get("evidence")) for z in idx)>=2:eligible.append(pid)
    control_ids=set(sorted(eligible,key=lambda pid:c.stable("049/control/v1:",pid))[:8])
    repeat_ids=set(sorted(triggered,key=lambda pid:c.stable("049/repeat/v1:",pid))[:6])

    for pid in sorted(triggered):
        x=cases[pid];h=c.stable("",pid)[:24];ref,idxC,idxR=details[pid]
        if pid in control_ids:
            scrambled=copy.deepcopy(idxC)
            evlists=[copy.deepcopy(z.get("evidence",[])) for z in scrambled]
            rotated=evlists[1:]+evlists[:1]
            for z,evs in zip(scrambled,rotated):z["evidence"]=evs
            jobs.append(dict(request_id="049_CTL_"+h,stage="screen_stage2",kind="judge",
              model_key="deepseek",condition="CTL",id=pid,body=index_body(x["claim"],ref,scrambled,False)))
        if pid in repeat_ids:
            jobs.append(dict(request_id="049_Brep_"+h,stage="screen_stage2",kind="judge",
              model_key="deepseek",condition="B_repeat",id=pid,body=c.score_body(x["claim"],x["base_reference"])))
            jobs.append(dict(request_id="049_Crep_"+h,stage="screen_stage2",kind="judge",
              model_key="deepseek",condition="C_repeat",id=pid,body=index_body(x["claim"],ref,idxC,False)))
            jobs.append(dict(request_id="049_Rrep_"+h,stage="screen_stage2",kind="judge",
              model_key="deepseek",condition="R_repeat",id=pid,body=index_body(x["claim"],ref,idxR,True)))

    c.jsonl(c.OUT/"screen_trigger_records.jsonl",records)
    c.jsonl(c.OUT/"screen_stage2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.SCREEN_CAP+1e-9,"049 screen budget bound")
    c.put(c.OUT/"screen_stage2_freeze.json",dict(created_utc=c.now(),trigger_n=len(triggered),
      trigger_ids=sorted(triggered),control_ids=sorted(control_ids),repeat_ids=sorted(repeat_ids),
      jobs=len(jobs),current_used_cny=used,stage2_bound_cny=bound,total_bound_cny=used+bound,
      GT_used_for_trigger_or_jobs=False))
    print("049 METHODS BUILT",dict(trigger=len(triggered),control=len(control_ids),repeat=len(repeat_ids),
      jobs=len(jobs),used=round(used,4),bound=round(bound,4),total=round(used+bound,4)),flush=True)

if __name__=="__main__":main()
