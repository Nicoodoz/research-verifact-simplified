"""Checkpointed local reranker over frozen pair sets. No GT/Judge metrics."""
import argparse, json, os, time
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import common021 as c

def load_completed(path):
    out={}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                row=json.loads(line); out[row['proposition_id']]=row
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tag',required=True); ap.add_argument('--pairs',required=True)
    ap.add_argument('--dtype',choices=('fp16','fp32'),required=True)
    ap.add_argument('--batch',type=int,default=32); ap.add_argument('--max-length',type=int,default=512)
    a=ap.parse_args()
    if c.sha256(c.RERANK_MODEL/'model.safetensors')!=c.RERANK_LFS_SHA: raise ValueError('weight sha')
    inputs={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    pairsets=c.jsonlines(c.OUT/a.pairs)
    out=c.OUT/f'local_rerank_scores_{a.tag}.jsonl'
    done=load_completed(out)
    dtype=torch.float16 if a.dtype=='fp16' else torch.float32
    tok=AutoTokenizer.from_pretrained(str(c.RERANK_MODEL),local_files_only=True)
    model=AutoModelForSequenceClassification.from_pretrained(str(c.RERANK_MODEL),dtype=dtype,local_files_only=True).to('cuda').eval()
    torch.backends.cuda.matmul.allow_tf32=False; torch.cuda.reset_peak_memory_stats()
    started=time.time(); new=0; token_max=0; token_sum=0; token_n=0
    mode='a' if out.exists() else 'w'
    with out.open(mode,encoding='utf-8',newline='\n') as f:
        for idx,row in enumerate(pairsets,1):
            pid=row['proposition_id']
            if pid in done: continue
            q=inputs[pid]['text']; ids=row['score_ids']; scores={}
            for lo in range(0,len(ids),a.batch):
                sub=ids[lo:lo+a.batch]
                enc=tok([q]*len(sub),[passages[x]['search_text'] for x in sub],padding=True,truncation=True,max_length=a.max_length,return_tensors='pt')
                lengths=enc['attention_mask'].sum(1).tolist()
                token_max=max(token_max,max(lengths)); token_sum+=sum(lengths); token_n+=len(lengths)
                enc={k:v.to('cuda') for k,v in enc.items()}
                with torch.inference_mode(): vals=model(**enc).logits.reshape(-1).float().cpu().tolist()
                for x,v in zip(sub,vals): scores[x]=float(v)
            payload={'proposition_id':pid,'scores':scores}
            f.write(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'); f.flush()
            new+=1
            if idx%50==0: print(f'RERANK {idx}/{len(pairsets)} completed={len(done)+new}',flush=True)
    summary={'tag':a.tag,'dtype':a.dtype,'batch':a.batch,'max_length':a.max_length,'claims':len(pairsets),'new_claims':new,'pairs':sum(len(x['score_ids']) for x in pairsets),'seconds_this_run':time.time()-started,'peak_cuda_mib':torch.cuda.max_memory_allocated()/1024**2,'token_max_this_run':token_max,'token_mean_this_run':token_sum/token_n if token_n else None,'weights_sha256':c.RERANK_LFS_SHA}
    c.save(c.OUT/f'rerank_{a.tag}_summary.json',summary); print(json.dumps(summary),flush=True)
if __name__=='__main__': main()
