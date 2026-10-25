from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import run065,common065 as c
A,T=run065.state()
jobs={x["request_id"]:x for x in c.lines(c.OUT/"stage2_jobs.jsonl")}
bad=[]
for rid,z in T.items():
    if rid not in jobs: continue
    p=z["parsed"]
    if p.get("status")!="valid":
        raw=json.loads(z["transport"]["body_text"])
        content=raw["choices"][0]["message"]["content"]
        bad.append((rid,p.get("errors"),content[:1200]))
print("bad",len(bad))
for x in bad:
    print("\nRID",x[0],"ERR",x[1],"\nCONTENT",x[2])
