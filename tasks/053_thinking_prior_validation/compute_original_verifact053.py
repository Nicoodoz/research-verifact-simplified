from pathlib import Path
import duckdb,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
import common053 as c
def main():
    cases=c.lines(c.OUT/"evaluation_cases.jsonl");ids=[x["id"] for x in cases]
    con=duckdb.connect();con.execute("create temp table wanted(proposition_id varchar)");con.executemany("insert into wanted values (?)",[(x,) for x in ids])
    rows=con.execute("""select v.proposition_id,v.verdict from read_parquet(?) v join wanted w using(proposition_id) where v.rater_alias='v1.1.0-rater-121'""",
      [str(ROOT/"data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet")]).fetchall();con.close()
    pred=dict(rows);c.require(len(pred)==len(ids),"release missing")
    c.jsonl(c.OUT/"original_verifact_predictions.jsonl",[dict(id=i,verdict=pred[i]) for i in ids])
    print("original",len(pred))
if __name__=="__main__":main()
