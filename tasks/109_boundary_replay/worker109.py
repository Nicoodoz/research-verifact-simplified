"""Future109 Linux GPU worker. Import/help never imports torch or loads9B."""
from pathlib import Path
import argparse,os,signal,sys,time
import common109 as c
from run109 import authorization,require_budget

STOP=False
_OLD=None
def stop(sig,frame):
    global STOP
    STOP=True
def append(path,row):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('ab') as f:f.write((c.canonical(row)+'\n').encode());f.flush();os.fsync(f.fileno())
def progress(a,stage,**values):c.put(a.work/'progress.json',dict(stage=stage,utc=c.utc(),**values))
def old_imports():
    global _OLD
    if _OLD is not None:return _OLD
    sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
    sys.path.insert(0,str(c.ROOT/'tasks/107_support_aux'))
    from data105 import encode,shared,training_plan,validate_cursor
    from parse105 import parse
    _OLD=(encode,shared,training_plan,validate_cursor,parse);return _OLD
def load_base(a):
    require_budget(a.session,120)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    os.environ.update(TORCH_EXTENSIONS_DIR=str(a.work/'cache/torch_extensions'),TRITON_CACHE_DIR=str(a.work/'cache/triton'),TORCHINDUCTOR_CACHE_DIR=str(a.work/'cache/inductor'))
    from unsloth import FastLanguageModel
    import torch
    from transformers import AutoTokenizer
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise RuntimeError('BF16 CUDA required; no quantization/truncation/CPU-offload fallback')
    cfg=c.read(a.bundle/'frozen/config109.json');length=c.read(a.bundle/'frozen/tokenizer109.json')['required_context_tokens']
    begin=time.perf_counter();tokenizer=AutoTokenizer.from_pretrained(a.model_dir,trust_remote_code=False,local_files_only=True)
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model_dir),max_seq_length=length,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    if getattr(model,'is_loaded_in_4bit',False) or getattr(model,'is_loaded_in_8bit',False) or any(p.device.type!='cuda' for p in model.parameters()):raise RuntimeError('Unexpected quantization/offload')
    append(a.work/'loads.jsonl',dict(mode=a.mode,seconds=time.perf_counter()-begin,context_tokens=length,GPU=torch.cuda.get_device_name()))
    return model,tokenizer,FastLanguageModel,torch,cfg
def source_folder(a):
    pointer=c.read(a.bundle/'source107/resume.json')
    if pointer['step']!=50 or pointer['fingerprint']['arm']!='label_only':raise ValueError('Wrong source checkpoint')
    return a.bundle/'source107'/pointer['slot']
def attach_training(model,Fast,cfg,torch):
    tr=cfg['training']
    model=Fast.get_peft_model(model,r=tr['lora_r'],lora_alpha=tr['lora_alpha'],lora_dropout=tr['lora_dropout'],
        bias=tr['bias'],target_modules=tr['target_modules'],use_gradient_checkpointing=tr['gradient_checkpointing'],
        random_state=cfg['seed'],use_rslora=tr['use_rslora'],finetune_vision_layers=False,finetune_language_layers=True)
    named=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if sum(p.numel() for n,p in named)!=tr['expected_trainable_parameters'] or any('lora_' not in n or 'vision' in n or 'visual' in n for n,p in named):raise ValueError('LoRA scope differs from107')
    Fast.for_training(model);return model,[p for n,p in named]
def optimizers(params,cfg,torch):
    tr=cfg['training'];optimizer=torch.optim.AdamW(params,lr=tr['learning_rate'],betas=tuple(tr['betas']),eps=tr['eps'],weight_decay=tr['weight_decay'])
    return optimizer,torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda step:1.)
def capture_rng(torch):
    import random,numpy as np
    return dict(torch=torch.get_rng_state().clone(),cuda=[s.clone() for s in torch.cuda.get_rng_state_all()],python=random.getstate(),numpy=np.random.get_state())
def restore_rng(torch,state):
    import random,numpy as np
    torch.set_rng_state(state['torch']);torch.cuda.set_rng_state_all(state['cuda']);random.setstate(state['python']);np.random.set_state(state['numpy'])
