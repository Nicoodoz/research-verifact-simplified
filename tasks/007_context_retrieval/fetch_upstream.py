"""Fetch fixed public source code only; never sends clinical text or credentials."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/sources/007_context_retrieval"
REVISION = "f115d36cb65fa2073fce0a10df56bb37f4cbcd50"
PATHS = ["LICENSE", "packages/llm_judge/src/llm_judge/reference_context.py",
    "packages/llm_judge/src/llm_judge/judge_subject.py", "packages/llm_judge/src/llm_judge/judge.py",
    "packages/rag/src/rag/node_parser/single_sentence_parser.py",
    "packages/rag/src/rag/embedding/m3_embedding.py", "packages/rag/src/rag/postprocessor/m3_reranker.py",
    "packages/rag/src/rag/vector_stores/qdrant.py", "scripts/dataset/decompose_text.py",
    "services/embed/README.md", "services/rerank/README.md"]
if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "manifest.json").exists()
    records = []
    for name in PATHS:
        path = OUT / name
        url = "https://raw.githubusercontent.com/philipchung/verifact/" + REVISION + "/" + name
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Research-VeriFact"}), timeout=40) as response:
                content = response.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(content)
        records.append(dict(path=name, url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT / "manifest.json").write_text(json.dumps(dict(revision=REVISION, downloaded_utc=datetime.now(timezone.utc).isoformat(),
        files=records), indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Public source files saved:", len(records))
