"""049 stage0: zero-API rule diagnostics on frozen 048 screen artifacts."""
from pathlib import Path
from collections import Counter
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/049_evidence_decision_utilization"
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c48
import run048

def contradicted_with_valid_quote(parsed):
    for row in parsed.get("requirements",[]):
        if row.get("relation")!="contradicted":continue
        evs=row.get("evidence",[])
        if any(bool(e.get("valid")) for e in evs):return True
    return False

def main():
    rows=list(csv.DictReader((c48.OUT/"screen_predictions.csv").open(encoding="utf-8")))
    b={r["id"]:r for r in rows if r["condition"]=="B"}
    jobs={(j["id"],j["condition"]):j for j in c48.lines(c48.OUT/"screen_stage2_jobs.jsonl")}
    _,term=run048.state()
    out=[]
    for pid,base in b.items():
        job=jobs[(pid,"K")];p=term[job["request_id"]]["parsed"]
        gt=base["GT"];raw=base["raw"];u2=base["U2"]
        veto=contradicted_with_valid_quote(p)
        A=raw if (u2=="Supported" and veto) else u2
        if p.get("status")=="valid" and p.get("citations_valid") is True and p.get("audit_label") in ("Supported","Not Supported","Not Addressed"):
            B=p["audit_label"]
        else:B=u2
        hard=u2 if p.get("strict_supported") and p.get("citations_valid") is True else raw
        out.append(dict(id=pid,sid=base["sid"],GT=gt,raw=raw,U2=u2,
          audit_label=p.get("audit_label"),coverage=p.get("coverage"),
          citations_valid=p.get("citations_valid"),veto=veto,A=A,B=B,Hard=hard))
    summary=[]
    for key in ("U2","A","B","Hard"):
        rr=[r for r in out];pred=[r[key] for r in rr]
        summary.append(dict(method=key,n=len(rr),correct=sum(p==r["GT"] for p,r in zip(pred,rr)),
          false_S=sum(r["GT"]!="Supported" and p=="Supported" for p,r in zip(pred,rr)),
          changed=sum(p!=r["U2"] for p,r in zip(pred,rr))))
    OUT.mkdir(parents=True,exist_ok=True)
    c48.csvwrite(OUT/"stage0_cases.csv",out)
    c48.csvwrite(OUT/"stage0_summary.csv",summary)
    c48.put(OUT/"stage0_summary.json",dict(created_utc=c48.now(),summary=summary,
      veto_cases=sum(r["veto"] for r in out),audit_labels=dict(Counter(r["audit_label"] for r in out))))
    print(json.dumps(dict(summary=summary,veto_cases=sum(r["veto"] for r in out)),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
