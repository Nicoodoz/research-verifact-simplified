"""Local reranker precision diagnostic on frozen candidate pairs; no GT/Judge metrics."""
import argparse, json, time
from collections import defaultdict
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import common021 as c

MAX_LENGTH=8192
BATCH=16

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tag',required=True)
    ap.add_argument('--pairs',required=True)
    ap.add_argument('--dtype',choices=('fp16','fp32'),required=True)
    a=ap.parse_args()
    if c.sha256(c.RERANK_MODEL/'model.safetensors')!=c.RERANK_LFS_SHA:
        raise ValueError('Reranker weight SHA mismatch')
    inputs={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    pairsets=c.jsonlines(c.OUT/a.pairs)
    dtype=torch.float16 if a.dtype=='fp16' else torch.float32
    tok=AutoTokenizer.from_pretrained(str(c.RERANK_MODEL),local_files_only=True)
    model=AutoModelForSequenceClassification.from_pretrained(str(c.RERANK_MODEL),dtype=dtype,local_files_only=True).to('cuda').eval()
    torch.backends.cuda.matmul.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()
    pairs=[]
    for row in pairsets:
        q=inputs[row['proposition_id']]['text']
        for passage_id in row['score_ids']:
            pairs.append((row['proposition_id'],passage_id,q,passages[passage_id]['search_text']))
    scores=defaultdict(dict); lengths=[]; started=time.time()
    for lo in range(0,len(pairs),BATCH):
        batch=pairs[lo:lo+BATCH]
        enc=tok([x[2] for x in batch],[x[3] for x in batch],padding=True,truncation=True,max_length=MAX_LENGTH,return_tensors='pt')
        lengths.extend(enc['attention_mask'].sum(1).tolist())
        enc={k:v.to('cuda') for k,v in enc.items()}
        with torch.inference_mode():
            logits=model(**enc).logits.reshape(-1).float().cpu().numpy()
        for item,score in zip(batch,logits):
            scores[item[0]][item[1]]=float(score)
        if lo%3200==0: print(f'RERANK-{a.tag} {min(lo+BATCH,len(pairs))}/{len(pairs)}',flush=True)
    out=c.OUT/f'local_rerank_scores_{a.tag}.jsonl'
    with out.open('w',encoding='utf-8',newline='\n') as f:
        for row in pairsets:
            pid=row['proposition_id']
            f.write(json.dumps({'proposition_id':pid,'scores':scores[pid]},ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    summary={'tag':a.tag,'dtype':a.dtype,'pairs':len(pairs),'batch_size':BATCH,'max_length':MAX_LENGTH,'token_length_max':int(max(lengths)),'token_length_mean':float(np.mean(lengths)),'seconds':time.time()-started,'peak_cuda_mib':torch.cuda.max_memory_allocated()/1024**2,'weights_sha256':c.RERANK_LFS_SHA}
    c.save(c.OUT/f'rerank_{a.tag}_summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
