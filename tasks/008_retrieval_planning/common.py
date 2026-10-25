"""Shared paths and immutable experiment settings for 008."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/008_retrieval_planning"
RAW=ROOT/"data/00_raw/verifact-bhc/1.1.0"
sys.path.insert(0,str(ROOT/"tasks/004_event_alignment_pilot"))
sys.path.insert(0,str(ROOT/"src"))
import pilot
import siliconflow as sf

METHODS=("direct","simple","planner")
EMBED_MODEL="Pro/BAAI/bge-m3"
RERANK_MODEL="Pro/BAAI/bge-reranker-v2-m3"
CHAT_MODEL="deepseek-ai/DeepSeek-V4-Flash"
PATIENTS=["84454","67117","71743","72844","93788","26858"]
PHASE_CAPS={"planner":8,"embedding_base":2,"embedding_plans":2,"rerank":8,"judge":20}
assert sum(PHASE_CAPS.values())==40


def read_json(path):
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_files(base,manifest="manifest.json",key="files"):
    value=read_json(base/manifest)
    for name,digest in value[key].items():
        pilot.require(pilot.digest_file(base/name)==digest,"Frozen artifact changed: "+name)
    return value
