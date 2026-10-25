from pathlib import Path
from collections import Counter
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c
import run048

def unpack_result(term,rid):
    p=term[rid]["parsed"]
    sc=p.get("scores")
    good=p.get("status") in c.VALID and sc is not None
    if not good:return {"valid":False,"raw":None,"U0":None,"U2":None,"scores":None,"reason":None,"checks":[]}
    obj=p.get("parsed") or {}
    return {"valid":True,"raw":p.get("verdict"),"U0":c.ulabel(sc,0),"U2":c.ulabel(sc,2),"scores":sc,"reason":obj.get("reason"),"checks":obj.get("checks") or []}

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    mapping={(x["id"],x["condition"]):x for x in c.lines(c.OUT/"screen_final_mapping.jsonl")}
    attempts,term=run048.state()
    rows=[];by={}
    for pid,x in cases.items():
        h=c.stable("",pid)[:24]
        preds={"B":unpack_result(term,"048_B_"+h)}
        for cond in ("K","G"):
            m=mapping[(pid,cond)]
            preds[cond]=unpack_result(term,m["final_request_id"]) if m["final_request_id"] else preds["B"]
        for cond,p in preds.items():
            m=mapping.get((pid,cond))
            row={"id":pid,"sid":x["sid"],"author":x["author"],"GT":x["GT"],"condition":cond,"valid":p["valid"],"raw":p["raw"],"U0":p["U0"],"U2":p["U2"]}
            row["raw_correct"]=p["raw"]==x["GT"]
            row["U0_correct"]=p["U0"]==x["GT"]
            row["U2_correct"]=p["U2"]==x["GT"]
            row["raw_false_S"]=x["GT"]!="Supported" and p["raw"]=="Supported"
            row["U2_false_S"]=x["GT"]!="Supported" and p["U2"]=="Supported"
            row["supported_score"]=p["scores"].get("Supported") if p.get("scores") else None
            base_max=max([int(z) for z in re.findall(r"(?m)^(\d+)\. Date:",x["base_reference"])] or [0])
            cited=[e for ck in p["checks"] for e in ck.get("evidence_ids",[]) if isinstance(e,int)]
            row["new_evidence_cited"]=bool(cond!="B" and any(e>base_max for e in cited))
            row["reference_changed"]=m["reference_changed"] if m else False
            row["cited_external_n"]=len(m["kept_external_pids"]) if m else 0
            row["audit_label"]=m["audit_label"] if m else None
            row["audit_coverage"]=m["audit_coverage"] if m else None
            row["reason"]=p.get("reason")
            rows.append(row);by[(pid,cond)]=row
    summary=[]
    for cond in ("B","K","G"):
        rr=[by[(pid,cond)] for pid in cases]
        z={"condition":cond,"n":len(rr),"valid":sum(x["valid"] for x in rr)}
        for layer in ("raw","U0","U2"):
            z[layer+"_correct"]=sum(x[layer+"_correct"] for x in rr)
            z[layer+"_false_S"]=sum(x[layer+"_false_S"] for x in rr) if layer in ("raw","U2") else None
            if cond!="B":
                z[layer+"_rescue"]=sum((not by[(x["id"],"B")][layer+"_correct"]) and x[layer+"_correct"] for x in rr)
                z[layer+"_harm"]=sum(by[(x["id"],"B")][layer+"_correct"] and (not x[layer+"_correct"]) for x in rr)
                z[layer+"_net"]=z[layer+"_rescue"]-z[layer+"_harm"]
        z["reference_changed"]=sum(x["reference_changed"] for x in rr)
        z["new_evidence_cited"]=sum(x["new_evidence_cited"] for x in rr)
        z["supported_score_mean"]=sum(x["supported_score"] for x in rr if x["supported_score"] is not None)/sum(x["supported_score"] is not None for x in rr)
        summary.append(z)
    promoted=[]
    base_row=next(x for x in summary if x["condition"]=="B")
    for z in summary:
        if z["condition"]=="B":continue
        cond=z["condition"]
        rp=set()
        for x in rows:
            if x["condition"]==cond and (not by[(x["id"],"B")]["raw_correct"]) and x["raw_correct"]:rp.add(x["sid"])
        z["raw_rescue_patients"]=len(rp)
        z["raw_false_S_delta"]=z["raw_false_S"]-base_row["raw_false_S"]
        z["U2_false_S_delta"]=z["U2_false_S"]-base_row["U2_false_S"]
        passed=True
        passed=passed and z["valid"]==z["n"]
        passed=passed and z["raw_net"]>=2 and z["raw_rescue"]>=2
        passed=passed and z["raw_rescue_patients"]>=2 and z["raw_harm"]<=1
        passed=passed and z["U2_net"]>=0 and z["U2_harm"]<=1
        passed=passed and z["raw_false_S_delta"]<=0
        z["passes"]=bool(passed)
        if passed:promoted.append(cond)
    repeats=[]
    grep={x["id"]:x for x in c.lines(c.OUT/"screen_G_repeats.jsonl")}
    for pid in c.read(c.OUT/"freeze.json")["repeat_ids"]:
        h=c.stable("",pid)[:24]
        br=unpack_result(term,"048_Brep_"+h)
        gr=unpack_result(term,grep[pid]["request_id"])
        repeats.append({"id":pid,"B":by[(pid,"B")]["raw"],"B_repeat":br["raw"],"B_changed":by[(pid,"B")]["raw"]!=br["raw"],"G":by[(pid,"G")]["raw"],"G_repeat":gr["raw"],"G_changed":by[(pid,"G")]["raw"]!=gr["raw"],"B_U2":by[(pid,"B")]["U2"],"B_repeat_U2":br["U2"],"G_U2":by[(pid,"G")]["U2"],"G_repeat_U2":gr["U2"]})
    transitions=[]
    for cond in ("K","G"):
        for pid,x in cases.items():
            b=by[(pid,"B")];m=by[(pid,cond)]
            if m["raw"]!=b["raw"] or m["U2"]!=b["U2"]:
                transitions.append({"condition":cond,"id":pid,"sid":x["sid"],"author":x["author"],"GT":x["GT"],"claim":x["claim"],"B_raw":b["raw"],"new_raw":m["raw"],"B_U2":b["U2"],"new_U2":m["U2"],"B_raw_correct":b["raw_correct"],"new_raw_correct":m["raw_correct"],"B_U2_correct":b["U2_correct"],"new_U2_correct":m["U2_correct"],"audit_label":m["audit_label"],"external_n":m["cited_external_n"],"new_evidence_cited":m["new_evidence_cited"]})
    drift={"raw":sum(by[(pid,"B")]["raw"]!=x["historical_raw"] for pid,x in cases.items()),"U2":sum(by[(pid,"B")]["U2"]!=x["historical_U2"] for pid,x in cases.items())}
    audit_summary={}
    for cond in ("K","G"):
        rr=[x for x in rows if x["condition"]==cond]
        audit_summary[cond]={"labels":dict(Counter(x["audit_label"] for x in rr)),"changed_references":sum(x["reference_changed"] for x in rr),"new_evidence_cited_by_final":sum(x["new_evidence_cited"] for x in rr),"external_passages":sum(x["cited_external_n"] for x in rr)}
    cost=sum(a["cost"] for a in attempts)
    result={"created_utc":c.now(),"summary":summary,"promoted":promoted,"audit_summary":audit_summary,"repeats":repeats,"historical_drift":drift,"transitions":transitions,"cost_cny":cost,"api_attempts":len(attempts),"http200":sum(a["http_status"]==200 for a in attempts)}
    c.put(c.OUT/"screen_analysis.json",result)
    c.csvwrite(c.OUT/"screen_predictions.csv",rows)
    c.csvwrite(c.OUT/"screen_summary.csv",summary)
    c.csvwrite(c.OUT/"screen_transitions.csv",transitions)
    c.put(c.OUT/"screen_decision.json",{"created_utc":c.now(),"promoted":promoted,"stop":not bool(promoted),"rule":"raw net>=2, rescue>=2 across >=2 patients, raw harm<=1, U2 net>=0, U2 harm<=1, raw false-S nonincrease"})
    md=["# 048 Screen Result",""]
    md.append("|cond|raw correct|raw rescue/harm/net|U2 correct|U2 rescue/harm/net|raw false-S d|pass|")
    md.append("|---|---:|---:|---:|---:|---:|---|")
    for z in summary:
        if z["condition"]=="B":
            md.append("|B|%d/%d|baseline|%d/%d|baseline|0|baseline|"%(z["raw_correct"],z["n"],z["U2_correct"],z["n"]))
        else:
            md.append("|%s|%d/%d|%d/%d/%+d|%d/%d|%d/%d/%+d|%+d|%s|"%(z["condition"],z["raw_correct"],z["n"],z["raw_rescue"],z["raw_harm"],z["raw_net"],z["U2_correct"],z["n"],z["U2_rescue"],z["U2_harm"],z["U2_net"],z["raw_false_S_delta"],z["passes"]))
    md.append("")
    md.append("Promoted: "+(", ".join(promoted) if promoted else "none"))
    md.append("B repeat raw changes: %d/%d"%(sum(x["B_changed"] for x in repeats),len(repeats)))
    md.append("G repeat raw changes: %d/%d"%(sum(x["G_changed"] for x in repeats),len(repeats)))
    md.append("API cost estimate: %.6f / screen cap %.0f CNY"%(cost,c.SCREEN_CAP))
    (c.OUT/"screen_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
