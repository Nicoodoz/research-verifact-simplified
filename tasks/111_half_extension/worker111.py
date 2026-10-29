"""Three saved endpoints, only missing selection IDs; no training or shutdown."""
from pathlib import Path
import argparse,os,sys,time,signal,json,math
sys.path.insert(0,'/root/autodl-tmp/verifact109/bundle/tasks/109_boundary_replay');import common109 as c
STOP=False
def stop(sig,frame):
    global STOP;STOP=True
def budget(a,seconds=60):
    s=c.read(a.session)
    import platform
    if s['task']!=111 or not s['authorized'] or platform.node()!=s['bound_instance']:raise PermissionError('Wrong111 current instance')
    if STOP or (time.time()+seconds-s['billing_start_epoch'])*s['hourly_cny']/3600>s['cap_cny']-.12:raise TimeoutError('Stop111 compute within6 CNY; retain first receipts, no shutdown')
def progress(a,stage,**values):c.put(a.work/'progress.json',dict(task=111,stage=stage,utc=c.utc(),**values))
def activate(model,name):
    model.set_adapter(name);model.eval()
    for p in model.parameters():p.requires_grad_(False)
    if list(model.active_adapters)!=[name]:raise ValueError('Exactly one original saved adapter active')
def main():
    p=argparse.ArgumentParser()
    for name in ['root','old','model','session']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.work=a.root/'results';a.work.mkdir(exist_ok=True);budget(a)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TORCH_EXTENSIONS_DIR=str(a.old/'results/cache/torch_extensions'),TRITON_CACHE_DIR=str(a.old/'results/cache/triton'),TORCHINDUCTOR_CACHE_DIR=str(a.old/'results/cache/inductor'))
    from unsloth import FastLanguageModel
    import torch
    from transformers import AutoTokenizer
    from peft import PeftModel
    sys.path.insert(0,str(a.old/'bundle/tasks/104_supervision_evidence'));from training104 import prompt_ids
    sys.path.insert(0,str(a.old/'bundle/tasks/105_brief_supervision'));from parse105 import parse
    cfg=c.read(a.root/'data/config111.json');rows={r['id']:r for r in c.rows(a.root/'data/inputs_new.jsonl')};assert len(rows)==cfg['new_IDs']
    tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True,trust_remote_code=False);progress(a,'tokenizing_full_author_reference',completed=0,total=len(rows));lengths={}
    for n,(i,r) in enumerate(rows.items()):
        seq=prompt_ids(tok,r);lengths[i]=dict(id=i,sid=r['sid'],input_tokens=len(seq),prompt_token_sha256=c.digest(c.canonical(seq)))
        if n%100==0:progress(a,'tokenizing_full_author_reference',completed=n+1,total=len(rows))
    c.putl(a.work/'input_lengths.jsonl',list(lengths.values()));ordered=sorted(rows,key=lambda i:(lengths[i]['input_tokens'],i));representatives=[ordered[-1],ordered[len(ordered)//2],ordered[0]]
    batches=[dict(batch=n,ids=[i],kind='formal_representative') for n,i in enumerate(representatives)];pending=[i for i in ordered if i not in representatives];n=0
    while n<len(pending):
        size=2 if lengths[pending[n]]['input_tokens']<=12701 else 1
        if size==2 and n+1<len(pending) and lengths[pending[n+1]]['input_tokens']>12701:size=1
        batches.append(dict(batch=len(batches),ids=pending[n:n+size],kind='formal_regular'));n+=size
    maximum=max(x['input_tokens'] for x in lengths.values());context=max(13097,maximum+384)
    c.put(a.work/'input_plan.json',dict(N=len(rows),max_prompt_tokens=maximum,context_tokens=context,representative_ids=representatives,batches=batches,no_truncation=True,same_all_arms=True))
    budget(a,120);progress(a,'loading_single_original9B',max_prompt_tokens=maximum,context=context)
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model),max_seq_length=context,dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    if any(p.device.type!='cuda' for p in model.parameters()) or getattr(model,'is_loaded_in_4bit',False):raise RuntimeError('Original BF16 full inputs only')
    identities={}
    for arm in cfg['arms']:
        folder=Path(cfg['source_adapters'][arm]['path'])
        while not (folder/'adapter_model.safetensors').exists():budget(a);time.sleep(2)
        #105 is transferred once; its readiness marker is written after close.
        if arm=='label_only105':
            while not (a.root/'105_READY.json').exists():budget(a);time.sleep(2)
        sha=c.sha(folder/'adapter_model.safetensors')
        if sha!=cfg['source_adapters'][arm]['sha256']:raise ValueError('Wrong saved adapter '+arm)
        if not identities:model=PeftModel.from_pretrained(model,folder,adapter_name=arm,is_trainable=False)
        else:model.load_adapter(folder,adapter_name=arm,is_trainable=False)
        identities[arm]=dict(arm=arm,adapter_sha256=sha)
    FastLanguageModel.for_inference(model);pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>')
    def predict(arm,batch):
        folder=a.work/arm;folder.mkdir(exist_ok=True);path=folder/f"batch-{batch['batch']:04d}.json"
        if path.exists():
            old=c.read(path)
            if old['identity']!=identities[arm] or old['ids']!=batch['ids']:raise ValueError('Wrong existing first receipt')
            return old
        budget(a,90);seqs=[prompt_ids(tok,rows[i]) for i in batch['ids']]
        if any(c.digest(c.canonical(s))!=lengths[i]['prompt_token_sha256'] for i,s in zip(batch['ids'],seqs)):raise ValueError('Prompt changed')
        length=max(map(len,seqs));x=torch.tensor([[pad]*(length-len(s))+s for s in seqs],device='cuda');mask=torch.tensor([[0]*(length-len(s))+[1]*len(s) for s in seqs],device='cuda')
        inflight=path.with_suffix('.inflight.json');c.put(inflight,dict(ids=batch['ids'],identity=identities[arm],utc=c.utc()))
        progress(a,arm,completed=sum(len(b['ids']) for b in batches[:batch['batch']]),total=len(rows),batch=batch['batch'],formal_kind=batch['kind'],longest_input=length)
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
        with torch.inference_mode():output=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
        torch.cuda.synchronize();seconds=time.perf_counter()-start;records=[]
        for j,i in enumerate(batch['ids']):
            tail=output[j,length:].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            text=tok.decode(tail,skip_special_tokens=True);records.append(dict(id=i,sid=rows[i]['sid'],identity=identities[arm],prompt_token_sha256=lengths[i]['prompt_token_sha256'],input_tokens=len(seqs[j]),output_tokens=len(tail),finish_reason=finish,content=text,parsed=parse(text,finish)))
        saved=dict(ids=batch['ids'],identity=identities[arm],seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),records=records)
        c.put(path,saved);inflight.unlink();return saved
    # Every check is an official first prediction, retained and skipped later.
    preflight_count=min(6,len(batches));bench={}
    for arm in cfg['arms']:
        activate(model,arm);bench[arm]=[predict(arm,b) for b in batches[:preflight_count]]
    total_tokens=sum(x['input_tokens'] for x in lengths.values());measured={}
    for arm,parts in bench.items():
        #The first batch2 can compile a different shape; its actual wall time
        #is already billed. Do not multiply that one-time cost over all IDs.
        warm=parts[4:] or parts[1:];tokens=sum(r['input_tokens'] for b in warm for r in b['records']);measured[arm]=sum(b['seconds'] for b in warm)/tokens
    remaining_seconds=sum(max(measured[a],985.3770993575454/4164271)*total_tokens*1.25 for a in cfg['arms'])+300
    budget(a,remaining_seconds);c.put(a.work/'gpu_gate.json',dict(formal_first_outputs_not_discarded=True,formal_prefix_batches=preflight_count,max_prompt_tokens=maximum,all_arms_longest_batch1_passed=True,
        per_arm_seconds_per_input_token=measured,estimated_remaining_seconds=remaining_seconds,all_remaining_work_and_return_budget_passed=True,peak_allocated_bytes={a:max(b['peak_allocated_bytes'] for b in parts) for a,parts in bench.items()},no_new_training=True))
    for arm in cfg['arms']:
        activate(model,arm)
        for b in batches:predict(arm,b)
        saved=[c.read(a.work/arm/f"batch-{b['batch']:04d}.json") for b in batches];records=[r for b in saved for r in b['records']]
        c.putl(a.work/arm/'predictions.jsonl',records);c.put(a.work/arm/'done.json',dict(N=len(records),invalid=sum(not r['parsed']['valid'] for r in records),seconds=sum(b['seconds'] for b in saved),identity=identities[arm]))
    c.put(a.work/'GPU_TASKS_COMPLETE.json',dict(task=111,new_IDs=len(rows),arms=cfg['arms'],new_training=False,new_paid_API_CNY=0,no_shutdown=True,utc=c.utc()))
if __name__=='__main__':main()
