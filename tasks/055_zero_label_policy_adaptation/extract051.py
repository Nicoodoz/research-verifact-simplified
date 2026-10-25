from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
import run051,common051 as c
VALID=c.VALID
def main():
    cases={}
    for f in ("screen_cases.jsonl","confirmation_cases_frozen.jsonl"):
        for x in c.lines(ROOT/"outputs/051_thinking_mode_validation"/f):cases[x["id"]]=x
    _,term=run051.state();rows=[];invalid=[]
    for jf in ("screen_jobs.jsonl","confirmation_jobs.jsonl"):
        for j in c.lines(ROOT/"outputs/051_thinking_mode_validation"/jf):
            if j.get("condition")!="T-S" or j.get("kind")!="judge":continue
            p=term[j["request_id"]]["parsed"];x=cases[j["id"]]
            if p.get("status") not in VALID or p.get("scores") is None:
                invalid.append(dict(id=j["id"],sid=x["sid"],request_id=j["request_id"],status=p.get("status")));continue
            rows.append(dict(pool="051",id=j["id"],sid=x["sid"],author=x["author"],GT=x["GT"],
              s=p["scores"]["Supported"],ns=p["scores"]["Not Supported"],na=p["scores"]["Not Addressed"]))
    seen={}
    for r in rows:seen[r["id"]]=r
    rows=list(seen.values())
    with (OUT/"compact_051_scores.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    (OUT/"compact_051_meta.json").write_text(json.dumps(dict(valid=len(rows),invalid=invalid),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("051 valid",len(rows),"GT",{k:sum(r["GT"]==k for r in rows) for k in ("Supported","Not Supported","Not Addressed")},"invalid",len(invalid))
if __name__=="__main__":main()
