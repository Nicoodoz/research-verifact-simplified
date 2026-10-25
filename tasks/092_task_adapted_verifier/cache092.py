"""Lossless input coverage and frozen lower-23-layer activation cache."""
import os,time,sys,copy,json
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import torch
from transformers import AutoTokenizer,AutoModel
import common092 as c
from pathlib import Path
def windows(tok,claim,reference,cfg):
    q=tok.encode(claim,add_special_tokens=False);e=tok.encode(reference,add_special_tokens=False)
    capacity=cfg['max_length']-len(q)-tok.num_special_tokens_to_add(pair=True)
    assert capacity>=64,'Claim would require truncation'
    starts=list(range(0,max(1,len(e)-capacity+1),capacity-cfg['overlap']))
    if starts[-1]+capacity<len(e):starts.append(len(e)-capacity)
    result=[]
    for start in sorted(set(starts)):
        ids=tok.build_inputs_with_special_tokens(e[start:start+capacity],q)
        assert len(ids)<=cfg['max_length'];result.append(dict(input_ids=ids,evidence_start=start,evidence_end=min(len(e),start+capacity)))
    covered=set(i for r in result for i in range(r['evidence_start'],r['evidence_end']))
    assert len(covered)==len(e)
    return result,len(e)
def main():
    start=time.time();torch.set_num_threads(4);cfg=c.read(c.TASK/'config.json');root=Path(cfg['activation_cache']);root.mkdir(parents=True,exist_ok=True)
    rows=c.lines(c.PRIVATE/'inputs.jsonl');tok=AutoTokenizer.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True)
    pairs=[];bags=[];offset=0
    for r in rows:
        ww,ne=windows(tok,r['text'],r['reference'],cfg);ix=[]
        for w in ww:
            ix.append(len(pairs));w['offset']=offset;offset+=len(w['input_ids']);pairs.append(w)
        bags.append(dict(id=r['proposition_id'],windows=ix,reference_sha256=c.digest(r['reference']),claim_sha256=c.digest(r['text']),source=r['source'],evidence_tokens=ne))
    binding=dict(input_sha=c.sha(c.PRIVATE/'inputs.jsonl'),config_sha=c.sha(c.TASK/'config.json'),pairs=len(pairs),tokens=offset,dimensions=1024)
    if (root/'binding.json').exists():
        previous=c.read(root/'binding.json')
        if previous!=binding:
            compat=c.read(c.OUT/'cache_config_compatibility.json')
            assert previous['config_sha']==compat['old_config_sha'] and binding['config_sha']==compat['current_config_sha']
            assert all(previous[k]==binding[k] for k in binding if k!='config_sha')
            assert compat['only_changed_field']=='window_microbatch' and compat['unused_by_cache_forward'] is True
    else:c.put(root/'binding.json',binding)
    c.jsonl(c.PRIVATE/'windows.jsonl',pairs);c.jsonl(c.OUT/'bags.jsonl',bags)
    def mmap(name,shape,dtype):
        p=root/name;return np.lib.format.open_memmap(p,mode='r+' if p.exists() else 'w+',dtype=dtype,shape=shape)
    hidden=mmap('lower23.npy',(offset,1024),'float16');features=mmap('cls24.npy',(len(pairs),1024),'float32');done=mmap('done.npy',(len(pairs),),'uint8')
    model=AutoModel.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
    for p in model.parameters():p.requires_grad_(False)
    # Save unmodified pretrained top block and shared relative table for exact continuation.
    torch.save(dict(layer={k:v.detach().cpu().float() for k,v in model.encoder.layer[-1].state_dict().items()},relative=model.encoder.get_rel_embedding().detach().cpu().float()),c.PRIVATE/'pretrained_top.pt')
    from model092 import Verifier
    top=Verifier(adapt=False).cuda().eval();max_difference=0.
    todo=np.flatnonzero(done==0).tolist();batch_size=c.read(c.OUT/'engineering_preflight.json')['cache_batch'];print('cache',binding,'remaining',len(todo),'batch',batch_size,flush=True)
    for j in range(0,len(todo),batch_size):
        ix=todo[j:j+batch_size];batch=tok.pad([dict(input_ids=pairs[i]['input_ids'],attention_mask=[1]*len(pairs[i]['input_ids'])) for i in ix],return_tensors='pt').to('cuda')
        with torch.inference_mode():
            out=model(**batch,output_hidden_states=True);lo=out.hidden_states[-2].cpu().numpy()
            with torch.autocast('cuda',dtype=torch.float16):hi=top.encode(out.hidden_states[-2].float(),batch['attention_mask']).float()
            max_difference=max(max_difference,float((hi-out.last_hidden_state[:,0].float()).abs().max()))
            hi=hi.cpu().numpy()
        for k,i in enumerate(ix):
            p=pairs[i];n=len(p['input_ids']);hidden[p['offset']:p['offset']+n]=lo[k,:n];features[i]=hi[k]
        hidden.flush();features.flush()
        done[ix]=1;done.flush()
        if j%100==0:
            c.put(c.OUT/'cache_progress.json',dict(completed=int(done.sum()),total=len(pairs),seconds=time.time()-start,utc=c.now()))
            print('cache',int(done.sum()),len(pairs),round(time.time()-start),flush=True)
        del out,batch,lo,hi
    hidden.flush();features.flush();c.put(c.OUT/'cache_manifest.json',dict(**binding,seconds_this_run=time.time()-start,path=str(root),bytes=hidden.nbytes+features.nbytes,max_split_vs_original_abs_difference=max_difference,both_arms_use_same_split_precision=True,model_source=c.read(c.ROOT/'outputs/032_evidence_relation_correction/model_manifest.json'),complete=bool(np.all(done))))
if __name__=='__main__':main()
