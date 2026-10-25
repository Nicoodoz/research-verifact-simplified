"""Offline integrity checks for completed 054. No API access."""
from pathlib import Path
import csv,hashlib,json,math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/054_unlabeled_prior_shift"
TASK=ROOT/"tasks/054_unlabeled_prior_shift"

def readj(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name+" "+str(detail))
    run=readj(OUT/"run_summary.json");fr=readj(OUT/"freeze.json")
    prior=rows(OUT/"prior_estimation_summary.csv");cls=rows(OUT/"classification_summary.csv")
    actualp=rows(OUT/"actual_prior_estimates.csv");actualc=rows(OUT/"actual_batch_results.csv")
    diag=rows(OUT/"source_diagnostics.csv")
    ck("run_pass",run["status"]=="PASS");ck("zero_api",run["API_calls"]==0)
    ck("pool_sizes",run["pools"]=={"052":236,"053":237},run["pools"])
    ck("invalid_ts",fr["invalid_TS"]=={"052":4,"053":3},fr["invalid_TS"])
    ck("protocol_hash",fr["protocol_sha256"]==sha(TASK/"protocol.md"))
    ck("prior_rows",len(prior)==2*6*4*2,len(prior))
    ck("classification_rows",len(cls)==2*6*4*7,len(cls))
    ck("actual_prior_rows",len(actualp)==8,len(actualp));ck("actual_class_rows",len(actualc)==14,len(actualc))
    ck("diagnostics_two",len(diag)==2)
    ck("condition_finite",all(math.isfinite(float(x["condition_number"])) for x in diag))
    # Under the source-prior scenario, Oracle PriorG must be identical to Frozen PriorG.
    for target in ("052","053"):
        for n in ("60","120","240","480"):
            z=[x for x in cls if x["target"]==target and x["scenario"]=="source" and x["batch_n"]==n]
            d={x["method"]:x for x in z}
            for met in ("PA_mean","MCC_mean","false_S_mean","S_recall_mean","NS_recall_mean","NA_recall_mean"):
                ck(f"source_oracle_equal_{target}_{n}_{met}",abs(float(d["FrozenPriorG"][met])-float(d["OraclePriorG"][met]))<1e-12)
    # Real 052/053 batches: BBSE prior estimation should be numerically bound to the saved results.
    for target,expected in {"052":0.031194862392620912,"053":0.022760029094013312}.items():
        z=next(x for x in actualp if x["target"]==target and x["estimator"]=="BBSE_unlabeled")
        ck("actual_bbse_"+target,abs(float(z["L1"])-expected)<1e-12,float(z["L1"]))
    # Canonical code must be offline and must not reference credential/API runner names.
    code="\n".join((TASK/f).read_text(encoding="utf-8-sig") for f in ("extract052.py","extract053.py","simulate054.py"))
    ck("offline_code","AliyunClient" not in code and ".env.aliyun" not in code and "DirectClient" not in code)
    result=dict(status="PASS",checks=checks,API_calls=0,
      hashes={str(p.relative_to(ROOT)):sha(p) for p in [
        TASK/"protocol.md",TASK/"extract052.py",TASK/"extract053.py",TASK/"simulate054.py",
        OUT/"freeze.json",OUT/"classification_summary.csv",OUT/"prior_estimation_summary.csv",
        OUT/"actual_batch_results.csv",OUT/"actual_prior_estimates.csv"]})
    (OUT/"verification_001.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status="PASS",checks=len(checks),API_calls=0),indent=2))
if __name__=="__main__":main()
