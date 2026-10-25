"""Reuse 008/009 C48 rules, 021 local BGE weights; no API and no GT read."""
import os,sys,time,json,ast,types,math,re,collections
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import torch
from transformers import AutoTokenizer,AutoModel,AutoModelForSequenceClassification
import common092 as c
def original_rules():
    # Compile exact pure definitions, avoiding the old API/duckdb import chain in GPU env.
    path=c.ROOT/'tasks/008_retrieval_planning/planning_core.py';tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    wanted={'tokenize','HybridIndex','display_line','select_evidence'}
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in wanted or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STOP' for t in n.targets)]
    ns=dict(re=re,math=math,np=np,Counter=collections.Counter,c=types.SimpleNamespace(pilot=types.SimpleNamespace(digest_text=c.digest)))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    tree=ast.parse((c.ROOT/'tasks/009_retrieval_baselines/study009.py').read_text(encoding='utf-8-sig'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'quota_candidates','candidates'}],type_ignores=[]),'original009','exec'),ns)
    return types.SimpleNamespace(core=types.SimpleNamespace(**{k:ns[k] for k in wanted}),candidates=ns['candidates'])
old=original_rules()
def main():
    torch.set_num_threads(4);start=time.time();inputs=c.lines(c.PRIVATE/'missing_inputs.jsonl');corpus=c.lines(c.PRIVATE/'missing_corpus.jsonl')
    catalog={p['embedding_id']:p['search_text'] for p in corpus};catalog.update({c.digest(r['text']):r['text'] for r in inputs});keys=sorted(catalog)
    n=len(keys);vp=c.PRIVATE/'missing_vectors.npy';dp=c.PRIVATE/'embed_done.npy'
    v=np.lib.format.open_memmap(vp,mode='r+' if vp.exists() else 'w+',dtype='float32',shape=(n,1024));done=np.lib.format.open_memmap(dp,mode='r+' if dp.exists() else 'w+',dtype='uint8',shape=(n,))
    todo=np.flatnonzero(done==0).tolist();base=c.ROOT/'.local_models/021'
    if todo:
        tok=AutoTokenizer.from_pretrained(base/'bge-m3',local_files_only=True);m=AutoModel.from_pretrained(base/'bge-m3',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
        for j in range(0,len(todo),4):
            ix=todo[j:j+4];batch=tok([catalog[keys[i]] for i in ix],padding=True,truncation=True,max_length=8192,return_tensors='pt').to('cuda')
            with torch.inference_mode():x=torch.nn.functional.normalize(m(**batch).last_hidden_state[:,0].float(),dim=-1).cpu().numpy()
            v[ix]=x;v.flush();done[ix]=1;done.flush()
            if j%100==0:print('embed',int(done.sum()),n,'seconds',round(time.time()-start),flush=True)
        del m;torch.cuda.empty_cache()
    vectors={k:v[i] for i,k in enumerate(keys)};byid={p['passage_id']:p for p in corpus};canpath=c.PRIVATE/'local_candidates.jsonl'
    if not canpath.exists():
        indices={sid:old.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in sorted({r['subject_id'] for r in inputs}) for pp in [[p for p in corpus if p['subject_id']==sid]]}
        cans=[dict(proposition_id=r['proposition_id'],candidate_ids=old.candidates(indices[r['subject_id']].retrieve(r['text'],vectors[c.digest(r['text'])]),'C')) for r in inputs];c.jsonl(canpath,cans)
    cans={r['proposition_id']:r['candidate_ids'] for r in c.lines(canpath)};out=c.PRIVATE/'local_c48.jsonl';existing={r['proposition_id'] for r in c.lines(out)} if out.exists() else set()
    todo=[r for r in inputs if r['proposition_id'] not in existing]
    if todo:
        tok=AutoTokenizer.from_pretrained(base/'bge-reranker-v2-m3',local_files_only=True);m=AutoModelForSequenceClassification.from_pretrained(base/'bge-reranker-v2-m3',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
        with out.open('a',encoding='utf-8') as f:
            for j,r in enumerate(todo):
                ids=cans[r['proposition_id']];scores={}
                for lo in range(0,len(ids),4):
                    pp=ids[lo:lo+4];batch=tok([r['text']]*len(pp),[byid[p]['search_text'] for p in pp],padding=True,truncation=True,max_length=8192,return_tensors='pt').to('cuda')
                    with torch.inference_mode():vals=m(**batch).logits.flatten().float().cpu().tolist()
                    scores.update(zip(pp,vals))
                pack=old.core.select_evidence(ids,scores,byid,r['admission']);result=dict(proposition_id=r['proposition_id'],text=r['text'],reference=pack['reference'],source='092_local_BGE_C48',selected_ids=pack['selected_ids'])
                f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush()
                if j%10==0:print('rerank+pack',len(existing)+j+1,len(inputs),'seconds',round(time.time()-start),flush=True)
        del m;torch.cuda.empty_cache()
    allrows=c.lines(c.PRIVATE/'cached_c48.jsonl')+c.lines(out);allrows.sort(key=lambda r:r['proposition_id']);assert len({r['proposition_id'] for r in allrows})==9065
    c.jsonl(c.PRIVATE/'inputs.jsonl',allrows);c.put(c.OUT/'c48_manifest.json',dict(n=len(allrows),sha256=c.sha(c.PRIVATE/'inputs.jsonl'),new_local=len(inputs),cached=len(allrows)-len(inputs),seconds_this_resume=time.time()-start,API_calls=0,local_not_claimed_bitwise_API_equivalent=True))
    print('C48 complete',len(allrows),flush=True)
if __name__=='__main__':main()
