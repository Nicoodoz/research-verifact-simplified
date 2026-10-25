"""Analyze 047 diagnostic screen and freeze promotion decision."""
from pathlib import Path
from collections import Counter
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/047_mechanism_stratified_validation"))
import common047 as c
import run047
VALID=("valid","valid_with_format_anomaly")
ROUTES=("B","J","P","S")

def judge(term,rid):
    c.require(rid in term,"missing "+str(rid))
    p=term[rid]["parsed"]
    if p.get("status") not in VALID:
        return {"valid":False,"verdict":None,"scores":None,"reason":None}
    return {"valid":True,"verdict":p.get("verdict"),"scores":p.get("scores"),"reason":(p.get("parsed") or {}).get("reason")}

def main():
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    smap={x["id"]:x for x in c.lines(c.OUT/"screen_S_mapping.jsonl")}
    attempts,term=run047.state()
    rows=[];by={}
    for pid,x in cases.items():
        preds={}
        for route,prefix in (("B","047_B_"),("J","047_J_"),("P","047_P_")):
            preds[route]=judge(term,prefix+c.stable("",pid)[:24])
        m=smap[pid]
        preds["S"]=judge(term,m["final_request_id"]) if m["final_request_id"] else preds["B"]
        for route in ROUTES:
            p=preds[route]
            ok=p["verdict"]==x["GT"] if p["valid"] else False
            fs=bool(p["valid"] and x["GT"]!="Supported" and p["verdict"]=="Supported")
            u=c.u2(p["scores"]) if route in ("B","P","S") and p.get("scores") else None
            row={"id":pid,"sid":x["sid"],"author":x["author"],"GT":x["GT"],"route":route,"valid":p["valid"],"verdict":p["verdict"],"correct":ok,"false_S":fs,"U2":u,"reason":p.get("reason")}
            rows.append(row);by[(pid,route)]=row
    summary=[]
    base_false=sum(by[(pid,"B")]["false_S"] for pid in cases)
    for route in ROUTES:
        rr=[by[(pid,route)] for pid in cases]
        valid=sum(x["valid"] for x in rr)
        correct=sum(x["correct"] for x in rr)
        rescued=0;harmed=0;rp=set()
        if route!="B":
            for x in rr:
                b=by[(x["id"],"B")]
                if (not b["correct"]) and x["correct"]:rescued+=1;rp.add(x["sid"])
                if b["correct"] and (not x["correct"]):harmed+=1
        false_s=sum(x["false_S"] for x in rr)
        row={"route":route,"n":len(rr),"valid":valid,"correct":correct,"rescued":rescued,"harmed":harmed,"net":rescued-harmed,"rescue_patients":len(rp),"false_S":false_s,"false_S_delta":false_s-base_false}
        if route in ("B","P","S"):
            row["U2_correct"]=sum(x["U2"]==x["GT"] for x in rr if x["U2"] is not None)
        summary.append(row)
    passes=[]
    for row in summary:
        if row["route"]=="B":continue
        ok=(row["valid"]==row["n"] and row["net"]>=2 and row["rescued"]>=2 and row["rescue_patients"]>=2 and row["harmed"]<=1 and row["false_S_delta"]<=0)
        row["passes"]=ok
        if ok:passes.append(row)
    complexity={"P":1,"J":1,"S":2};tie={"P":0,"J":1,"S":2}
    passes.sort(key=lambda z:(-z["net"],z["harmed"],-z["rescue_patients"],complexity[z["route"]],tie[z["route"]]))
    promoted=[x["route"] for x in passes[:2]]
    repeats=[]
    for pid in c.read(c.OUT/"freeze.json")["repeat_ids"]:
        p=judge(term,"047_Brep_"+c.stable("",pid)[:24])
        repeats.append({"id":pid,"base":by[(pid,"B")]["verdict"],"repeat":p["verdict"],"changed":p["verdict"]!=by[(pid,"B")]["verdict"]})
    transitions=[]
    for route in ("J","P","S"):
        for pid,x in cases.items():
            b=by[(pid,"B")];r=by[(pid,route)]
            if r["verdict"]!=b["verdict"]:
                transitions.append({"route":route,"id":pid,"sid":x["sid"],"author":x["author"],"GT":x["GT"],"claim":x["claim"],"base":b["verdict"],"new":r["verdict"],"base_correct":b["correct"],"new_correct":r["correct"]})
    cost=sum(x["cost"] for x in attempts)
    result={"created_utc":c.now(),"summary":summary,"promoted":promoted,"repeats":repeats,"transitions":transitions,"cost_cny":cost,"api_attempts":len(attempts),"http200":sum(x["http_status"]==200 for x in attempts)}
    c.put(c.OUT/"screen_analysis.json",result)
    c.csvwrite(c.OUT/"screen_predictions.csv",rows)
    c.csvwrite(c.OUT/"screen_route_summary.csv",summary)
    c.csvwrite(c.OUT/"screen_transitions.csv",transitions)
    c.put(c.OUT/"screen_decision.json",{"created_utc":c.now(),"promoted":promoted,"stop":not bool(promoted),"rule":"net>=2,rescue>=2,rescue_patients>=2,harm<=1,falseS_delta<=0; max2 fixed tie-break"})
    md=["# 047 Screen Result","","24条development诊断screen；不是总体benchmark。","","|route|valid|correct|rescue|harm|net|rescue patients|false-S Δ|pass|","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for z in summary:
        md.append(f"|{z['route']}|{z['valid']}/{z['n']}|{z['correct']}|{z['rescued']}|{z['harmed']}|{z['net']}|{z['rescue_patients']}|{z['false_S_delta']:+d}|{z.get('passes','baseline')}|")
    md += ["",f"Promoted: {', '.join(promoted) if promoted else 'none'}",f"Same-input baseline repeat changes: {sum(x['changed'] for x in repeats)}/{len(repeats)}",f"API cost estimate: ¥{cost:.6f} / screen cap ¥{c.SCREEN_CAP:.0f}"]
    (c.OUT/"screen_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    main()
