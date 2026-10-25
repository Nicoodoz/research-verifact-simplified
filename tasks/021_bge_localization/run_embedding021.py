"""Local BGE-M3 dense inference on the exact 020 embedding catalog."""
from pathlib import Path
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
    if c.sha256(weight)!=c.EMBED_LFS_SHA:
        raise ValueError('BGE-M3 weight SHA-256 mismatch')
    ids=c.read(c.CAN20/'embedding_ids.json')
    catalog=c.read(c.PREP20/'embedding_catalog.json')
    if set(ids)!=set(catalog) or len(ids)!=2057:
        raise ValueError('020 embedding catalog binding mismatch')
    tokenizer=AutoTokenizer.from_pretrained(str(c.EMBED_MODEL),local_files_only=True)
    model=AutoModel.from_pretrained(
        str(c.EMBED_MODEL),torch_dtype=torch.float16,local_files_only=True
    ).to('cuda').eval()
    torch.backends.cuda.matmul.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()

    texts=[catalog[k] for k in ids]
    vectors=[]; token_lengths=[]; started=time.time()
    for lo in range(0,len(texts),BATCH):
        batch=texts[lo:lo+BATCH]
        encoded=tokenizer(
            batch,padding=True,truncation=True,max_length=MAX_LENGTH,
            return_tensors='pt',return_attention_mask=True
        )
        token_lengths.extend(encoded['attention_mask'].sum(1).tolist())
        encoded={k:v.to('cuda') for k,v in encoded.items()}
        with torch.inference_mode():
            out=model(**encoded).last_hidden_state[:,0]
            out=F.normalize(out.float(),p=2,dim=1)
        vectors.append(out.cpu().numpy().astype(np.float32))
        if lo%160==0:
            print(f'EMBED {min(lo+BATCH,len(texts))}/{len(texts)}',flush=True)
    array=np.concatenate(vectors,axis=0)
    if array.shape!=(2057,1024) or not np.isfinite(array).all():
        raise ValueError('Unexpected local embedding output')

    c.OUT.mkdir(parents=True,exist_ok=True)
    np.save(c.OUT/'local_vectors_fp16.npy',array,allow_pickle=False)
    (c.OUT/'local_embedding_ids.json').write_text(
        json.dumps(ids,ensure_ascii=False)+'\n',encoding='utf-8'
    )
    summary={
        'model':'BAAI/bge-m3',
        'revision':'5617a9f61b028005a4858fdac845db406aefb181',
        'weights_sha256':c.EMBED_LFS_SHA,
        'dtype':'float16_weights_float32_normalized_output',
        'pooling':'CLS',
        'normalize':True,
        'batch_size':BATCH,
        'max_length':MAX_LENGTH,
        'texts':len(texts),
        'dimension':array.shape[1],
        'token_length_max':int(max(token_lengths)),
        'token_length_mean':float(np.mean(token_lengths)),
        'seconds':time.time()-started,
        'peak_cuda_mib':torch.cuda.max_memory_allocated()/1024**2,
    }
    c.save(c.OUT/'embedding_local_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
