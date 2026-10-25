"""FP32 precision diagnostic allowed by protocol_001; no GT/Judge metrics."""
import json, time
import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer
import common021 as c

BATCH=8
MAX_LENGTH=8192

def main():
    weight=c.EMBED_MODEL/'pytorch_model.bin'
    if c.sha256(weight)!=c.EMBED_LFS_SHA: raise ValueError('weight sha')
    ids=c.read(c.CAN20/'embedding_ids.json'); catalog=c.read(c.PREP20/'embedding_catalog.json')
    tok=AutoTokenizer.from_pretrained(str(c.EMBED_MODEL),local_files_only=True)
    model=AutoModel.from_pretrained(str(c.EMBED_MODEL),dtype=torch.float32,local_files_only=True).to('cuda').eval()
    torch.backends.cuda.matmul.allow_tf32=False
    torch.cuda.reset_peak_memory_stats(); vec=[]; started=time.time()
    for lo in range(0,len(ids),BATCH):
        texts=[catalog[k] for k in ids[lo:lo+BATCH]]
        enc=tok(texts,padding=True,truncation=True,max_length=MAX_LENGTH,return_tensors='pt')
        enc={k:v.to('cuda') for k,v in enc.items()}
        with torch.inference_mode():
            out=F.normalize(model(**enc).last_hidden_state[:,0],p=2,dim=1)
        vec.append(out.cpu().numpy().astype(np.float32))
        if lo%320==0: print(f'FP32 {min(lo+BATCH,len(ids))}/{len(ids)}',flush=True)
    arr=np.concatenate(vec)
    np.save(c.OUT/'local_vectors_fp32.npy',arr,allow_pickle=False)
    c.save(c.OUT/'embedding_fp32_summary.json',{
        'texts':len(ids),'dtype':'float32','seconds':time.time()-started,
        'peak_cuda_mib':torch.cuda.max_memory_allocated()/1024**2,
        'weights_sha256':c.EMBED_LFS_SHA
    })
    print(json.dumps(c.read(c.OUT/'embedding_fp32_summary.json')),flush=True)
if __name__=='__main__': main()
