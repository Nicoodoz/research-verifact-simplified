"""Analyze 045 first-batch route screen. No API calls."""
from pathlib import Path
import json,math,csv,hashlib
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/045_semantic_recovery_screen";R044=ROOT/"outputs/044_incremental_evidence_recovery"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/045_semantic_recovery_screen"))
import run045
LABELS=("Supported","Not Supported","Not Addressed")
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def csvwrite(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r));p=Path(p)
    with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def u2(scores):
    return max(("Not Supported","Not Addressed","Supported"),key=lambda k:math.log(max(float(scores[k])/100,1e-6))+(2 if k=="Supported" else 0))
def hid(pid):return hashlib.sha256(pid.encode()).hexdigest()[:24]
def main():
    cohort={x["id"]:x for x in lines(OUT/"cohort.jsonl")};sel={(x["id"],x["route"]):x for x in lines(OUT/"stage2_selections.jsonl")}
    attempts,term=run045.state();base_rows=read(R044/"results_recovery_001/score_rows.json")
    br={x["id"]:x for x in base_rows if x["condition"]=="base" and x["round"]==0 and x.get("Score")}
    predictions=[];details=[]
    for pid,x in cohort.items():
        routes={}
        routes["base"]=dict(verdict=x["base_verdict"],reason=x["base_reason"],scores=br[pid]["scores"],source="044_base")
        pa=term["045_A_"+hid(pid)]["parsed"]
        routes["A"]=dict(verdict=pa.get("verdict"),reason=(pa.get("parsed") or {}).get("reason"),scores=pa.get("scores"),source="new_deepseek")
        pd=term["045_D_"+hid(pid)]["parsed"];obj=pd.get("parsed") or {}
        routes["D"]=dict(verdict=obj.get("verdict"),reason=obj.get("reason"),scores=obj.get("label_scores"),source="qwen_judge")
        sb=sel[(pid,"B")]
        if sb["reference_changed"]:
            p=term["045_Bfinal_"+hid(pid)]["parsed"];routes["B"]=dict(verdict=p.get("verdict"),reason=(p.get("parsed") or {}).get("reason"),scores=p.get("scores"),source=sb.get("choice"))
        else:routes["B"]=dict(routes["base"],source="baseline_reused_none")
        sc=sel[(pid,"C")]
        if sc["reference_changed"]:
            p=term["045_Cfinal_"+hid(pid)]["parsed"];routes["C"]=dict(verdict=p.get("verdict"),reason=(p.get("parsed") or {}).get("reason"),scores=p.get("scores"),source="feedback_bm25")
        else:routes["C"]=dict(routes["base"],source="baseline_reused_no_query_or_hit")
        for name,r in routes.items():
            pred=r["verdict"];correct=pred==x["GT"] if pred else False
            predictions.append(dict(id=pid,sid=x["sid"],author=x["author"],GT=x["GT"],base_correct=x["base_correct"],
              route=name,verdict=pred,correct=correct,U2=u2(r["scores"]) if r.get("scores") else None,
              reason=r.get("reason"),source=r.get("source")))
        details.append(dict(id=pid,claim=x["claim"],GT=x["GT"],base=x["base_verdict"],
          B_choice=sb.get("choice"),B_selector=sb.get("selector"),C_gap=sc.get("gap"),C_queries=sc.get("queries"),
          C_passages=sc.get("passage_ids"),C_added_chars=sc.get("added_chars")))
    by={(r["id"],r["route"]):r for r in predictions};routes=("A","B","C","D");summary=[]
    for route in ("base",)+routes:
        rr=[r for r in predictions if r["route"]==route]
        row=dict(route=route,n=len(rr),correct=sum(r["correct"] for r in rr),changed=sum(r["verdict"]!=by[(r["id"],"base")]["verdict"] for r in rr),
          predicted_S=sum(r["verdict"]=="Supported" for r in rr),false_S=sum(r["GT"]!="Supported" and r["verdict"]=="Supported" for r in rr),
          U2_correct=sum(r["U2"]==r["GT"] for r in rr if r["U2"]),U2_false_S=sum(r["GT"]!="Supported" and r["U2"]=="Supported" for r in rr if r["U2"]))
        if route!="base":
            row["rescued"]=sum((not by[(r["id"],"base")]["correct"]) and r["correct"] for r in rr)
            row["harmed"]=sum(by[(r["id"],"base")]["correct"] and not r["correct"] for r in rr)
            row["net"]=row["rescued"]-row["harmed"]
            row["U2_rescued"]=sum(by[(r["id"],"base")]["U2"]!=r["GT"] and r["U2"]==r["GT"] for r in rr)
            row["U2_harmed"]=sum(by[(r["id"],"base")]["U2"]==r["GT"] and r["U2"]!=r["GT"] for r in rr)
        summary.append(row)
    breakdown=[]
    for route in routes:
        for gt in LABELS:
            rr=[r for r in predictions if r["route"]==route and r["GT"]==gt]
            breakdown.append(dict(route=route,group="GT",value=gt,n=len(rr),correct=sum(r["correct"] for r in rr),
              rescued=sum(not by[(r["id"],"base")]["correct"] and r["correct"] for r in rr),harmed=sum(by[(r["id"],"base")]["correct"] and not r["correct"] for r in rr)))
        for author in ("human","llm"):
            rr=[r for r in predictions if r["route"]==route and r["author"]==author]
            breakdown.append(dict(route=route,group="author",value=author,n=len(rr),correct=sum(r["correct"] for r in rr),
              rescued=sum(not by[(r["id"],"base")]["correct"] and r["correct"] for r in rr),harmed=sum(by[(r["id"],"base")]["correct"] and not r["correct"] for r in rr)))
    # Four same-input repeats
    reps=[]
    for pid in read(OUT/"freeze.json")["repeat_ids"]:
        p=term["045_repeat_"+hid(pid)]["parsed"];v=p.get("verdict")
        reps.append(dict(id=pid,GT=cohort[pid]["GT"],base=cohort[pid]["base_verdict"],repeat=v,changed=v!=cohort[pid]["base_verdict"],
          base_correct=cohort[pid]["base_verdict"]==cohort[pid]["GT"],repeat_correct=v==cohort[pid]["GT"]))
    changed=[]
    for route in routes:
        for pid,x in cohort.items():
            r=by[(pid,route)];b=by[(pid,"base")]
            if r["verdict"]!=b["verdict"]:
                changed.append(dict(route=route,id=pid,claim=x["claim"],GT=x["GT"],author=x["author"],sid=x["sid"],
                  base=b["verdict"],new=r["verdict"],base_correct=b["correct"],new_correct=r["correct"],reason=r["reason"],
                  B_choice=sel[(pid,"B")].get("choice"),C_gap=sel[(pid,"C")].get("gap"),C_queries=sel[(pid,"C")].get("queries"),C_passages=sel[(pid,"C")].get("passage_ids")))
    cost=sum(a["cost"] for a in attempts)
    put(OUT/"analysis_summary.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      routes=summary,breakdown=breakdown,repeats=reps,changed_cases=changed,cost_cny=cost,stage2=read(OUT/"stage2_freeze.json")))
    csvwrite(OUT/"predictions.csv",predictions);csvwrite(OUT/"route_summary.csv",summary);csvwrite(OUT/"changed_cases.csv",changed);csvwrite(OUT/"breakdown.csv",breakdown)
    print(json.dumps(read(OUT/"analysis_summary.json"),ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
