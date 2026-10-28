"""Future GPU entry. Import/help is inert; no cloud, API, download or CPU 9B path."""
from pathlib import Path
import argparse
import os
import random
import signal
import time
import common105 as c
import budget105 as budget
from data105 import encode,shared,training_plan,validate_cursor
from parse105 import parse
from verify105 import bundle as verify_bundle

STOP=False
def stopped(sig,frame):
    global STOP
    STOP=True

def append(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('ab') as f:f.write((c.canonical(value)+'\n').encode('utf-8'));f.flush();os.fsync(f.fileno())

def load(a,config):
    budget.require(a.ledger,120,watchdog=True)
    preflight=c.read(a.work/'nogpu_preflight.json')
    if not preflight.get('all_weights_SHA_match'):raise RuntimeError('Real no-GPU weight/environment preflight must pass first')
    assert preflight['bundle_sha256']==c.sha(a.bundle/'manifest.json') and preflight['model_dir']==str(a.model_dir.resolve())
    if config['revision']!=c.REVISION:raise ValueError('Wrong frozen revision')
    # Prevent even accidental Hub/network fallback. The supplied original model
    # directory was verified by all four shard hashes during no-GPU preflight.
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from unsloth import FastLanguageModel
    import torch
    import numpy as np
    from transformers import AutoTokenizer
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise RuntimeError('BF16 CUDA required; no CPU/quantized fallback')
    random.seed(config['seed']);np.random.seed(config['seed']);torch.manual_seed(config['seed']);torch.cuda.manual_seed_all(config['seed'])
    if (a.model_dir/'adapter_config.json').exists():raise ValueError('Do not initialize from the 103 adapter')
    for name,sha in c.read(a.bundle/'frozen/token_summary.json')['tokenizer_files'].items():assert c.sha(a.model_dir/name)==sha,name
    length=c.read(a.bundle/'frozen/token_summary.json')['required_context_tokens']
    tok=AutoTokenizer.from_pretrained(str(a.model_dir),trust_remote_code=False,local_files_only=True)
    begin=time.perf_counter()
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model_dir),max_seq_length=length,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    assert not getattr(model,'is_loaded_in_4bit',False) and not getattr(model,'is_loaded_in_8bit',False)
    assert all(p.device.type=='cuda' for p in model.parameters())
    append(a.work/'loads.jsonl',dict(mode=a.mode,arm=a.arm,seconds=time.perf_counter()-begin,revision=c.REVISION,
                                    gpu=torch.cuda.get_device_name(),context_tokens=length,quantized=False,CPU_offload=False))
    return model,tok,FastLanguageModel,torch

def adapt(model,Fast,config,work):
    training=config['training']
    model=Fast.get_peft_model(model,r=training['lora_r'],lora_alpha=training['lora_alpha'],lora_dropout=0,bias='none',
        target_modules=training['target_modules'],use_gradient_checkpointing=True,random_state=config['seed'],use_rslora=False,
        finetune_vision_layers=False,finetune_language_layers=True)
    named={n:p for n,p in model.named_parameters() if p.requires_grad}
    assert named and all('lora_' in n for n in named) and not any('visual' in n or 'vision' in n for n in named)
    count=sum(p.numel() for p in named.values())
    assert count==training['expected_trainable_parameters'],('LoRA coverage differs from 103',count)
    bs=[p for n,p in named.items() if 'lora_B' in n]
    assert bs and all(int(p.detach().count_nonzero())==0 for p in bs),'Fresh standard LoRA-B initialization required'
    c.put(work/'adapter_setup.json',dict(trainable_parameters=count,only_LoRA=True,vision_frozen=True,
                                        original_base_revision=c.REVISION,initialized_from_103_adapter=False))
    Fast.for_training(model);return model

