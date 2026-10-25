"""Small local model sanity check using frozen 020 inputs only."""
import json, pathlib, sys, gc
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

ROOT=pathlib.Path(__file__).resolve().parents[2]
catalog=json.loads((ROOT/'outputs/020_lambda2_patient_validation/new10/preparation_002/embedding_catalog.json').read_text(encoding='utf-8'))
texts=list(catalog.values())[:4]
embed=ROOT/'.local_models/021/bge-m3'
rerank=ROOT/'.local_models/021/bge-reranker-v2-m3'

tok=AutoTokenizer.from_pretrained(str(embed),local_files_only=True)
model=AutoModel.from_pretrained(str(embed),torch_dtype=torch.float16,local_files_only=True).to('cuda').eval()
torch.cuda.reset_peak_memory_stats()
enc=tok(texts,padding=True,truncation=True,max_length=8192,return_tensors='pt')
enc={k:v.to('cuda') for k,v in enc.items()}
with torch.inference_mode():
    v=F.normalize(model(**enc).last_hidden_state[:,0].float(),p=2,dim=1)
print(json.dumps({'embedding_shape':list(v.shape),'finite':bool(torch.isfinite(v).all()),'norms':[float(x) for x in v.norm(dim=1).cpu()],'peak_mib':torch.cuda.max_memory_allocated()/1024**2},ensure_ascii=False),flush=True)
del model,enc,v; gc.collect(); torch.cuda.empty_cache()

inputs=[json.loads(x) for x in (ROOT/'outputs/020_lambda2_patient_validation/new10/candidates_001/jobs.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
job=inputs[0]
pairs=[[job['body']['query'],x] for x in job['body']['documents'][:4]]
tok=AutoTokenizer.from_pretrained(str(rerank),local_files_only=True)
model=AutoModelForSequenceClassification.from_pretrained(str(rerank),torch_dtype=torch.float16,local_files_only=True).to('cuda').eval()
torch.cuda.reset_peak_memory_stats()
enc=tok([x[0] for x in pairs],[x[1] for x in pairs],padding=True,truncation=True,max_length=8192,return_tensors='pt')
enc={k:v.to('cuda') for k,v in enc.items()}
with torch.inference_mode():
    logits=model(**enc).logits.reshape(-1).float()
print(json.dumps({'rerank_shape':list(logits.shape),'finite':bool(torch.isfinite(logits).all()),'scores':[float(x) for x in logits.cpu()],'peak_mib':torch.cuda.max_memory_allocated()/1024**2},ensure_ascii=False),flush=True)
