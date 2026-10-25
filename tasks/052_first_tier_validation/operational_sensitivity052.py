"""Exploratory deployment fallback sensitivity: invalid T-S -> frozen U2. No API or tuning."""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from verifact_research.evaluation import evaluate,paired_compare
OUT=ROOT/"outputs/052_first_tier_validation"
LABELS=("Supported","Not Supported","Not Addressed")

def main():
    rows=list(csv.DictReader((OUT/"predictions.csv").open(encoding="utf-8")))
    cohort=[dict(proposition_id=r["id"],subject_id=r["sid"],human_gt=r["GT"]) for r in rows]
    methods={}
    for name in ("U2","GateA_patient_out","O_Verifact","NV","TV"):
        methods[name]={r["id"]:r[name] for r in rows if r[name] in LABELS}
    methods["TS_U2_fb_U2"]={r["id"]:(r["TS_U2"] if r["TS_U2"] in LABELS else r["U2"]) for r in rows}
    summary=[];pairs=[]
    for name,m in methods.items():
        pp=[dict(proposition_id=r["id"],verdict=m[r["id"]]) for r in rows if r["id"] in m]
        ev=evaluate(cohort,pp,profile="research_patient",missing="available",iterations=1000)
        summary.append(dict(method=name,n=len(rows),valid_n=len(pp),correct=sum(m.get(r["id"])==r["GT"] for r in rows),
          PA=ev["percent_agreement"],MCC=ev["mcc"],AC1=ev["gwet_ac1"],
          false_S=sum(r["GT"]!="Supported" and m.get(r["id"])=="Supported" for r in rows),
          S_recall=ev["per_class"]["Supported"]["recall"],NS_recall=ev["per_class"]["Not Supported"]["recall"],
          NA_recall=ev["per_class"]["Not Addressed"]["recall"]))
    cand=methods["TS_U2_fb_U2"]
    for b in ("U2","GateA_patient_out","O_Verifact","NV","TV"):
        common=[r for r in rows if r["id"] in cand and r["id"] in methods[b]]
        sub=[dict(proposition_id=r["id"],subject_id=r["sid"],human_gt=r["GT"]) for r in common]
        ap=[dict(proposition_id=r["id"],verdict=cand[r["id"]]) for r in common]
        bp=[dict(proposition_id=r["id"],verdict=methods[b][r["id"]]) for r in common]
        pc=paired_compare(sub,bp,ap,iterations=1000)
        rescue=sum(cand[r["id"]]==r["GT"] and methods[b][r["id"]]!=r["GT"] for r in common)
        harm=sum(methods[b][r["id"]]==r["GT"] and cand[r["id"]]!=r["GT"] for r in common)
        pairs.append(dict(candidate="TS_U2_fb_U2",baseline=b,n=len(common),rescue=rescue,harm=harm,net=rescue-harm,
          delta_PA=pc["metrics"]["percent_agreement"]["delta"],PA_ci95=pc["metrics"]["percent_agreement"]["ci95"],
          delta_MCC=pc["metrics"]["mcc"]["delta"],MCC_ci95=pc["metrics"]["mcc"]["ci95"],
          delta_AC1=pc["metrics"]["gwet_ac1"]["delta"],AC1_ci95=pc["metrics"]["gwet_ac1"]["ci95"],
          false_S_delta=sum(r["GT"]!="Supported" and cand[r["id"]]=="Supported" for r in common)-
                        sum(r["GT"]!="Supported" and methods[b][r["id"]]=="Supported" for r in common)))
    out=dict(note="post-hoc operational sensitivity only; no 052 parameter changed; fallback is invalid T-S to frozen concurrent U2",
      invalid_TS=sum(r["TS_U2"] not in LABELS for r in rows),summary=summary,comparisons=pairs)
    (OUT/"operational_sensitivity.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
