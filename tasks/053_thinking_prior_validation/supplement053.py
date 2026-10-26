from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c,run053
sys.path.insert(0,str(ROOT/"src"))
from verifact_research.evaluation import evaluate,paired_compare

def metric(rows,pred):
    cohort=[dict(proposition_id=r["id"],subject_id=r["sid"],human_gt=r["GT"]) for r in rows]
    pp=[dict(proposition_id=r["id"],verdict=pred[r["id"]]) for r in rows]
    ev=evaluate(cohort,pp,profile="research_patient",missing="available",iterations=1000)
    out=dict(n=len(rows),correct=sum(pred[r["id"]]==r["GT"] for r in rows),PA=ev["percent_agreement"],MCC=ev["mcc"],AC1=ev["gwet_ac1"],
      false_S=sum(r["GT"]!="Supported" and pred[r["id"]]=="Supported" for r in rows))
    for lab in c.LABELS:
        den=sum(r["GT"]==lab for r in rows);out["recall_"+lab.replace(" ","_")]=sum(r["GT"]==lab and pred[r["id"]]==lab for r in rows)/den
    return out

def main():
    rows=list(csv.DictReader((c.OUT/"predictions.csv").open(encoding="utf-8")))
    _,term=run053.state()
    methods={m:{r["id"]:r[m] for r in rows} for m in ("U2","GateA","TS_U2","TS_PriorG","TS_PriorM")}
    methods["O_Verifact"]={x["id"]:x["verdict"] for x in c.lines(c.OUT/"original_verifact_predictions.jsonl")}
    methods["AuthorG"]={r["id"]:(r["TS_PriorG"] if r["author"]=="human" else r["U2"]) for r in rows}
    methods["AuthorM"]={r["id"]:(r["TS_PriorM"] if r["author"]=="human" else r["U2"]) for r in rows}
    routes=[]
    for m in ("AuthorG","AuthorM"):
        z=metric(rows,methods[m]);z["method"]=m;routes.append(z)
    comps=[]
    for a in ("AuthorG","AuthorM"):
        for b in ("U2","GateA","TS_PriorG","O_Verifact"):
            cohort=[dict(proposition_id=r["id"],subject_id=r["sid"],human_gt=r["GT"]) for r in rows]
            ap=[dict(proposition_id=r["id"],verdict=methods[a][r["id"]]) for r in rows]
            bp=[dict(proposition_id=r["id"],verdict=methods[b][r["id"]]) for r in rows]
            pc=paired_compare(cohort,bp,ap,iterations=1000)
            rescue=sum(methods[a][r["id"]]==r["GT"] and methods[b][r["id"]]!=r["GT"] for r in rows)
            harm=sum(methods[b][r["id"]]==r["GT"] and methods[a][r["id"]]!=r["GT"] for r in rows)
            comps.append(dict(candidate=a,baseline=b,rescue=rescue,harm=harm,net=rescue-harm,
              delta_PA=pc["metrics"]["percent_agreement"]["delta"],PA_ci95=pc["metrics"]["percent_agreement"]["ci95"],
              delta_MCC=pc["metrics"]["mcc"]["delta"],MCC_ci95=pc["metrics"]["mcc"]["ci95"],
              false_S_delta=sum(r["GT"]!="Supported" and methods[a][r["id"]]=="Supported" for r in rows)-
                            sum(r["GT"]!="Supported" and methods[b][r["id"]]=="Supported" for r in rows)))
    sync=[]
    for name in ("U2","GateA","TS_U2","TS_PriorG","TS_PriorM","AuthorG","AuthorM"):
        n=0
        for r in rows:
            h=c.stable("",r["id"])[:24];ns=term["053_N_S_"+h]["parsed"];ts=term["053_T_S_"+h]["parsed"]
            if name in ("U2","GateA") or (name in ("AuthorG","AuthorM") and r["author"]=="llm"):
                obj=ns.get("parsed") or {};raw=ns.get("verdict")
            else:
                obj=ts.get("parsed") or {};raw=ts.get("verdict")
                if not isinstance(obj.get("reason"),str) or not obj.get("reason").strip():
                    obj=ns.get("parsed") or {};raw=ns.get("verdict")
            n+=bool(isinstance(obj.get("reason"),str) and obj.get("reason").strip() and raw==methods[name][r["id"]])
        sync.append(dict(method=name,sync_n=n,n=len(rows),sync_rate=n/len(rows)))
    c.csvwrite(c.OUT/"exploratory_routes.csv",routes);c.csvwrite(c.OUT/"exploratory_route_comparisons.csv",comps);c.csvwrite(c.OUT/"reason_sync_corrected.csv",sync)
    c.put(c.OUT/"supplement_001.json",dict(note="offline only; no new API; author routes are exploratory performance workpoints; reason-sync corrects parser nesting bug in original summary",routes=routes,comparisons=comps,reason_sync=sync))
    print(json.dumps(dict(routes=routes,reason_sync=sync),ensure_ascii=False,indent=2))
if __name__=="__main__":main()

