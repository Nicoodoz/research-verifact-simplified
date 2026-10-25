"""Additional primary-paper check; public downloads only, no model services."""
from datetime import datetime,timezone
import urllib.request
from pypdf import PdfReader
import common as c

if __name__=="__main__":
    base=c.ROOT/"docs/sources/008_retrieval_planning"
    entries={"medical_stepwise":"https://aclanthology.org/2025.naacl-short.68.pdf",
        "fire":"https://aclanthology.org/2025.findings-naacl.158.pdf"}
    records={}
    for name,url in entries.items():
        path=base/(name+".pdf")
        assert not path.exists()
        with urllib.request.urlopen(url,timeout=60) as response:
            content=response.read()
        with path.open("xb") as f:
            f.write(content)
        reader=PdfReader(path)
        c.pilot.write_json(base/(name+"_pages.json"),[{"page":i+1,"text":page.extract_text()} for i,page in enumerate(reader.pages)])
        records[name]=dict(url=url,sha256=c.pilot.digest_file(path),pages=len(reader.pages))
    c.pilot.write_json(base/"additional_manifest.json",dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),sources=records))
    print(c.pilot.canonical(records))
