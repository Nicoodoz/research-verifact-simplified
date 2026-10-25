"""040 zero-API route decision from frozen 039 attribution."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/040_route_decision"
SRC=ROOT/"outputs/039_full_ehr_attribution/analysis_001"

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if any(OUT.iterdir()): raise RuntimeError("040 output not empty")
    df=pd.read_csv(SRC/"attribution_cases.csv",keep_default_na=False)
    R=df[df.flip_type=="R"];H=df[df.flip_type=="H"];W=df[df.flip_type=="W"]
    validR=R[R.attribution!="U_invalid_audit"]
    counts=validR.attribution.value_counts().to_dict()
    A=counts.get("A_C48_sufficient",0);B=counts.get("B_fullEHR_search_sufficient",0)
    C=counts.get("C_partial_or_conflicting",0);D=counts.get("D_no_clear_support",0);n=len(validR)
    a=A/n;ab=(A+B)/n;b=B/n
    if a>=.5:
        route="decision_boundary_dominant";action="041_C48_only_primary"
    elif ab>=.5 and B>A:
        route="retrieval_plus_decision_retrieval_dominant";action="041_retrieval_augmented_primary"
    elif ab<.5:
        route="evidence_scope_mismatch_dominant";action="041_selective_abstention_only"
    else:
        route="mixed_uncovered_by_preregistered_dominance_rules";action="041_report_C48_and_expanded_selective_points_no_winner"
    hw=pd.concat([H,W])
    risk=((hw.attribution=="A_C48_sufficient")|(hw.attribution=="B_fullEHR_search_sufficient")).sum()
    result=dict(route=route,action=action,R_valid=n,A=A,B=B,C=C,D=D,A_rate=a,B_rate=b,
      AB_rate=ab,CD_rate=(C+D)/n,HW_n=len(hw),HW_evidence_supported=int(risk),
      HW_false_justification_candidate_rate=float(risk/len(hw)),
      note="No new classification parameter is fit. The preregistered rules did not explicitly cover A+B>=50% with A<50% and B<=A; this is reported as mixed rather than forcing a winner.")
    (OUT/"decision.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