def tensor_batch(tok,row,torch):
    encoded=encode(tok,row)
    return dict(input_ids=torch.tensor([encoded['input_ids']],dtype=torch.long,device='cuda'),
                attention_mask=torch.ones((1,len(encoded['input_ids'])),dtype=torch.long,device='cuda'),
                groups=torch.tensor([encoded['groups']],dtype=torch.long,device='cuda')),encoded

def fingerprint(a):
    return dict(arm=a.arm,config_sha256=c.sha(a.bundle/'frozen/config.json'),
                training_file_sha256=c.sha(a.bundle/'data/train'/(a.arm+'.jsonl')),
                bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'))

def train(a,config,model,tok,Fast,torch):
    from loss105 import backbone_loss
    import checkpoint105 as ckpt
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    work=a.work/'train'/a.arm;work.mkdir(parents=True,exist_ok=True)
    rows=c.rows(a.bundle/'data/train'/(a.arm+'.jsonl'));by_id={r['id']:r for r in rows}
    expected_lengths={r['id']:r for r in c.rows(a.bundle/'frozen/train_token_lengths.jsonl') if r['arm']==a.arm}
    plan=training_plan([r['id'] for r in rows],config['training']['epochs'],config['training']['gradient_accumulation'])
    if len(plan)!=50 or plan[-1]['consumed']!=392:raise ValueError('Frozen train196/two epochs schedule mismatch')
    fp=fingerprint(a)
    if (work/'training_done.json').exists():
        done=c.read(work/'training_done.json');assert done['fingerprint']==fp and done['step']==len(plan)
        return
    if (work/'resume.json').exists() and not a.resume:raise ValueError('Existing task105 state: explicitly --resume, never restart from base')
    model=adapt(model,Fast,config,work)
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=config['training']['learning_rate'],betas=tuple(config['training']['betas']),
                               eps=config['training']['eps'],weight_decay=0.)
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda step:1.)
    step=consumed=0
    if a.resume:
        def restore(folder):set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
        step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore)
    else:ckpt.save(model,optimizer,scheduler,work,0,0,fp)
    remaining=validate_cursor(plan,step,consumed)
    for entry in remaining:
        if STOP:raise InterruptedError('Stop before optimizer boundary; last complete checkpoint retained')
        budget.require(a.ledger,120,watchdog=True)
        optimizer.zero_grad(set_to_none=True);begin=time.perf_counter();losses=[];positions=0;tokens=0
        torch.cuda.reset_peak_memory_stats()
        for identifier in entry['ids']:
            batch,encoded=tensor_batch(tok,by_id[identifier],torch)
            expected=expected_lengths[identifier]
            assert encoded['prompt_token_sha256']==expected['prompt_token_sha256'] and encoded['answer_sha256']==expected['answer_sha256']
            with torch.autocast('cuda',dtype=torch.bfloat16):
                loss,info=backbone_loss(model,batch,config['training']['head_chunk_tokens'])
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite segmented loss')
            (loss/entry['loss_divisor']).backward();losses.append(float(loss.detach()));positions+=info['projected_positions'];tokens+=len(encoded['input_ids'])
            del loss,batch
        norm=torch.nn.utils.clip_grad_norm_(params,config['training']['gradient_clip'])
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite adapter gradient')
        optimizer.step();scheduler.step();torch.cuda.synchronize()
        # Commit every complete optimizer step. Never checkpoint partial gradient
        # accumulation with advanced RNG but unchanged consumed-sample position.
        save_begin=time.perf_counter();folder=ckpt.save(model,optimizer,scheduler,work,entry['step'],entry['consumed'],fp)
        append(work/'steps.jsonl',dict(step=entry['step'],epoch=entry['epoch'],consumed=entry['consumed'],ids=entry['ids'],
            microbatches=len(entry['ids']),loss_divisor=entry['loss_divisor'],loss=sum(losses)/len(losses),lr=optimizer.param_groups[0]['lr'],
            tokens=tokens,answer_projected_positions=positions,seconds=time.perf_counter()-begin,checkpoint_seconds=time.perf_counter()-save_begin,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),one_backbone_forward_per_microbatch=True))
    state=c.read(work/'resume.json')
    assert state['step']==len(plan) and state['consumed']==392
    updated=sum(int(p.detach().count_nonzero())>0 for n,p in model.named_parameters() if p.requires_grad and 'lora_B' in n)
    assert updated>0,'No LoRA-B update'
    c.put(work/'training_done.json',dict(step=state['step'],consumed=state['consumed'],epochs=2,final_slot=state['slot'],fingerprint=fp,
                                        chosen_by='fixed_final_epoch_not_evaluation',scheduler_last_epoch=scheduler.last_epoch,updated_lora_B_tensors=updated))

