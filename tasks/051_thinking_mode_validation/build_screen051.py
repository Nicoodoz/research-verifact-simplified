"""Build frozen 051 clinical screen/repeats and synthetic semantic-pair jobs."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import common051 as c
import run051

CONDS=(("N-S",True,False),("N-V",False,False),("T-S",True,True),("T-V",False,True))

def semantic_cases():
    groups=[
      ("temporal_scope","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 10:00:00, Note Category: Procedure | Text: The patient was intubated after the procedure.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 09:00:00, Note Category: Nursing | Text: The patient was extubated this morning.",
       [("The patient remained intubated immediately after the procedure.","Supported"),("The patient remained intubated throughout the hospitalization.","Not Supported")]),
      ("plan_completion","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 08:00:00, Note Category: Physician | Text: Plan: obtain CT chest tomorrow. No CT result is documented in this reference.",
       [("A CT chest was planned.","Supported"),("A CT chest was performed.","Not Supported")]),
      ("refusal_completion","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 11:00:00, Note Category: Nursing | Text: Patient refused the repeat speech and swallow study.",
       [("The patient refused the repeat speech and swallow study.","Supported"),("The repeat speech and swallow study was performed.","Not Supported")]),
      ("possible_confirmed","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 12:00:00, Note Category: Physician | Text: Possible pulmonary embolism was considered as a cause of the tachycardia.",
       [("Pulmonary embolism was considered a possible cause.","Supported"),("Pulmonary embolism was confirmed as the cause.","Not Supported")]),
      ("considered_excluded","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 09:00:00, Note Category: Physician | Text: New pulmonary embolism is in the differential.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 15:00:00, Note Category: Radiology | Text: CT angiography shows no pulmonary embolism.",
       [("Pulmonary embolism was considered in the differential.","Supported"),("Pulmonary embolism was confirmed on CT angiography.","Not Supported")]),
      ("local_global_stability","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 13:00:00, Note Category: Procedure | Text: Immediately post procedure the patient was hemodynamically stable.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 06:00:00, Note Category: Physician | Text: Overnight the patient developed hypotension requiring norepinephrine.",
       [("The patient was hemodynamically stable immediately after the procedure.","Supported"),("The patient's vital signs remained stable throughout the post-procedure period.","Not Supported")]),
      ("single_series","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 08:00:00, Note Category: Radiology | Text: Chest radiograph: no definite consolidation.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 08:00:00, Note Category: Radiology | Text: New opacity; pneumonia cannot be excluded.",
       [("One chest radiograph showed no definite consolidation.","Supported"),("A series of chest radiographs consistently showed no consolidation.","Not Supported")]),
      ("attempt_continuation","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 10:00:00, Note Category: Physician | Text: Heparin was attempted, but the patient felt hot and became tachycardic, so heparin was stopped.",
       [("Heparin was attempted.","Supported"),("Heparin therapy was continued without interruption.","Not Supported")]),
      ("success_complication","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 14:00:00, Note Category: Procedure | Text: Ablation was successful.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 07:00:00, Note Category: Physician | Text: A post-procedure groin hematoma required monitoring.",
       [("The ablation was successful.","Supported"),("The procedure had no complications.","Not Supported")]),
      ("negation_scope","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 09:00:00, Note Category: Physician | Text: The patient denied chest pain but reported shortness of breath.",
       [("The patient denied chest pain.","Supported"),("The patient denied all cardiopulmonary symptoms.","Not Supported")]),
      ("conditional_plan","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 09:00:00, Note Category: Physician | Text: If fever develops, start ceftriaxone. The patient remained afebrile in the supplied reference.",
       [("Starting ceftriaxone was a conditional plan if fever developed.","Supported"),("Ceftriaxone was started for fever.","Not Supported")]),
      ("state_change","1. Date: [CLINICAL_LITERAL_REMOVED], Time: 08:00:00, Note Category: Nursing | Text: Patient on 2 L nasal cannula this morning.\n2. Date: [CLINICAL_LITERAL_REMOVED], Time: 20:00:00, Note Category: Nursing | Text: Patient now comfortable on room air.",
       [("The patient required supplemental oxygen in the morning.","Supported"),("The patient never required supplemental oxygen.","Not Supported")]),
    ]
    out=[]
    for g,ref,pairs in groups:
        reference="Electronic Health Record Context\n"+ref
        for i,(claim,label) in enumerate(pairs):
            out.append(dict(id=f"semantic_{g}_{i}",group=g,claim=claim,reference=reference,expected=label))
    return out

def main():
    if (c.OUT/"screen_jobs.jsonl").exists():raise RuntimeError("051 screen already built")
    # Preflight must be complete and genuinely thinking.
    attempts,term=run051.state()
    for cond,scored,thinking in CONDS:
        rid="051_pre_"+cond.replace("-","_")
        c.require(rid in term and term[rid]["parsed"].get("status") in c.VALID,"preflight missing "+cond)
        if thinking:c.require(term[rid]["parsed"].get("reasoning_present") is True,"thinking preflight missing reasoning "+cond)

    cases=c.lines(c.OUT/"screen_cases.jsonl")
    repeat_ids={x["id"] for x in sorted(cases,key=lambda z:c.stable("051/repeat/v1:",z["id"]))[:6]}
    jobs=[]
    for x in cases:
        h=c.stable("",x["id"])[:24]
        for cond,scored,thinking in CONDS:
            jobs.append(dict(request_id="051_"+cond.replace("-","_")+"_"+h,stage="screen",
              kind="judge",condition=cond,id=x["id"],scored=scored,thinking=thinking,
              body=c.judge_body(x["claim"],x["reference"],scored,thinking)))
            if x["id"] in repeat_ids:
                jobs.append(dict(request_id="051_"+cond.replace("-","_")+"_rep_"+h,stage="screen",
                  kind="judge",condition=cond+"_repeat",id=x["id"],scored=scored,thinking=thinking,
                  body=c.judge_body(x["claim"],x["reference"],scored,thinking)))

    semantics=semantic_cases()
    for x in semantics:
        h=c.stable("",x["id"])[:24]
        for cond,scored,thinking in (("N-V",False,False),("T-V",False,True)):
            jobs.append(dict(request_id="051_sem_"+cond.replace("-","_")+"_"+h,stage="screen",
              kind="judge",condition=cond,id=x["id"],semantic=True,scored=scored,thinking=thinking,
              body=c.judge_body(x["claim"],x["reference"],scored,thinking)))
    jobs.sort(key=lambda z:c.stable("051/screen/order/v1:",z["request_id"]))
    c.jsonl(c.OUT/"semantic_cases.jsonl",semantics)
    c.jsonl(c.OUT/"screen_jobs.jsonl",jobs)
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.SCREEN_CAP+1e-9,f"screen conservative bound {used+bound:.3f}>{c.SCREEN_CAP}")
    c.put(c.OUT/"screen_freeze.json",dict(created_utc=c.now(),clinical_n=len(cases),repeat_ids=sorted(repeat_ids),
      semantic_n=len(semantics),jobs=len(jobs),preflight_used_cny=used,screen_bound_cny=bound,total_bound_cny=used+bound,
      current_protocol_sha256=c.sha(ROOT/"tasks/051_thinking_mode_validation/protocol.md"),
      amendment_sha256=c.sha(c.OUT/"protocol_amendment_001.json")))
    print("051 SCREEN BUILT",dict(clinical=len(cases),semantic=len(semantics),repeat=len(repeat_ids),
      jobs=len(jobs),used=round(used,4),bound=round(bound,4),total=round(used+bound,4)),flush=True)

if __name__=="__main__":main()
