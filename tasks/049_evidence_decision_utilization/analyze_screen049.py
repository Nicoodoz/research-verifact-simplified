"""Analyze 049 screen decisions. No API calls."""
from pathlib import Path
from collections import Counter
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/049_evidence_decision_utilization"))
import common049 as c
import run049
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c48
import run048

def unpack(term,rid):
    p=term[rid]["parsed"];sc=p.get("scores")
    c.require(p.get("status") in c.VALID and sc is not None,"invalid "+rid)
    return dict(raw=p.get("verdict"),U0=c.ulabel(sc,0),U2=c.ulabel(sc,2),
      scores=sc,reason=(p.get("parsed") or {}).get("reason"))

def has_contradiction(p):
    for row in p.get("requirements",[]):
        if row.get("relation")=="contradicted" and any(ev.get("valid") for ev in row.get("evidence",[])):return True
    return False

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    recs={x["id"]:x for x in c.lines(c.OUT/"screen_trigger_records.jsonl")}
    freeze=c.read(c.OUT/"screen_stage2_freeze.json")
    control_ids=set(freeze["control_ids"]);repeat_ids=set(freeze["repeat_ids"])
    attempts,term=run049.state()
    jobs48={(x["id"],x["condition"]):x for x in c48.lines(c48.OUT/"screen_stage2_jobs.jsonl")}
    _,term48=run048.state()

    by={};detail=[]
    for pid,x in cases.items():
        h=c.stable("",pid)[:24];bp=unpack(term,"049_B_"+h)
        base=bp["U2"];trig=recs[pid]["trigger"]
        aj=jobs48[(pid,"K")];ap=term48[aj["request_id"]]["parsed"]
        A=bp["raw"] if trig and has_contradiction(ap) else base
        B=ap.get("audit_label") if trig and ap.get("status")=="valid" and ap.get("citations_valid") is True and ap.get("audit_label") in ("Supported","Not Supported","Not Addressed") else base
        Hard=(base if ap.get("strict_supported") and ap.get("citations_valid") is True else bp["raw"]) if trig else base
        preds={"BASE":base,"A":A,"B":B,"Hard":Hard}
        aux={}
        for cond in ("E","C","R"):
            if trig:
                q=unpack(term,"049_"+cond+"_"+h);preds[cond]=q["raw"];aux[cond]=q
                preds[cond+"_U2"]=q["U2"]
            else:
                preds[cond]=base;preds[cond+"_U2"]=base
        for method,pred in preds.items():
            by[(pid,method)]=dict(id=pid,sid=x["sid"],GT=x["GT"],author=x["author"],method=method,
              pred=pred,correct=pred==x["GT"],false_S=x["GT"]!="Supported" and pred=="Supported",trigger=trig)
        detail.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],trigger=trig,
          B_raw=bp["raw"],B_U2=base,audit_label=ap.get("audit_label"),audit_coverage=ap.get("coverage"),
          citations_valid=ap.get("citations_valid"),contradiction=has_contradiction(ap),
          E=preds["E"],C=preds["C"],R=preds["R"],E_U2=preds["E_U2"],C_U2=preds["C_U2"],R_U2=preds["R_U2"]))

    summary=[]
    methods=("BASE","A","B","Hard","E","C","R","E_U2","C_U2","R_U2")
    base_correct={pid:by[(pid,"BASE")]["correct"] for pid in cases}
    base_false=sum(by[(pid,"BASE")]["false_S"] for pid in cases)
    for method in methods:
        rr=[by[(pid,method)] for pid in cases]
        row=dict(method=method,n=len(rr),correct=sum(x["correct"] for x in rr),
          false_S=sum(x["false_S"] for x in rr),changed=sum(x["pred"]!=by[(x["id"],"BASE")]["pred"] for x in rr))
        if method!="BASE":
            row["rescued"]=sum((not base_correct[x["id"]]) and x["correct"] for x in rr)
            row["harmed"]=sum(base_correct[x["id"]] and (not x["correct"]) for x in rr)
            row["net"]=row["rescued"]-row["harmed"]
            row["rescue_patients"]=len({x["sid"] for x in rr if (not base_correct[x["id"]]) and x["correct"]})
            row["false_S_delta"]=row["false_S"]-base_false
        summary.append(row)

    # Method-specific pre-registered pass rules.
    sm={z["method"]:z for z in summary}
    promoted=[]
    for method in ("E","C","R"):
        z=sm[method]
        accuracy=(z["net"]>=2 and z["harmed"]<=1 and z["rescue_patients"]>=2 and z["false_S_delta"]<=0)
        risk=(z["false_S_delta"]<=-2 and z["net"]>=-1 and len({x["sid"] for x in [by[(pid,method)] for pid in cases] if x["false_S"]!=by[(x["id"],"BASE")]["false_S"]})>=2)
        incremental=True
        if method in ("C","R"):
            e=sm["E"]
            incremental=(z["correct"]>=e["correct"]+1) or (z["correct"]>=e["correct"] and z["false_S"]<=e["false_S"]-1)
        z["accuracy_pass"]=accuracy;z["risk_pass"]=risk;z["incremental_vs_E"]=incremental
        z["passes"]=bool((accuracy or risk) and incremental)
        if z["passes"]:promoted.append(method)

    # Correct-alignment ablation on fixed control subset.
    controls=[]
    for pid in sorted(control_ids):
        h=c.stable("",pid)[:24];x=cases[pid]
        cp=unpack(term,"049_C_"+h);tp=unpack(term,"049_CTL_"+h)
        controls.append(dict(id=pid,sid=x["sid"],GT=x["GT"],C=cp["raw"],CTL=tp["raw"],
          C_correct=cp["raw"]==x["GT"],CTL_correct=tp["raw"]==x["GT"],label_diff=cp["raw"]!=tp["raw"]))

    repeats=[]
    for pid in sorted(repeat_ids):
        h=c.stable("",pid)[:24];x=cases[pid]
        b=unpack(term,"049_B_"+h);br=unpack(term,"049_Brep_"+h)
        cc=unpack(term,"049_C_"+h);cr=unpack(term,"049_Crep_"+h)
        rr=unpack(term,"049_R_"+h);rrep=unpack(term,"049_Rrep_"+h)
        repeats.append(dict(id=pid,sid=x["sid"],GT=x["GT"],
          B=b["raw"],B_repeat=br["raw"],B_changed=b["raw"]!=br["raw"],
          B_U2=b["U2"],B_repeat_U2=br["U2"],B_U2_changed=b["U2"]!=br["U2"],
          C=cc["raw"],C_repeat=cr["raw"],C_changed=cc["raw"]!=cr["raw"],
          R=rr["raw"],R_repeat=rrep["raw"],R_changed=rr["raw"]!=rrep["raw"]))

    result=dict(created_utc=c.now(),trigger_n=sum(x["trigger"] for x in recs.values()),
      summary=summary,promoted=promoted,
      controls=dict(n=len(controls),label_diff=sum(x["label_diff"] for x in controls),
        C_correct=sum(x["C_correct"] for x in controls),CTL_correct=sum(x["CTL_correct"] for x in controls)),
      repeats=dict(n=len(repeats),B_raw_changes=sum(x["B_changed"] for x in repeats),
        B_U2_changes=sum(x["B_U2_changed"] for x in repeats),
        C_raw_changes=sum(x["C_changed"] for x in repeats),R_raw_changes=sum(x["R_changed"] for x in repeats)),
      cost_cny=sum(a["cost"] for a in attempts),api_attempts=len(attempts),
      http200=sum(a["http_status"]==200 for a in attempts))
    c.put(c.OUT/"screen_analysis.json",result)
    c.csvwrite(c.OUT/"screen_cases_analysis.csv",detail)
    c.csvwrite(c.OUT/"screen_summary.csv",summary)
    c.csvwrite(c.OUT/"screen_controls.csv",controls)
    c.csvwrite(c.OUT/"screen_repeats.csv",repeats)
    c.put(c.OUT/"screen_decision.json",dict(created_utc=c.now(),promoted=promoted,stop=not bool(promoted),
      rule="accuracy or risk lane; C/R additionally require increment over E"))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
