"""Frozen107 causal states before/after a universal Not token; no labels read."""
from pathlib import Path
import argparse, gc, os, signal, sys, time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as common
sys.path.insert(0,str(ROOT/'tasks/104_supervision_evidence'));import training104 as original
PREFIX=[4754,415,8217,3147]
NOT=[2536]
STOP=False

def stop(*_):
    global STOP
    STOP=True

def prefix_index(prompt_length,sequence_length,padded_length):
    # The final Not token is a future position relative to this saved state.
    return padded_length-sequence_length+prompt_length+len(PREFIX)-1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',required=True);args=parser.parse_args()
    job=common.read(ROOT/'data'/args.job);session=common.read(ROOT/'session.json')
    out=ROOT/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
    start=time.time();deadline=min(session['start_epoch']+session['duration_seconds']-300,start+job['phase_limit_seconds'])
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def check():
        if STOP or time.time()>deadline-30:raise TimeoutError('Preserve126 states and stop at current authorized boundary')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
    from unsloth import FastLanguageModel as Fast
    import numpy as np
    import torch
    from transformers import AutoTokenizer
    from peft import PeftModel
    tok=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
    assert tok.encode('{"verdict":"',add_special_tokens=False)==PREFIX
    assert tok.encode('{"verdict":"Not',add_special_tokens=False)==PREFIX+NOT
    for label in ('Not Supported','Not Addressed'):
        assert tok.encode(common.canonical({'verdict':label}),add_special_tokens=False)[:5]==PREFIX+NOT
    pool={r['id']:r for r in common.rows(ROOT/job['inputs'])};seq={};prompt_lengths={}
    for identifier in job['ids']:
        row=pool[identifier];assert not {'GT','sid','panel','verdict','answer'}&set(row)
        prompt=original.prompt_ids(tok,row)
        assert common.digest(common.canonical(prompt))==row['expected_prompt_sha256']
        # Exactly the same suffix for every S/NS/NA input, independent of GT.
        seq[identifier]=prompt+PREFIX+NOT;prompt_lengths[identifier]=len(prompt)
        assert len(seq[identifier])<=job['max_seq_length']
    accepted=set();files=list((out/'batches').glob('*.json'))
    for path in files:
        receipt=common.read(path);assert path.with_suffix('.npz').exists()
        assert receipt['adapter_sha256']==job['adapter_sha256'] and receipt['suffix_ids']==PREFIX+NOT
        assert not accepted&set(receipt['ids']);accepted.update(receipt['ids'])
    assert accepted<=set(job['ids'])
    check();common.put(out/'progress.json',dict(stage='loading',completed=len(accepted),total=len(seq)))
    model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=job['max_seq_length'],dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    adapter=Path(job['adapter_path']);assert common.sha(adapter/'adapter_model.safetensors')==job['adapter_sha256']
    model=PeftModel.from_pretrained(model,adapter,is_trainable=False);Fast.for_inference(model);model.eval()
    assert not any(p.requires_grad for p in model.parameters())
    backbone=model.get_base_model().model;pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    order=sorted(set(seq)-accepted,key=lambda i:(len(seq[i]),i));limit=job['batch_size']
    if order:order=order[-limit:]+order[:-limit]
    batchno=max([int(p.stem) for p in files],default=0);times=[]
    while order:
        check();ids=order[:limit];order=order[limit:];n=len(ids);mx=max(len(seq[i]) for i in ids)
        batch=dict(input_ids=torch.tensor([[pad]*(mx-len(seq[i]))+seq[i] for i in ids],device='cuda'),
            attention_mask=torch.tensor([[0]*(mx-len(seq[i]))+[1]*len(seq[i]) for i in ids],device='cuda'),use_cache=False,return_dict=True)
        torch.cuda.reset_peak_memory_stats();started=time.perf_counter()
        try:
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                result=backbone(**batch);h=result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]
                pos=torch.tensor([prefix_index(prompt_lengths[i],len(seq[i]),mx) for i in ids],device='cuda')
                assert bool((pos==mx-2).all())
                before=h[torch.arange(n,device='cuda'),pos].float().cpu().numpy()
                after=h[:,-1].float().cpu().numpy()
        except torch.cuda.OutOfMemoryError:
            del batch;gc.collect();torch.cuda.empty_cache()
            if n==1:raise
            limit=max(1,n//2);order=ids+order;continue
        assert np.isfinite(before).all() and np.isfinite(after).all();torch.cuda.synchronize()
        seconds=time.perf_counter()-started;batchno+=1;target=out/'batches'/f'{batchno:05d}.npz';target.parent.mkdir(exist_ok=True)
        temporary=target.with_suffix('.tmp')
        with temporary.open('wb') as stream:np.savez(stream,ids=np.asarray(ids),verdict_prefix=before,not_prefix=after)
        temporary.replace(target)
        common.put(target.with_suffix('.json'),dict(ids=ids,input_tokens=[len(seq[i]) for i in ids],seconds=seconds,
            suffix_ids=PREFIX+NOT,prefix_saved_before_not=True,adapter_sha256=job['adapter_sha256'],peak_allocated_bytes=torch.cuda.max_memory_allocated()))
        accepted.update(ids);times.append(seconds)
        common.put(out/'progress.json',dict(stage='extracting',completed=len(accepted),total=len(seq),
            remaining_seconds=sum(times)/len(times)*len(order)/limit,epoch=time.time()))
        del batch,h,result,before,after
    common.put(out/'complete.json',dict(N=len(accepted),adapter_sha256=job['adapter_sha256'],suffix_ids=PREFIX+NOT,
        wall_seconds=time.time()-start,seconds=sum(times),same_forward_states=True,prefix_saved_before_not=True,
        all_examples_same_suffix=True,labels_in_inputs=False,initial_batch=job['batch_size'],final_batch=limit))
    common.put(out/'progress.json',dict(stage='complete',completed=len(accepted),total=len(seq)))

if __name__=='__main__':main()
