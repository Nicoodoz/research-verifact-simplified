"""Evaluate a frozen, selected three-code classifier on new IDs only."""
from pathlib import Path
import sys,os,time,signal,argparse,gc
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(Path(__file__).parent));import classifier116 as method
STOP=False

def stop(*_):
    global STOP;STOP=True

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True)
    job=c.read(R/'data'/p.parse_args().job);cfg=c.read(R/job['config']);session=c.read(R/'session.json')
    out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True);started=time.time()
    deadline=min(session['start_epoch']+session['duration_seconds']-600,started+job['phase_limit_seconds'])
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def budget():
        if STOP or time.time()>deadline-45:raise TimeoutError('Save received predictions; cycle time limit')
    def progress(stage,n,eta=None):c.put(out/'progress.json',dict(stage=stage,completed=n,total=len(job['ids']),remaining_seconds=eta,epoch=time.time()))
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
    from unsloth import FastLanguageModel as Fast
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(cfg['model_dir'],local_files_only=True);codes=method.label_token_ids(tok);assert list(codes)==cfg['code_token_ids']
    pool={r['id']:r for r in c.rows(R/job.get('inputs','data/inputs.jsonl'))};encoded={}
    for i in job['ids']:
        row=pool[i];assert not {'GT','sid','panel','verdict'}&set(row)
        encoded[i]=method.prompt_ids(tok,row)
        assert len(encoded[i])<=job['max_seq_length'],'No silent truncation'
    folder=Path(job['adapter_path']);assert c.sha(folder/'adapter_model.safetensors')==job['adapter_sha256']
    progress('loading',0);budget()
    model,_=Fast.from_pretrained(model_name=cfg['model_dir'],max_seq_length=job['max_seq_length'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    model=PeftModel.from_pretrained(model,folder,is_trainable=False);Fast.for_inference(model);model.eval()
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    order=sorted(job['ids'],key=lambda i:(len(encoded[i]),i));done=0;times=[];group_index=0
    batch_limit=job.get('batch_size',2);assert batch_limit in {1,2,4}
    if job.get('longest_batch_first'):
        order=order[-batch_limit:]+order[:-batch_limit]
    while order:
        n=min(batch_limit,len(order))
        if batch_limit<=2 and len(encoded[order[0]])>12701:n=1
        ids=order[:n];order=order[n:];group_index+=1
        existing=[out/'predictions'/f'{i}.json' for i in ids]
        if all(f.exists() for f in existing):
            assert all(c.read(f)['adapter_sha256']==job['adapter_sha256'] for f in existing)
            done+=n;continue
        assert not any(f.exists() for f in existing),'Partial group needs explicit continuation, not overwrite'
        budget();mx=max(len(encoded[i]) for i in ids)
        batch=dict(input_ids=torch.tensor([[pad]*(mx-len(encoded[i]))+encoded[i] for i in ids],device='cuda'),attention_mask=torch.tensor([[0]*(mx-len(encoded[i]))+[1]*len(encoded[i]) for i in ids],device='cuda'))
        torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
        try:
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):pred=method.predict(model,batch,codes)
        except torch.cuda.OutOfMemoryError:
            c.put(out/'oom_attempts'/f'{group_index:05d}.json',dict(ids=ids,batch_size=n,seconds=time.perf_counter()-t,accepted_outputs=0))
            del batch;gc.collect();torch.cuda.empty_cache()
            if n==1:raise
            batch_limit=max(1,n//2);order=ids+order;continue
        torch.cuda.synchronize();seconds=time.perf_counter()-t;times.append(seconds)
        for i,z in zip(ids,pred):
            c.put(out/'predictions'/f'{i}.json',dict(id=i,source_prompt_sha256_104=pool[i]['expected_prompt_sha256'],internal_prompt_sha256=c.digest(c.canonical(encoded[i])),input_tokens=len(encoded[i]),adapter_sha256=job['adapter_sha256'],**z))
        c.put(out/'batches'/f'{group_index:05d}.json',dict(ids=ids,seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),batch_limit=batch_limit))
        done+=n;progress('classifying',done,sum(times[1:])/max(1,len(times)-1)*len(order)/batch_limit);del batch
    c.put(out/'complete.json',dict(N=done,seconds=sum(times),wall_seconds=time.time()-started,epoch=time.time(),adapter_sha256=job['adapter_sha256'],decision='three_fixed_codes_argmax',initial_batch_limit=job.get('batch_size',2),final_batch_limit=batch_limit))
    progress('complete',done)

if __name__=='__main__':main()
