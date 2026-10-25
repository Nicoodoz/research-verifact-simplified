"""Analyze 046 first-batch six-route retrieval screen. No API calls."""
from pathlib import Path
import json,math,csv,re
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/046_requirement_aware_retrieval_screen"))
import run046
ROUTES=("R1","R2","R3","R4","R5","R6");LABELS=("Supported","Not Supported","Not Addressed")
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
    with Path(p).open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def csvwrite(p,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def u2(scores):
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:math.log(max(float(scores[k])/100,1e-6))+(2 if k=="Supported" else 0))
def main():
    cohort={x["id"]:x for x in lines(OUT/"cohort.jsonl")};mapping=lines(OUT/"final_mapping.jsonl");attempts,term=run046.state()
    assert all(j["request_id"] in term for j in lines(OUT/"stage3_jobs.jsonl"))
    mm={(x["id"],x["route"]):x for x in mapping};pred=[]
    for pid,x in cohort.items():
        base=dict(verdict=x["base_verdict"],scores=x["base_scores"],reason=x["base_reason"],checks=x["base_checks"])
        bmax=max([int(z) for z in re.findall(r"(?m)^(\d+)\. Date:",x["base_reference"])] or [0])
        for route in ("base",)+ROUTES:
            if route=="base":p=base;changed=False;selected=[];added=0;source="E0"
            else:
                m=mm[(pid,route)];changed=m["reference_changed"];selected=m["selected_pids"];added=m["added_chars"];source=m["source"]
                if not changed:p=base
                else:
                    t=term[m["request_id"]]["parsed"];p=dict(verdict=t.get("verdict"),scores=t.get("scores"),
                      reason=(t.get("parsed") or {}).get("reason"),checks=(t.get("parsed") or {}).get("checks"))
            cited=[]
            for ck in p.get("checks") or []:
                for e in ck.get("evidence_ids",[]):
                    if isinstance(e,int):cited.append(e)
            new_cited=bool(changed and any(e>bmax for e in cited))
            pred.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],type=x["type"],route=route,
              verdict=p.get("verdict"),correct=p.get("verdict")==x["GT"],U2=u2(p["scores"]) if p.get("scores") else None,
              reason=p.get("reason"),reference_changed=changed,selected_n=len(selected),selected_pids=";".join(selected),
              added_chars=added,source=source,new_evidence_cited=new_cited))
    by={(r["id"],r["route"]):r for r in pred};summary=[];groups=[]
    for route in ("base",)+ROUTES:
        rr=[r for r in pred if r["route"]==route]
        row=dict(route=route,n=16,correct=sum(r["correct"] for r in rr),U2_correct=sum(r["U2"]==r["GT"] for r in rr),
          false_S=sum(r["GT"]!="Supported" and r["verdict"]=="Supported" for r in rr),
          changed_reference=sum(r["reference_changed"] for r in rr),changed_label=sum(r["verdict"]!=by[(r["id"],"base")]["verdict"] for r in rr),
          new_evidence_cited=sum(r["new_evidence_cited"] for r in rr))
        if route!="base":
            row["rescued"]=sum(not by[(r["id"],"base")]["correct"] and r["correct"] for r in rr)
            row["harmed"]=sum(by[(r["id"],"base")]["correct"] and not r["correct"] for r in rr)
            row["net"]=row["rescued"]-row["harmed"]
            row["U2_rescued"]=sum(by[(r["id"],"base")]["U2"]!=r["GT"] and r["U2"]==r["GT"] for r in rr)
            row["U2_harmed"]=sum(by[(r["id"],"base")]["U2"]==r["GT"] and r["U2"]!=r["GT"] for r in rr)
        summary.append(row)
        for typ in ("retrieval_sensitive","judge_error_control","protection"):
            z=[r for r in rr if r["type"]==typ]
            groups.append(dict(route=route,type=typ,n=len(z),correct=sum(r["correct"] for r in z),
              rescued=sum(route!="base" and (not by[(r["id"],"base")]["correct"]) and r["correct"] for r in z),
              harmed=sum(route!="base" and by[(r["id"],"base")]["correct"] and not r["correct"] for r in z),
              changed_reference=sum(r["reference_changed"] for r in z),new_evidence_cited=sum(r["new_evidence_cited"] for r in z)))
    transitions=[]
    for route in ROUTES:
        for pid,x in cohort.items():
            r=by[(pid,route)];b=by[(pid,"base")]
            if r["verdict"]!=b["verdict"] or r["correct"]!=b["correct"]:
                transitions.append(dict(route=route,id=pid,type=x["type"],sid=x["sid"],author=x["author"],GT=x["GT"],
                  claim=x["claim"],base=b["verdict"],new=r["verdict"],base_correct=b["correct"],new_correct=r["correct"],
                  selected_pids=r["selected_pids"],added_chars=r["added_chars"],new_evidence_cited=r["new_evidence_cited"],reason=r["reason"]))
    rescue_sets={route:sorted(r["id"] for r in pred if r["route"]==route and not by[(r["id"],"base")]["correct"] and r["correct"]) for route in ROUTES}
    harm_sets={route:sorted(r["id"] for r in pred if r["route"]==route and by[(r["id"],"base")]["correct"] and not r["correct"]) for route in ROUTES}
    # Same-input repeat stability.
    reps=[]
    for pid in read(OUT/"freeze.json")["repeat_ids"]:
        rid="046_repeat_"+__import__("hashlib").sha256(pid.encode()).hexdigest()[:24];p=term[rid]["parsed"]
        reps.append(dict(id=pid,GT=cohort[pid]["GT"],base=cohort[pid]["base_verdict"],repeat=p.get("verdict"),
          changed=p.get("verdict")!=cohort[pid]["base_verdict"]))
    # R1/R3/R5 factor comparison.
    factor=[]
    for pid in cohort:
        factor.append(dict(id=pid,GT=cohort[pid]["GT"],R1=by[(pid,"R1")]["verdict"],R3=by[(pid,"R3")]["verdict"],R5=by[(pid,"R5")]["verdict"],
          R1_R3_diff=by[(pid,"R1")]["verdict"]!=by[(pid,"R3")]["verdict"],R1_R5_diff=by[(pid,"R1")]["verdict"]!=by[(pid,"R5")]["verdict"]))
    cost=sum(a["cost"] for a in attempts)
    result=dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      routes=summary,groups=groups,rescue_sets=rescue_sets,harm_sets=harm_sets,repeats=reps,
      factor=dict(R1_R3_label_differences=sum(x["R1_R3_diff"] for x in factor),R1_R5_label_differences=sum(x["R1_R5_diff"] for x in factor)),
      transitions=transitions,cost_cny=cost,
      api=dict(attempts=len(attempts),http200=sum(a["http_status"]==200 for a in attempts),by_stage=dict(Counter(a["stage"] for a in attempts)),by_model=dict(Counter(a["model_key"] for a in attempts))))
    put(OUT/"analysis_summary.json",result);csvwrite(OUT/"predictions.csv",pred);csvwrite(OUT/"route_summary.csv",summary)
    csvwrite(OUT/"group_summary.csv",groups);csvwrite(OUT/"transitions.csv",transitions);csvwrite(OUT/"factor_R1_R3_R5.csv",factor)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
