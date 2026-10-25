"""Local BGE reranker v2 m3 on frozen API/local candidate pairs."""
import json, time
from collections import defaultdict
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import common021 as c

BATCH=8
MAX_LENGTH=8192

def main():
    weight=c.RERANK_MODEL/'model.safetensors'
    if c.sha256(weight)!=c.RERANK_LFS_SHA:
        raise ValueError('Reranker weight SHA-256 mismatch')
    inputs={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    pairsets=c.jsonlines(c.OUT/'rerank_pair_ids.jsonl')
    tokenizer=AutoTokenizer.from_pretrained(str(c.RERANK_MODEL),local_files_only=True)
    model=AutoModelForSequenceClassification.from_pretrained(
        str(c.RERANK_MODEL),torch_dtype=torch.float16,local_files_only=True
    ).to('cuda').eval()
    torch.backends.cuda.matmul.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()

    pairs=[]
    for row in pairsets:
        q=inputs[row['proposition_id']]['text']
        for passage_id in row['score_ids']:
            pairs.append((row['proposition_id'],passage_id,q,passages[passage_id]['search_text']))
    scores=defaultdict(dict); token_lengths=[]; started=time.time()
    for lo in range(0,len(pairs),BATCH):
        batch=pairs[lo:lo+BATCH]
        enc=tokenizer(
            [x[2] for x in batch],[x[3] for x in batch],
            padding=True,truncation=True,max_length=MAX_LENGTH,
            return_tensors='pt'
        )
        token_lengths.extend(enc['attention_mask'].sum(1).tolist())
        enc={k:v.to('cuda') for k,v in enc.items()}
        with torch.inference_mode():
            logits=model(**enc).logits.reshape(-1).float().cpu().numpy()
        for item,score in zip(batch,logits):
            scores[item[0]][item[1]]=float(score)
        if lo%1600==0:
            print(f'RERANK {min(lo+BATCH,len(pairs))}/{len(pairs)}',flush=True)

    out=c.OUT/'local_rerank_scores.jsonl'
    with out.open('w',encoding='utf-8',newline='\n') as f:
        for row in pairsets:
            pid=row['proposition_id']
            f.write(json.dumps({
                'proposition_id':pid,'scores':scores[pid]
            },ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    summary={
        'model':'BAAI/bge-reranker-v2-m3',
        'revision':'953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e',
        'weights_sha256':c.RERANK_LFS_SHA,
        'dtype':'float16_weights_float32_logits',
        'batch_size':BATCH,'max_length':MAX_LENGTH,
        'pairs':len(pairs),
        'token_length_max':int(max(token_lengths)),
        'token_length_mean':float(np.mean(token_lengths)),
        'seconds':time.time()-started,
        'peak_cuda_mib':torch.cuda.max_memory_allocated()/1024**2,
    }
    c.save(c.OUT/'rerank_local_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
