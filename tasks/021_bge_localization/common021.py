"""Shared paths and immutable bindings for task 021."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/021_bge_localization'
O20=ROOT/'outputs/020_lambda2_patient_validation'
PREP20=O20/'new10/preparation_002'
CAN20=O20/'new10/candidates_001'
BASE20=O20/'new10/base_preparation_001'
MODEL_ROOT=ROOT/'.local_models/021'
EMBED_MODEL=MODEL_ROOT/'bge-m3'
RERANK_MODEL=MODEL_ROOT/'bge-reranker-v2-m3'
EMBED_LFS_SHA='b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38'
RERANK_LFS_SHA='d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def jsonlines(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()
def save(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