def evaluate(a,config,model,tok,Fast,torch):
    if a.arm!='base_judge':
        from peft import PeftModel
        work=a.work/'train'/a.arm;done=c.read(work/'training_done.json');pointer=c.read(work/'resume.json')
        assert done['step']==50 and done['consumed']==392 and pointer['slot']==done['final_slot']
        assert done['fingerprint']==fingerprint(a)
        folder=work/pointer['slot'];complete=c.read(folder/'checkpoint_complete.json')
        assert c.sha(folder/'checkpoint_complete.json')==pointer['complete_sha256']
        for name,sha in complete['files'].items():assert c.sha(folder/name)==sha
        model=PeftModel.from_pretrained(model,folder,is_trainable=False)
    Fast.for_inference(model);model.eval()
    rows={r['id']:r for r in c.rows(a.bundle/'data/eval_inputs.jsonl')}
    lengths={r['id']:r for r in c.rows(a.bundle/'frozen/eval_token_lengths.jsonl')}
    batches=c.read(a.bundle/'frozen/eval_batches.json')['batches']
    work=a.work/'eval'/a.arm;work.mkdir(parents=True,exist_ok=True)
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    eos=tok.convert_tokens_to_ids('<|im_end|>')
    for entry in batches:
        path=work/f"batch-{entry['batch']:04d}.json"
        if path.exists():
            saved=c.read(path);assert saved['ids']==entry['ids'] and saved['bundle_sha256']==c.sha(a.bundle/'manifest.json')
            continue # includes bad/truncated first answers, never content retries
        if STOP:raise InterruptedError('Preserve complete inference batches')
        budget.require(a.ledger,120,watchdog=True)
        sequences=[]
        for identifier in entry['ids']:
            ids=shared.prompt_ids(tok,rows[identifier]);assert c.digest(c.canonical(ids))==lengths[identifier]['prompt_token_sha256'];sequences.append(ids)
        maximum=max(map(len,sequences))
        inputs=torch.tensor([[pad]*(maximum-len(ids))+ids for ids in sequences],device='cuda')
        mask=torch.tensor([[0]*(maximum-len(ids))+[1]*len(ids) for ids in sequences],device='cuda')
        attempt=work/f"batch-{entry['batch']:04d}.inflight.json"
        if attempt.exists():append(work/'recovery_events.jsonl',dict(batch=entry['batch'],prior_uncommitted_attempt=True,previous_answer_not_available=True,utc=c.utc()))
        c.put(attempt,dict(ids=entry['ids'],utc=c.utc(),bundle_sha256=c.sha(a.bundle/'manifest.json')))
        torch.cuda.synchronize();begin=time.perf_counter();torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            result=model.generate(input_ids=inputs,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
                max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
        torch.cuda.synchronize();seconds=time.perf_counter()-begin;records=[]
        for index,identifier in enumerate(entry['ids']):
            tail=result[index,maximum:].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            content=tok.decode(tail,skip_special_tokens=True)
            records.append(dict(id=identifier,arm=a.arm,prompt_token_sha256=lengths[identifier]['prompt_token_sha256'],input_tokens=len(sequences[index]),
                                output_tokens=len(tail),finish_reason=finish,content=content,parsed=parse(content,finish)))
        c.put(path,dict(ids=entry['ids'],bundle_sha256=c.sha(a.bundle/'manifest.json'),batch_seconds=seconds,
                       peak_allocated_bytes=torch.cuda.max_memory_allocated(),records=records))
        attempt.unlink()

def gate(a,config,model,tok,Fast,torch):
    from loss105 import backbone_loss
    training=c.rows(a.bundle/'data/train/evidence_brief.jsonl')
    lengths=c.rows(a.bundle/'frozen/train_token_lengths.jsonl')
    longest=max((r for r in lengths if r['arm']=='evidence_brief'),key=lambda r:r['total_tokens'])['id']
    work=a.work/'gate';work.mkdir(exist_ok=True)
    model=adapt(model,Fast,config,work);row=next(r for r in training if r['id']==longest)
    batch,encoded=tensor_batch(tok,row,torch);torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
    with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_loss(model,batch,config['training']['head_chunk_tokens'])
    loss.backward();torch.cuda.synchronize()
    finite=bool(torch.isfinite(loss)) and all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None)
    assert finite
    nonzero_grad=sum(bool(p.grad.count_nonzero()) for p in model.parameters() if p.requires_grad and p.grad is not None)
    assert nonzero_grad>0,'No adapter gradient through the selected backbone path'
    train_peak=torch.cuda.max_memory_allocated();train_seconds=time.perf_counter()-begin
    model.zero_grad(set_to_none=True);del loss,batch;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
    eval_rows={r['id']:r for r in c.rows(a.bundle/'data/eval_inputs.jsonl')}
    longest_batch=c.read(a.bundle/'frozen/eval_batches.json')['batches'][-1]
    # Use the longest FULL batch when the last group is a short tail.
    candidates=[b for b in c.read(a.bundle/'frozen/eval_batches.json')['batches'] if len(b['ids'])==8]
    if candidates:longest_batch=max(candidates,key=lambda b:b['max_input_tokens'])
    sequences=[shared.prompt_ids(tok,eval_rows[i]) for i in longest_batch['ids']];maximum=max(map(len,sequences));pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    ids=torch.tensor([[pad]*(maximum-len(s))+s for s in sequences],device='cuda');mask=torch.tensor([[0]*(maximum-len(s))+[1]*len(s) for s in sequences],device='cuda')
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():model.generate(input_ids=ids,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=4,use_cache=True,pad_token_id=pad)
    torch.cuda.synchronize()
    c.put(a.work/'gpu_gate.json',dict(status='PASS_training_path',bundle_sha256=c.sha(a.bundle/'manifest.json'),
        longest_train_tokens=len(encoded['input_ids']),seconds=time.perf_counter()-begin,finite_loss_and_gradients=True,
        training_seconds=train_seconds,training_peak_allocated_bytes=train_peak,
        nonzero_adapter_gradient_tensors=nonzero_grad,
        inference_batch_size=len(sequences),inference_max_input=maximum,inference_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        head_projection=info,optimizer_updates=0,probe_not_reused_for_training=True,
        full_384_decode_memory_and_average_formal_throughput_not_yet_verified=True))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--mode',choices=['gate','train','eval'],required=True);p.add_argument('--arm',choices=c.ARMS,default='base_judge');p.add_argument('--resume',action='store_true')
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True);verify_bundle(a.bundle)
    config=c.read(a.bundle/'frozen/config.json')
    if a.mode=='train' and a.arm=='base_judge':p.error('base_judge is never trained')
    if a.mode!='gate':
        check=c.read(a.work/'gpu_gate.json');assert check['status']=='PASS_training_path' and check['bundle_sha256']==c.sha(a.bundle/'manifest.json')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    lock=a.work/'gpu_worker.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        model,tok,Fast,torch=load(a,config)
        if a.mode=='gate':gate(a,config,model,tok,Fast,torch)
        elif a.mode=='train':train(a,config,model,tok,Fast,torch)
        else:evaluate(a,config,model,tok,Fast,torch)
    finally:lock.unlink()

if __name__=='__main__':main()
