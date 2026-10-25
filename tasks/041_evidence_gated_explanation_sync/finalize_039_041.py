from pathlib import Path
import hashlib,json,datetime

ROOT=Path(__file__).resolve().parents[2]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

for name in ("039_full_ehr_attribution","040_route_decision","041_evidence_gated_explanation_sync"):
    out=ROOT/"outputs"/name
    files=[p for p in out.rglob("*") if p.is_file() and "attempts" not in p.parts and p.name!="manifest.json"]
    obj={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "files":{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}}
    attempts=sorted((out/"attempts").glob("*/*.json")) if (out/"attempts").exists() else []
    if attempts:
        obj["attempt_json_count"]=len(attempts)
        obj["attempts_combined_sha256"]=hashlib.sha256("".join(sha(p) for p in attempts).encode()).hexdigest()
    (out/"manifest.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(name,"manifest",len(files),"files",len(attempts),"attempt json")
