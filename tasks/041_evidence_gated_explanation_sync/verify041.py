"""Read-only verification of 041 outputs."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/041_evidence_gated_explanation_sync"
P036=pd.read_csv(ROOT/"outputs/036_final_validation/analysis_001/R0/predictions.csv",keep_default_na=False)
ATTR=pd.read_csv(ROOT/"outputs/039_full_ehr_attribution/analysis_001/attribution_cases.csv",keep_default_na=False)

def main():
    df=pd.read_csv(OUT/"outputs.csv",keep_default_na=False);m=pd.read_csv(OUT/"metrics.csv")
    assert len(df)==2*len(P036)==7142
    for mode in ("C48_only","Expanded_AplusB"):
        x=df[df["mode"]==mode];assert len(x)==3571
        merged=x.merge(P036[["id","U2"]],on="id",suffixes=("_041","_036"))
        assert (merged.U2_041==merged.U2_036).all()
        sync=x[x.status=="synchronized_evidence_explanation"]
        assert (sync.U2=="Supported").all()
        assert sync.explanation.str.startswith("Evidence-grounded support:").all()
        if mode=="C48_only":assert set(sync.attribution)=={"A_C48_sufficient"}
        else:assert set(sync.attribution)<= {"A_C48_sufficient","B_fullEHR_search_sufficient"}
    mm={r["mode"]:r for _,r in m.iterrows()}
    assert int(mm["C48_only"]["flip_explained"])==83
    assert int(mm["Expanded_AplusB"]["flip_explained"])==153
    assert int(mm["C48_only"]["HW_false_justification"])==17
    assert int(mm["Expanded_AplusB"]["HW_false_justification"])==32
    assert json.loads((OUT/"status.json").read_text(encoding="utf-8"))["API_calls"]==0
    result={"status":"pass","checks":{"rows_and_label_identity":True,"rendered_trace_only":True,
      "C48_flip_explained":83,"expanded_flip_explained":153,"C48_HW_false_justification":17,
      "expanded_HW_false_justification":32,"API_calls":0},"independent_audit":False}
    (OUT/"verification_001.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("041 verification PASS")
if __name__=="__main__":main()
