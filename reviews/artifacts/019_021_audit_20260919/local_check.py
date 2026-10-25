from pathlib import Path
import json,hashlib,socket,os,time,importlib.metadata as md,sys
root=Path('D:/Research-VeriFact');out=Path(r'C:/Users/13359/AppData/Local/Temp/verifact019_021_audit_kke5ih2d')
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('audit offline'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
weights={}
for name,file,digest in [('bge-m3','pytorch_model.bin','b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38'),('bge-reranker-v2-m3','model.safetensors','d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286')]:
 weights[name]=sha(root/'.local_models/021'/name/file);assert weights[name]==digest
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained(str(root/'.local_models/021/bge-reranker-v2-m3'),local_files_only=True)
prep=root/'outputs/020_lambda2_patient_validation/new10/preparation_002';q={x['proposition_id']:x['text'] for x in jl(prep/'inputs.jsonl')};ps={x['passage_id']:x['search_text'] for x in jl(prep/'corpus.jsonl')}
pairs=jl(root/'outputs/021_bge_localization/rerank_pair_ids_fp32.jsonl')
maxlen=0;count=0
for r in pairs:
 enc=tok([q[r['proposition_id']]]*len(r['score_ids']),[ps[p] for p in r['score_ids']],padding=False,truncation=False,return_length=True)
 maxlen=max(maxlen,max(enc['length']));count+=len(enc['length'])
assert count==49246 and maxlen==319
result=dict(weight_sha256=weights,rerank_pairs=count,max_untruncated_pair_tokens=maxlen,cutoff512_truncates=False,python=sys.version,packages={n:md.version(n) for n in ['numpy','torch','transformers','tokenizers','huggingface-hub','safetensors','sentence-transformers','PyYAML']},new_API_calls=0)
(out/'local_environment_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
