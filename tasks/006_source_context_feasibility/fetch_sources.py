"""Download only public primary papers/code metadata; no clinical data or credentials."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/sources/006_source_context_feasibility"
OUT.mkdir(parents=True,exist_ok=True)
sources={
    "DnDScore_EMNLP2025.pdf":"https://aclanthology.org/2025.emnlp-main.1205.pdf",
    "Molecular_Facts_EMNLP2024.pdf":"https://aclanthology.org/2024.findings-emnlp.215.pdf",
    "verifact_tree_f115d36.json":"https://api.github.com/repos/philipchung/verifact/git/trees/f115d36cb65fa2073fce0a10df56bb37f4cbcd50?recursive=1",
}
records=[]
for name,url in sources.items():
    path=OUT/name
    if not path.exists():
        request=urllib.request.Request(url,headers={"User-Agent":"Research-VeriFact source review"})
        with urllib.request.urlopen(request,timeout=60) as r:
            raw=r.read()
        with path.open("xb") as f:
            f.write(raw)
    raw=path.read_bytes()
    records.append(dict(path=name,url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
manifest=OUT/"source_manifest.json"
if not manifest.exists():
    with manifest.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(dict(fetched_date="2026-09-14",sources=records),f,ensure_ascii=False,indent=2)
        f.write("\n")
print(json.dumps(records))