def fingerprint(a):
    return dict(task=109,arm='boundary_replay',source_task=107,source_adapter_sha256=c.SOURCE_ADAPTER_SHA,
        config_sha256=c.sha(a.bundle/'frozen/config109.json'),training_file_sha256=c.sha(a.work/'train.jsonl'),
        bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'))
def training_batch(tokenizer,row,torch,expected):
    encoded=old_imports()[0](tokenizer,row)
    if encoded['prompt_token_sha256']!=expected['prompt_token_sha256']:raise ValueError('Own unchanged original input differs from106/107')
    return dict(input_ids=torch.tensor([encoded['input_ids']],dtype=torch.long,device='cuda'),
        attention_mask=torch.ones((1,len(encoded['input_ids'])),dtype=torch.long,device='cuda'),
        groups=torch.tensor([encoded['groups']],dtype=torch.long,device='cuda')),encoded

def train(a,model,tokenizer,Fast,torch,cfg):
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    import checkpoint107 as ckpt
    from loss105 import backbone_loss
    rows=c.rows(a.work/'train.jsonl');meta={r['id']:r for r in c.rows(a.bundle/'data/pool_metadata.jsonl')}
    summary=c.read(a.work/'selection_summary.json');plan=old_imports()[2]([r['id'] for r in rows],1,8)
    if len(rows)!=192 or summary['N']!=192 or len(plan)!=24 or plan[-1]['consumed']!=192:raise ValueError('Fixed192/one-epoch/24-step candidate required')
    work=a.work/'train';work.mkdir(exist_ok=True);fp=fingerprint(a)
    if (work/'training_done.json').exists():
        done=c.read(work/'training_done.json')
        if done['fingerprint']!=fp or done['step']!=24:raise ValueError('Wrong109 training completion')
        return
    model,params=attach_training(model,Fast,cfg,torch)
    def restore(folder):set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
    if (work/'resume.json').exists():
        optimizer,scheduler=optimizers(params,cfg,torch);step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore)
        gate=c.read(work/'gpu_gate.json')
        if gate['fingerprint']!=fp:raise ValueError('Resume GPU gate belongs to another candidate')
        components=gate['components_seconds']
        require_budget(a.session,components['training']*(192-consumed)/192+components['evaluation']+components['saving_loading'])
    else:
        # The real longest backward includes the inherited optimizer on GPU.
        # It does no optimizer update; restore the tiny RNG snapshot afterwards.
        optimizer,scheduler=optimizers(params,cfg,torch);source_pointer=c.read(a.bundle/'source107/resume.json')
        old_step,old_consumed,_=ckpt.load(optimizer,scheduler,a.bundle/'source107',source_pointer['fingerprint'],restore)
        if (old_step,old_consumed)!=(50,392) or scheduler.last_epoch!=50:raise ValueError('Full107 optimizer/scheduler continuation failed')
        original_rng=capture_rng(torch)
        longest=max(rows,key=lambda r:meta[r['id']]['input_tokens']);timings=[]
        progress(a,'real_longest_backward_check',id=longest['id'],input_tokens=meta[longest['id']]['input_tokens'])
        for repeat in range(3):
            require_budget(a.session,120);model.zero_grad(set_to_none=True);torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
            batch,encoded=training_batch(tokenizer,longest,torch,meta[longest['id']])
            with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,chunk_tokens=16)
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite BF16 loss')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.0);torch.cuda.synchronize()
            if not torch.isfinite(norm) or float(norm)<=0:raise FloatingPointError('Nonfinite/zero LoRA gradient')
            timings.append(dict(warmup=repeat==0,seconds=time.perf_counter()-begin,tokens=len(encoded['input_ids']),peak_allocated_bytes=torch.cuda.max_memory_allocated()))
            del batch,loss
        model.zero_grad(set_to_none=True);restore_rng(torch,original_rng)
        infer=[c.read(a.work/name/'done.json') for name in ('mining_a','mining_s')]
        infer_seconds=sum(d['generation_seconds'] for d in infer);infer_tokens=sum(d['input_tokens'] for d in infer)
        actual_per_token=max(t['seconds']/t['tokens'] for t in timings[1:])
        historical_per_token=(932.3954121560382-44.82827805897978)/(1636868*2)
        training_tokens=sum(meta[r['id']]['input_tokens']+9 for r in rows)
        evaluation_tokens=sum(r['input_tokens'] for r in c.rows(a.bundle/'frozen/eval_token_lengths.jsonl'))
        components=dict(training=max(actual_per_token,historical_per_token)*training_tokens*1.5+24*(44.82827805897978/50),
            evaluation=infer_seconds/infer_tokens*evaluation_tokens*1.5,saving_loading=300)
        projected=sum(components.values())
        require_budget(a.session,projected)
        gate=dict(fingerprint=fp,source_optimizer_step=50,source_consumed=392,source_RNG_restored_after_probe=True,
            source_optimizer_moments_resident_during_probe=True,
            probe_optimizer_updates=0,real_longest_backward_passed=True,measurements=timings,
            max_input_tokens=meta[longest['id']]['input_tokens'],BF16=True,microbatch=1,full_input=True,
            main_loss='loss105.backbone_loss',auxiliary_head=False,estimated_remaining_seconds=projected,
            components_seconds=components,
            whole_remaining_training_evaluation_and_save_fits=True)
        c.put(work/'gpu_gate.json',gate);step=consumed=0;ckpt.save(model,optimizer,scheduler,work,0,0,fp)
    by_id={r['id']:r for r in rows};progress(a,'training',new_steps_total=24,source_steps=50)
    for entry in old_imports()[3](plan,step,consumed):
        if STOP:raise InterruptedError('Stopped at previous committed optimizer boundary')
        require_budget(a.session,120);optimizer.zero_grad(set_to_none=True);begin=time.perf_counter();losses=[]
        for identifier in entry['ids']:
            if STOP:raise InterruptedError('Partial accumulation discarded; previous complete checkpoint retained')
            require_budget(a.session,90)
            batch,encoded=training_batch(tokenizer,by_id[identifier],torch,meta[identifier])
            with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,chunk_tokens=16)
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite unchanged main loss')
            (loss/entry['loss_divisor']).backward();losses.append(float(loss.detach()));del batch,loss
        norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite gradient')
        optimizer.step();scheduler.step();torch.cuda.synchronize();ckpt.save(model,optimizer,scheduler,work,entry['step'],entry['consumed'],fp)
        append(work/'steps.jsonl',dict(step=entry['step'],global_step=50+entry['step'],consumed=entry['consumed'],ids=entry['ids'],
            loss=sum(losses)/len(losses),loss_divisor=entry['loss_divisor'],lr=optimizer.param_groups[0]['lr'],seconds=time.perf_counter()-begin))
        progress(a,'training',step=entry['step'],steps_total=24,consumed=entry['consumed'])
    pointer=c.read(work/'resume.json')
    if pointer['step']!=24 or scheduler.last_epoch!=74:raise ValueError('Wrong fixed continuation endpoint')
    c.put(work/'training_done.json',dict(step=24,consumed=192,source_step=50,global_step=74,fingerprint=fp,
        chosen_by='fixed_final_one_epoch_not500_results',final_slot=pointer['slot'],auxiliary_head_saved=False))

