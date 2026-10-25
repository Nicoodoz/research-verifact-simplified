"""Read-only verification of 040 decision."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/040_route_decision"
SRC=ROOT/"outputs/039_full_ehr_attribution/analysis_001/attribution_cases.csv"

def main():
    d=json.loads((OUT/"decision.json").read_text(encoding="utf-8"))
    df=pd.read_csv(SRC,keep_default_na=False);R=df[(df.flip_type=="R")&(df.attribution!="U_invalid_audit")]
    ct=R.attribution.value_counts().to_dict()
    assert len(R)==216
    assert ct["A_C48_sufficient"]==66 and ct["B_fullEHR_search_sufficient"]==55
    assert ct["C_partial_or_conflicting"]==94 and ct["D_no_clear_support"]==1
    assert d["route"]=="mixed_uncovered_by_preregistered_dominance_rules"
    assert d["action"]=="041_report_C48_and_expanded_selective_points_no_winner"
    res={"status":"pass","checks":{"R_valid":216,"A":66,"B":55,"C":94,"D":1,
      "route":d["route"],"API_calls":0},"independent_audit":False}
    (OUT/"verification_001.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("040 verification PASS")
if __name__=="__main__":main()
