import json,pathlib,duckdb
from sklearn.metrics import matthews_corrcoef
root=pathlib.Path(r"D:\Research-VeriFact")
cases=[json.loads(s) for s in (root/r"outputs/051_thinking_mode_validation/confirmation_cases_frozen.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
ids=[x["id"] for x in cases]
con=duckdb.connect()
con.execute("PRAGMA threads=8")
con.execute("create temp table wanted(proposition_id varchar)")
con.executemany("insert into wanted values (?)",[(x,) for x in ids])
q="""
select v.proposition_id,v.verdict
from read_parquet(?) v
join wanted w using(proposition_id)
where v.rater_alias='v1.1.0-rater-121'
"""
rows=con.execute(q,[str(root/r"data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet")]).fetchall()
con.close()
pred=dict(rows)
assert len(pred)==96,(len(rows),len(pred),set(ids)-set(pred))
gt={x["id"]:x["GT"] for x in cases}
labels=["Supported","Not Supported","Not Addressed"]
y=[gt[i] for i in ids];p=[pred[i] for i in ids]
res={
 "n":len(ids),
 "correct":sum(a==b for a,b in zip(y,p)),
 "PA":sum(a==b for a,b in zip(y,p))/len(y),
 "MCC":float(matthews_corrcoef(y,p)),
 "false_S":sum(a!="Supported" and b=="Supported" for a,b in zip(y,p)),
 "recall":{lab:sum(a==b==lab for a,b in zip(y,p))/sum(a==lab for a in y) for lab in labels}
}
out=root/r"outputs/051_thinking_mode_validation/original_verifact_same96.json"
out.write_text(json.dumps(res,indent=2)+"\n",encoding="utf-8")
print(json.dumps(res,indent=2),flush=True)