def inference(a,model,tokenizer,Fast,torch,cfg):
    from peft import PeftModel
    _,shared,_,_,parse=old_imports()
    if a.mode=='evaluate':
        work=a.work/'evaluation';train_work=a.work/'train';done=c.read(train_work/'training_done.json')
        if done['fingerprint']!=fingerprint(a) or done['step']!=24:raise ValueError('Final109 adapter required')
        pointer=c.read(train_work/'resume.json');folder=train_work/pointer['slot'];adapter_sha=c.sha(folder/'adapter_model.safetensors')
        rows={r['id']:r for r in c.rows(a.bundle/'data/eval_inputs.jsonl')};lengths={r['id']:r for r in c.rows(a.bundle/'frozen/eval_token_lengths.jsonl')}
        batches=c.read(a.bundle/'frozen/eval_batches.json')['batches']
    else:
        phase='mining_a' if a.mode=='mine_a' else 'mining_s';work=a.work/phase;folder=source_folder(a);adapter_sha=c.SOURCE_ADAPTER_SHA
        rows={r['id']:r for r in c.rows(a.bundle/'data/pool.jsonl')};lengths={r['id']:r for r in c.rows(a.bundle/'data/pool_metadata.jsonl')}
        ids=c.read(a.bundle/'data/stage_a_ids.json') if a.mode=='mine_a' else c.read(a.work/'supported_request.json')['ids']
        ids=sorted(ids,key=lambda i:(lengths[i]['input_tokens'],i));size=cfg['mining']['batch_size']
        batches=[dict(batch=n//size,ids=ids[n:n+size]) for n in range(0,len(ids),size)]
    work.mkdir(parents=True,exist_ok=True);model=PeftModel.from_pretrained(model,folder,is_trainable=False);Fast.for_inference(model);model.eval()
    pad=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id;eos=tokenizer.convert_tokens_to_ids('<|im_end|>')
    progress(a,a.mode,total=len(batches),source_adapter_sha256=adapter_sha)
    for entry in batches:
        path=work/f"batch-{entry['batch']:04d}.json"
        if path.exists():
            prior=c.read(path)
            if prior['ids']!=entry['ids'] or prior['checkpoint_adapter_sha256']!=adapter_sha:raise ValueError('Existing first receipt mismatched')
            continue
        if STOP:raise InterruptedError('Inference stopped; preserve first receipts')
        require_budget(a.session,120);sequences=[]
        for identifier in entry['ids']:
            ids=shared.prompt_ids(tokenizer,rows[identifier]);expected=lengths[identifier].get('prompt_token_sha256',lengths[identifier].get('input_token_sha256'))
            if c.digest(c.canonical(ids))!=expected:raise ValueError('Inference prompt changed')
            sequences.append(ids)
        maximum=max(map(len,sequences));inputs=torch.tensor([[pad]*(maximum-len(s))+s for s in sequences],device='cuda')
        mask=torch.tensor([[0]*(maximum-len(s))+[1]*len(s) for s in sequences],device='cuda')
        inflight=path.with_suffix('.inflight.json')
        if inflight.exists():append(work/'recovery_events.jsonl',dict(batch=entry['batch'],prior_uncommitted_attempt=True,prior_answer_not_available=True,utc=c.utc()))
        c.put(inflight,dict(ids=entry['ids'],checkpoint_adapter_sha256=adapter_sha,utc=c.utc()))
        torch.cuda.synchronize();begin=time.perf_counter()
        with torch.inference_mode():generated=model.generate(input_ids=inputs,attention_mask=mask,do_sample=False,num_beams=1,
            num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
        torch.cuda.synchronize();seconds=time.perf_counter()-begin;records=[]
        for n,identifier in enumerate(entry['ids']):
            tail=generated[n,maximum:].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            content=tokenizer.decode(tail,skip_special_tokens=True)
            records.append(dict(id=identifier,sid=rows[identifier]['sid'],prediction_origin='actual_GPU_checkpoint',
                checkpoint_adapter_sha256=adapter_sha,prompt_token_sha256=c.digest(c.canonical(sequences[n])),
                input_tokens=len(sequences[n]),output_tokens=len(tail),finish_reason=finish,content=content,parsed=parse(content,finish)))
        c.put(path,dict(ids=entry['ids'],checkpoint_adapter_sha256=adapter_sha,generation_seconds=seconds,records=records))
        inflight.unlink()
        progress(a,a.mode,batches_completed=entry['batch']+1,batches_total=len(batches))
    receipts=[c.read(work/f"batch-{b['batch']:04d}.json") for b in batches];records=[r for b in receipts for r in b['records']]
    c.putl(work/'predictions.jsonl',records)
    c.put(work/'done.json',dict(N=len(records),input_tokens=sum(r['input_tokens'] for r in records),
        generation_seconds=sum(r['generation_seconds'] for r in receipts),invalid=sum(not r['parsed']['valid'] for r in records),
        checkpoint_adapter_sha256=adapter_sha,successful_receipt_repeated=False))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['mine_a','mine_s','train','evaluate'])
    for key in ('bundle','model-dir','work','session'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--execute-rented-gpu',action='store_true');a=p.parse_args();authorization(a.bundle,a.session,a.execute_rented_gpu)
    if a.work.resolve().is_relative_to(a.bundle.resolve()):raise ValueError('Never write into the immutable bundle/source107 checkpoint')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);old_imports()
    model,tokenizer,Fast,torch,cfg=load_base(a)
    if a.mode=='train':train(a,model,tokenizer,Fast,torch,cfg)
    else:inference(a,model,tokenizer,Fast,torch,cfg)

if __name__=='__main__':main()
