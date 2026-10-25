"""041 deterministic evidence-gated explanation synchronization; zero API."""
import json,sys
from pathlib import Path
from collections import Counter
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/041_evidence_gated_explanation_sync"
P036=ROOT/"outputs/036_final_validation/analysis_001/R0/predictions.csv"
P039=ROOT/"outputs/039_full_ehr_attribution/analysis_001/attribution_cases.csv"

sys.path.insert(0,str(ROOT/"tasks/038_evidence_explanation_audit"))
import execute038
sys.path.insert(0,str(ROOT/"tasks/039_full_ehr_attribution"))
import execute039

def render_038(p):
    parts=[]
    for row in p["requirements"]:
        ev="; ".join(f"C48 ref {e['reference_id']}: \"{e['quote']}\"" for e in row["evidence"] if e["valid"])
        parts.append(f"{row.get('requirement') or row.get('claim_quote')}: {ev}")
    return "Evidence-grounded support: "+" | ".join(parts)

def render_039(p):
    parts=[]
    for row in p["requirements"]:
        ev="; ".join(f"{e['source']} {e['id']}: \"{e['quote']}\"" for e in row["evidence"] if e["valid"])
        parts.append(f"{row.get('claim_requirement')}: {ev}")
    return "Evidence-grounded support: "+" | ".join(parts)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if any(OUT.iterdir()):raise RuntimeError("041 output not empty")
    pred=pd.read_csv(P036,keep_default_na=False)
    attr=pd.read_csv(P039,keep_default_na=False);amap={r.id:r for _,r in attr.iterrows()}

    _,t38=execute038.state();trace38={}
    for rid,t in t38.items():
        j=t["job"];p=t["parsed"]
        if j["kind"]=="evidence" and j["model_key"]=="qwen" and p.get("trace_supported"):
            trace38[j["proposition_id"]]=p
    _,t39=execute039.state();trace39={}
    for rid,t in t39.items():
        j=t["job"];p=t["parsed"]
        if j["kind"]=="audit" and p.get("strict_supported"):
            trace39[j["proposition_id"]]=p

    records=[]
    for _,r in pred.iterrows():
        pid=r["id"];changed=r["U2"]!=r["Score_verdict"]
        base=dict(id=pid,sid=r["sid"],author=r["author"],GT=r["GT"],Score_verdict=r["Score_verdict"],U2=r["U2"],changed=changed)
        for mode in ("C48_only","Expanded_AplusB"):
            status="not_applicable";explanation=""
            if not changed:
                status="retain_original_pre_adjustment_explanation"
            elif r["U2"]!="Supported":
                status="abstain_changed_nonS_not_audited"
            elif pid not in amap:
                status="abstain_unassessed_finalS_mismatch"
            else:
                cat=amap[pid].attribution
                allow=cat=="A_C48_sufficient" or (mode=="Expanded_AplusB" and cat=="B_fullEHR_search_sufficient")
                if allow:
                    if cat=="A_C48_sufficient" and pid in trace38:
                        explanation=render_038(trace38[pid])
                    elif pid in trace39:
                        explanation=render_039(trace39[pid])
                    else:
                        allow=False
                status="synchronized_evidence_explanation" if allow else "explanation_abstain_evidence_mismatch"
            records.append(dict(**base,mode=mode,status=status,explanation=explanation,
                                attribution=amap[pid].attribution if pid in amap else ""))
    pd.DataFrame(records).to_csv(OUT/"outputs.csv",index=False,encoding="utf-8")
    metrics=[]
    df=pd.DataFrame(records)
    for mode in ("C48_only","Expanded_AplusB"):
        x=df[df["mode"]==mode];flips=x[(x.U2=="Supported")&(x.changed)&(x.id.isin(amap))]
        explained=flips[flips.status=="synchronized_evidence_explanation"]
        R=flips[flips.GT=="Supported"];risk=flips[flips.GT!="Supported"]
        er=explained[explained.GT=="Supported"];ehw=explained[explained.GT!="Supported"]
        finalS=x[x.U2=="Supported"];avail=finalS[finalS.status.isin(["retain_original_pre_adjustment_explanation","synchronized_evidence_explanation"])]
        changed_all=x[x.changed];changed_expl=changed_all[changed_all.status=="synchronized_evidence_explanation"]
        metrics.append(dict(mode=mode,flip_n=len(flips),flip_explained=len(explained),
          flip_explanation_coverage=len(explained)/len(flips),
          R_n=len(R),R_explained=len(er),R_explanation_coverage=len(er)/len(R),
          HW_n=len(risk),HW_false_justification=len(ehw),HW_false_justification_rate=len(ehw)/len(risk),
          explained_flip_GT_precision=len(er)/len(explained) if len(explained) else None,
          finalS_n=len(finalS),finalS_structural_explanation_available=len(avail),
          finalS_structural_coverage=len(avail)/len(finalS),
          all_changed_n=len(changed_all),all_changed_synchronized=len(changed_expl),
          all_changed_sync_coverage=len(changed_expl)/len(changed_all)))
    pd.DataFrame(metrics).to_csv(OUT/"metrics.csv",index=False)
    print(pd.DataFrame(metrics).to_string(index=False))
    # Sanity: every rendered explanation is built only from an already strict-supported trace.
    for r in records:
        if r["status"]=="synchronized_evidence_explanation":
            assert r["explanation"].startswith("Evidence-grounded support:")
            assert "\"" in r["explanation"]
    (OUT/"status.json").write_text(json.dumps(dict(status="complete",API_calls=0,posthoc=True,
      note="No label changes; deterministic rendering from strict trace only; no winner selected between workpoints."),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
