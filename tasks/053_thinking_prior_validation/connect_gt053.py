from pathlib import Path
import csv,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c
def main():
    blind=c.lines(c.OUT/"sample_blind.jsonl")
    cm={r["proposition_id"]:r for r in csv.DictReader((ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv").open(encoding="utf-8-sig"))}
    rows=[]
    for x in blind:
        r=cm[x["id"]];c.require(r["human_gt"] in c.LABELS,"bad GT")
        rows.append(dict(**x,GT=r["human_gt"]))
    c.jsonl(c.OUT/"evaluation_cases.jsonl",rows)
    print("GT connected",len(rows))
if __name__=="__main__":main()
