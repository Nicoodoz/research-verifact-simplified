import json,pathlib,duckdb
root=pathlib.Path(r"D:\Research-VeriFact")
cases=[json.loads(s) for s in (root/r"outputs/052_first_tier_validation/evaluation_cases.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
ids=[x["id"] for x in cases]
con=duckdb.connect();con.execute("PRAGMA threads=8");con.execute("create temp table wanted(proposition_id varchar)")
con.executemany("insert into wanted values (?)",[(x,) for x in ids])
rows=con.execute("""select v.proposition_id,v.verdict from read_parquet(?) v join wanted w using(proposition_id)
where v.rater_alias='v1.1.0-rater-121'""",[str(root/r"data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet")]).fetchall();con.close()
pred=dict(rows);assert len(pred)==len(ids),(len(pred),len(ids),set(ids)-set(pred))
out=[dict(id=i,verdict=pred[i]) for i in ids]
with (root/r"outputs/052_first_tier_validation/original_verifact_predictions.jsonl").open("x",encoding="utf-8",newline="\n") as f:
    for r in out:f.write(json.dumps(r)+"\n")
print("ORIGINAL VERIFACT",len(out),flush=True)
