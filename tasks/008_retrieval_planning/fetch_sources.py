"""Save public primary sources for 008; never sends clinical data or credentials."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import urllib.request
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/sources/008_retrieval_planning"
SOURCES={
    "query2doc.pdf":"https://aclanthology.org/2023.emnlp-main.585.pdf",
    "query_rewriting.pdf":"https://aclanthology.org/2023.emnlp-main.322.pdf",
    "rarr.pdf":"https://aclanthology.org/2023.acl-long.910.pdf",
    "pricing.html":"https://siliconflow.cn/pricing",
    "embedding_api.html":"https://api-docs.siliconflow.cn/docs/api/embeddings-post",
    "rerank_api.html":"https://api-docs.siliconflow.cn/docs/api/rerank-post",
    "release_notes.html":"https://docs.siliconflow.cn/docs/release-notes/overview",
    "bge_m3_card.md":"https://huggingface.co/BAAI/bge-m3/raw/main/README.md"
}
if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for name,url in SOURCES.items():
        path=OUT/name
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Research-VeriFact source reading"}),timeout=45) as response:
                raw=response.read()
            path.write_bytes(raw)
        records.append(dict(file=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if name.endswith(".pdf"):
            reader=PdfReader(path)
            pages=[dict(page=i+1,text=page.extract_text()) for i,page in enumerate(reader.pages)]
            (OUT/(path.stem+"_pages.json")).write_text(json.dumps(pages,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    target=OUT/"manifest.json"
    with target.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(dict(fetched_utc=datetime.now(timezone.utc).isoformat(),sources=records),f,ensure_ascii=False,indent=2)
        f.write("\n")
    print("Public sources saved:",len(records))
