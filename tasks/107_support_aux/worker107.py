"""Supplied Linux GPU worker; importing/help never loads9B or touches CUDA."""
from pathlib import Path
import argparse
import hashlib
import os
import platform
import random
import signal
import sys
import time
import common107 as c
sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
from data105 import encode,shared,training_plan,validate_cursor
from parse105 import parse
from run107 import require_budget,verify_authorization,verify_bundle

STOP=False


def stopped(sig,frame):
    global STOP
    STOP=True


def append(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('ab') as stream:
        stream.write((c.canonical(value)+'\n').encode('utf-8'));stream.flush();os.fsync(stream.fileno())


def parameter_digest(named):
    h=hashlib.sha256()
    for name,p in sorted(named):
        h.update(name.encode());h.update(str(tuple(p.shape)).encode());h.update(str(p.dtype).encode())
        h.update(p.detach().cpu().contiguous().view(-1).view(__import__('torch').uint8).numpy().tobytes())
    return h.hexdigest()


def state_digest(value):
    """Exact optimizer/scheduler state digest, including scalar/group settings."""
    import torch
    h=hashlib.sha256()
    def add(item):
        if torch.is_tensor(item):
            h.update(str(item.dtype).encode());h.update(str(tuple(item.shape)).encode())
            h.update(item.detach().cpu().contiguous().view(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item,key=str):h.update(repr(key).encode());add(item[key])
        elif isinstance(item,(list,tuple)):
            h.update(type(item).__name__.encode())
            for part in item:add(part)
        else:h.update(repr(item).encode())
    add(value);return h.hexdigest()


def rng_digest(torch):
    import numpy as np
    h=hashlib.sha256(torch.get_rng_state().numpy().tobytes())
    for state in torch.cuda.get_rng_state_all():h.update(state.cpu().numpy().tobytes())
    h.update(repr(random.getstate()).encode());state=np.random.get_state()
    h.update(state[0].encode());h.update(state[1].tobytes());h.update(repr(state[2:]).encode())
    return h.hexdigest()


def load(a,config):
    require_budget(a.ledger,120);pre=c.read(a.work/'preflight107.json')
    if not pre.get('all_weights_SHA_match') or pre['bundle_sha256']!=c.sha(a.bundle/'manifest.json') or pre['model_dir']!=str(a.model_dir.resolve()):raise ValueError('Current exact original-base preflight required')
    if config['revision']!=c.REVISION or (a.model_dir/'adapter_config.json').exists():raise ValueError('Original frozen9B base required')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from unsloth import FastLanguageModel
    import numpy as np
    import torch
    from transformers import AutoTokenizer
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise RuntimeError('BF16 CUDA required; no CPU/quantized fallback')
    random.seed(config['seed']);np.random.seed(config['seed']);torch.manual_seed(config['seed']);torch.cuda.manual_seed_all(config['seed'])
    summary=c.read(a.bundle/'frozen/tokenizer_summary.json')
    for name,wanted in summary['tokenizer_files'].items():
        if c.sha(a.model_dir/name)!=wanted:raise ValueError('Tokenizer file mismatch: '+name)
    tok=AutoTokenizer.from_pretrained(str(a.model_dir),trust_remote_code=False,local_files_only=True)
    begin=time.perf_counter()
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model_dir),max_seq_length=summary['required_context_tokens'],dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    if getattr(model,'is_loaded_in_4bit',False) or getattr(model,'is_loaded_in_8bit',False) or any(p.device.type!='cuda' for p in model.parameters()):raise RuntimeError('Quantization/offload differs from105')
    append(a.work/'loads.jsonl',dict(mode=a.mode,arm=a.arm,seconds=time.perf_counter()-begin,
        revision=c.REVISION,gpu=torch.cuda.get_device_name(),context_tokens=summary['required_context_tokens'],quantized=False,CPU_offload=False))
    return model,tok,FastLanguageModel,torch


def adapt(model,Fast,config,work):
    tr=config['training']
    model=Fast.get_peft_model(model,r=tr['lora_r'],lora_alpha=tr['lora_alpha'],lora_dropout=tr['lora_dropout'],bias=tr['bias'],
        target_modules=tr['target_modules'],use_gradient_checkpointing=tr['gradient_checkpointing'],random_state=config['seed'],
        use_rslora=tr['use_rslora'],finetune_vision_layers=False,finetune_language_layers=True)
    named=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if not named or any('lora_' not in n or 'vision' in n or 'visual' in n for n,p in named):raise ValueError('Unexpected trainable backbone parameter')
    count=sum(p.numel() for n,p in named)
    if count!=tr['expected_trainable_parameters']:raise ValueError('LoRA coverage differs from105: '+str(count))
    bs=[p for n,p in named if 'lora_B' in n]
    if not bs or any(int(p.detach().count_nonzero()) for p in bs):raise ValueError('Both arms must start fresh zero LoRA-B')
    initial=parameter_digest(named)
    Fast.for_training(model)
    import torch
    c.put(work/'adapter_setup.json',dict(trainable_parameters=count,only_LoRA=True,vision_frozen=True,
        original_base_revision=c.REVISION,fresh_original_base=True,initial_LoRA_sha256=initial,initial_RNG_sha256=rng_digest(torch)))
    return model,initial


def hidden_size(model):
    config=model.config
    return int(getattr(getattr(config,'text_config',config),'hidden_size'))


def make_head(model,config,arm):
    if arm=='label_only':return None
    from loss107 import make_aux_head
    aux=config['training']['auxiliary']
    if aux['weight']!=1. or aux['positive_label']!='Supported' or aux['representation']!='prompt_last':raise ValueError('Frozen auxiliary specification changed')
    import torch
    before=rng_digest(torch);head=make_aux_head(hidden_size(model),aux['head_seed'],device='cuda')
    if rng_digest(torch)!=before:raise RuntimeError('Auxiliary initialization advanced shared global RNG')
    return head


def tensor_batch(tok,row,torch):
    e=encode(tok,row)
    return dict(input_ids=torch.tensor([e['input_ids']],dtype=torch.long,device='cuda'),
        attention_mask=torch.ones((1,len(e['input_ids'])),dtype=torch.long,device='cuda'),
        groups=torch.tensor([e['groups']],dtype=torch.long,device='cuda'),
        prompt_tokens=e['prompt_tokens'],support_target=int(row['GT']=='Supported')),e


def fingerprint(a):
    return dict(arm=a.arm,config_sha256=c.sha(a.bundle/'frozen/config.json'),
        training_file_sha256=c.sha(a.bundle/'data/train'/(a.arm+'.jsonl')),bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'))


def optimizer_for(model,head,config,torch):
    params=[p for p in model.parameters() if p.requires_grad]+(list(head.parameters()) if head is not None else [])
    tr=config['training']
    optimizer=torch.optim.AdamW(params,lr=tr['learning_rate'],betas=tuple(tr['betas']),eps=tr['eps'],weight_decay=tr['weight_decay'])
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda step:1.)
    return params,optimizer,scheduler


def train(a,config,model,tok,Fast,torch):
    from loss107 import backbone_loss
    import checkpoint107 as ckpt
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    work=a.work/'train'/a.arm;work.mkdir(parents=True,exist_ok=True);fp=fingerprint(a)
    rows=c.rows(a.bundle/'data/train'/(a.arm+'.jsonl'));by_id={r['id']:r for r in rows}
    expected={r['id']:r for r in c.rows(a.bundle/'frozen/train_token_lengths.jsonl') if r['arm']==a.arm}
    plan=training_plan([r['id'] for r in rows],config['training']['epochs'],config['training']['gradient_accumulation'])
    if len(rows)!=196 or len(plan)!=50 or plan[-1]['consumed']!=392 or [p['loss_divisor'] for p in plan if p['epoch_end']]!=[4,4]:raise ValueError('Original196 two-epoch tail schedule changed')
    if (work/'training_done.json').exists():
        d=c.read(work/'training_done.json')
        if d['fingerprint']!=fp or d['step']!=50:raise ValueError('Wrong training completion')
        return
    if (work/'resume.json').exists() and not a.resume:raise ValueError('Existing committed state requires --resume, never silently retrain')
    model,initial=adapt(model,Fast,config,work)
    expected_init=c.read(a.work/'gpu_gate.json')['initial_LoRA_sha256']
    if initial!=expected_init:raise ValueError('Fresh arm initialization differs from GPU gate/original base')
    if c.read(work/'adapter_setup.json')['initial_RNG_sha256']!=c.read(a.work/'gpu_gate.json')['initial_RNG_sha256']:raise ValueError('Fresh arm shared RNG differs from GPU gate')
    other=next(arm for arm in c.ARMS if arm!=a.arm);other_init=a.work/'train'/other/'adapter_setup.json'
    if other_init.exists() and c.read(other_init)['initial_LoRA_sha256']!=initial:raise ValueError('Arms have unequal initial LoRA')
    head=make_head(model,config,a.arm);params,optimizer,scheduler=optimizer_for(model,head,config,torch)
    step=consumed=0
    if a.resume:
        def restore(folder):set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
        step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore,aux_head=head)
    else:ckpt.save(model,optimizer,scheduler,work,0,0,fp,aux_head=head)
    for entry in validate_cursor(plan,step,consumed):
        if STOP:raise InterruptedError('Stopped before optimizer boundary; committed state remains')
        require_budget(a.ledger,120);optimizer.zero_grad(set_to_none=True);begin=time.perf_counter();losses=[];mains=[];auxs=[];tokens=positions=0
        torch.cuda.reset_peak_memory_stats()
        for identifier in entry['ids']:
            if STOP:raise InterruptedError('Partial accumulation discarded; previous complete boundary remains')
            require_budget(a.ledger,90);batch,e=tensor_batch(tok,by_id[identifier],torch);wanted=expected[identifier]
            if e['prompt_token_sha256']!=wanted['prompt_token_sha256'] or e['answer_sha256']!=wanted['answer_sha256']:raise ValueError('Training input differs from freeze')
            with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_loss(model,batch,aux_head=head,chunk_tokens=config['training']['head_chunk_tokens'])
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite loss')
            (loss/entry['loss_divisor']).backward();losses.append(float(loss.detach()));mains.append(info['main_loss']);auxs.append(info['aux_loss'])
            tokens+=len(e['input_ids']);positions+=info['projected_positions'];del batch,loss
        norm=torch.nn.utils.clip_grad_norm_(params,config['training']['gradient_clip'])
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite gradient')
        optimizer.step();scheduler.step();torch.cuda.synchronize();save_begin=time.perf_counter()
        ckpt.save(model,optimizer,scheduler,work,entry['step'],entry['consumed'],fp,aux_head=head)
        append(work/'steps.jsonl',dict(step=entry['step'],epoch=entry['epoch'],consumed=entry['consumed'],ids=entry['ids'],
            microbatches=len(entry['ids']),loss_divisor=entry['loss_divisor'],loss=sum(losses)/len(losses),main_loss=sum(mains)/len(mains),
            aux_loss=sum(auxs)/len(auxs),aux_weight=1 if head is not None else 0,lr=optimizer.param_groups[0]['lr'],tokens=tokens,
            answer_projected_positions=positions,seconds=time.perf_counter()-begin,checkpoint_seconds=time.perf_counter()-save_begin,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),one_backbone_forward_per_microbatch=True))
    pointer=c.read(work/'resume.json')
    if pointer['step']!=50 or pointer['consumed']!=392:raise ValueError('Training ended before fixed final step')
    updated=sum(int(p.detach().count_nonzero())>0 for n,p in model.named_parameters() if p.requires_grad and 'lora_B' in n)
    if updated==0:raise RuntimeError('No LoRA-B update')
    c.put(work/'training_done.json',dict(step=50,consumed=392,epochs=2,final_slot=pointer['slot'],fingerprint=fp,
        chosen_by='fixed_final_epoch_not_evaluation',initial_LoRA_sha256=initial,aux_head_saved=head is not None,
        scheduler_last_epoch=scheduler.last_epoch,updated_lora_B_tensors=updated))


def evaluate(a,config,model,tok,Fast,torch):
    from peft import PeftModel
    train_work=a.work/'train'/a.arm;done=c.read(train_work/'training_done.json');pointer=c.read(train_work/'resume.json')
    if done['step']!=50 or done['consumed']!=392 or done['fingerprint']!=fingerprint(a) or pointer['slot']!=done['final_slot']:raise ValueError('Fixed final trained adapter required')
    folder=train_work/pointer['slot'];complete=c.read(folder/'checkpoint_complete.json')
    if c.sha(folder/'checkpoint_complete.json')!=pointer['complete_sha256']:raise ValueError('Incomplete adapter checkpoint')
    for name,wanted in complete['files'].items():
        if c.sha(folder/name)!=wanted:raise ValueError('Checkpoint SHA mismatch')
    # The auxiliary head is deliberately never loaded into inference.
    model=PeftModel.from_pretrained(model,folder,is_trainable=False);Fast.for_inference(model);model.eval()
    rows={r['id']:r for r in c.rows(a.bundle/'data/eval_inputs.jsonl')}
    lengths={r['id']:r for r in c.rows(a.bundle/'frozen/eval_token_lengths.jsonl')}
    batches=c.read(a.bundle/'frozen/eval_batches.json')['batches'];work=a.work/'eval'/a.arm/'development';work.mkdir(parents=True,exist_ok=True)
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>')
    for entry in batches:
        path=work/f"batch-{entry['batch']:04d}.json"
        if path.exists():
            saved=c.read(path)
            if saved['ids']!=entry['ids'] or saved['bundle_sha256']!=c.sha(a.bundle/'manifest.json'):raise ValueError('Existing first receipt mismatched')
            continue
        if STOP:raise InterruptedError('Inference stopped; preserve every first receipt')
        require_budget(a.ledger,120);sequences=[]
        for identifier in entry['ids']:
            ids=shared.prompt_ids(tok,rows[identifier])
            if c.digest(c.canonical(ids))!=lengths[identifier]['prompt_token_sha256']:raise ValueError('Inference prompt SHA mismatch')
            sequences.append(ids)
        maximum=max(map(len,sequences));inputs=torch.tensor([[pad]*(maximum-len(s))+s for s in sequences],device='cuda')
        mask=torch.tensor([[0]*(maximum-len(s))+[1]*len(s) for s in sequences],device='cuda')
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
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),aux_head_used=False,records=records));attempt.unlink()
    c.put(work/'evaluation_done.json',dict(bundle_sha256=c.sha(a.bundle/'manifest.json'),received=sum(len(c.read(work/f"batch-{b['batch']:04d}.json")['records']) for b in batches),aux_head_used=False))


def _hidden(model,batch):
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    result=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
    return result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]


def memory_margin(torch,minimum=268435456):
    free,total=torch.cuda.mem_get_info();reserved=torch.cuda.memory_reserved();allocated=torch.cuda.memory_allocated()
    external=max(0,total-free-reserved);peak=torch.cuda.max_memory_allocated()
    margin=total-external-peak
    result=dict(device_total_bytes=total,device_free_bytes=free,current_allocated_bytes=allocated,
        current_reserved_bytes=reserved,peak_allocated_bytes=peak,peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        estimated_non_allocator_bytes=external,peak_allocated_headroom_bytes=margin,minimum_headroom_bytes=minimum)
    if margin<minimum:raise RuntimeError('Measured peak leaves less than256MiB physical GPU headroom')
    return result


def gate(a,config,model,tok,Fast,torch):
    """Disposable real9B checks; no probe update is reused as formal training."""
    from loss107 import backbone_loss,auxiliary_hidden_loss
    import checkpoint107 as ckpt
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    work=a.work/'gate';work.mkdir(exist_ok=True);model,initial=adapt(model,Fast,config,work);head=make_head(model,config,'support_aux')
    params,optimizer,scheduler=optimizer_for(model,head,config,torch)
    rows=c.rows(a.bundle/'data/train/label_only.jsonl');lengths=[r for r in c.rows(a.bundle/'frozen/train_token_lengths.jsonl') if r['arm']=='label_only']
    by={r['id']:r for r in rows};ordered=sorted(lengths,key=lambda r:r['total_tokens']);short=ordered[0];long=ordered[-1]
    batch,e=tensor_batch(tok,by[short['id']],torch);model.eval()
    with torch.no_grad(),torch.autocast('cuda',dtype=torch.bfloat16):
        before=_hidden(model,batch)[0,e['prompt_tokens']-1].clone()
        changed=dict(batch,input_ids=batch['input_ids'].clone())
        changed['input_ids'][:,e['prompt_tokens']:]=torch.roll(changed['input_ids'][:,e['prompt_tokens']:],1,dims=1)
        after=_hidden(model,changed)[0,e['prompt_tokens']-1].clone()
        prefix=dict(batch,input_ids=batch['input_ids'][:,:e['prompt_tokens']],attention_mask=batch['attention_mask'][:,:e['prompt_tokens']])
        prompt_only=_hidden(model,prefix)[0,-1].clone()
    difference=float((before.float()-after.float()).abs().max())
    if not torch.allclose(before,after,rtol=1e-5,atol=1e-5):raise RuntimeError('Answer suffix changes prompt representation: leakage gate failed')
    prefix_difference=float((before.float()-prompt_only.float()).abs().max())
    if not torch.allclose(before,prompt_only,rtol=.01,atol=.01):raise RuntimeError('Prompt-only/full-sequence prefix bridge failed')
    del before,after,changed,prompt_only,prefix;model.train();optimizer.zero_grad(set_to_none=True)
    with torch.autocast('cuda',dtype=torch.bfloat16):aux_loss,aux_info=auxiliary_hidden_loss(_hidden(model,batch),head,batch)
    aux_loss.backward();torch.cuda.synchronize()
    aux_grad=sum(bool(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.count_nonzero()) for n,p in model.named_parameters() if p.requires_grad and 'lora_' in n)
    aux_B_grad=sum(bool(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.count_nonzero()) for n,p in model.named_parameters() if p.requires_grad and 'lora_B' in n)
    if aux_grad==0 or aux_B_grad==0 or not all(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.count_nonzero() for p in head.parameters()):raise RuntimeError('Auxiliary-only gradient does not reach LoRA-B/head')
    del aux_loss,batch;optimizer.zero_grad(set_to_none=True);timings=[]
    for record in (ordered[len(ordered)//2],long):
        require_budget(a.ledger,120);batch,e=tensor_batch(tok,by[record['id']],torch);torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
        with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_loss(model,batch,aux_head=head,chunk_tokens=config['training']['head_chunk_tokens'])
        loss.backward();torch.cuda.synchronize()
        if not torch.isfinite(loss) or not all(torch.isfinite(p.grad).all() for p in params if p.grad is not None):raise FloatingPointError('Nonfinite real9B loss/gradient')
        timings.append(dict(tokens=len(e['input_ids']),seconds=time.perf_counter()-begin,peak_allocated_bytes=torch.cuda.max_memory_allocated()))
        del loss,batch;optimizer.zero_grad(set_to_none=True)
    # A disposable optimizer update populates Adam moments for genuine restore.
    batch,e=tensor_batch(tok,by[short['id']],torch)
    with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,aux_head=head,chunk_tokens=config['training']['head_chunk_tokens'])
    loss.backward();torch.nn.utils.clip_grad_norm_(params,1.);torch.cuda.synchronize();optimizer_begin=time.perf_counter()
    optimizer.step();scheduler.step();torch.cuda.synchronize();optimizer_seconds=time.perf_counter()-optimizer_begin;optimizer.zero_grad(set_to_none=True)
    probe_fp=dict(task=107,disposable_probe=True,bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'))
    checkpoint_begin=time.perf_counter();ckpt.save(model,optimizer,scheduler,work/'restore_probe',1,1,probe_fp,aux_head=head)
    checkpoint_seconds=time.perf_counter()-checkpoint_begin
    expected=parameter_digest([(n,p) for n,p in model.named_parameters() if p.requires_grad]+[('aux.'+n,p) for n,p in head.named_parameters()])
    expected_rng=rng_digest(torch);expected_optimizer=state_digest(optimizer.state_dict());expected_scheduler=state_digest(scheduler.state_dict())
    def next_probe_step():
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.bfloat16):probe_loss,_=backbone_loss(model,batch,aux_head=head,chunk_tokens=config['training']['head_chunk_tokens'])
        if not torch.isfinite(probe_loss):raise FloatingPointError('Nonfinite restore continuation loss')
        probe_loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite restore continuation gradient')
        optimizer.step();scheduler.step();optimizer.zero_grad(set_to_none=True)
        return (parameter_digest([(n,p) for n,p in model.named_parameters() if p.requires_grad]+[('aux.'+n,p) for n,p in head.named_parameters()]),
            state_digest(optimizer.state_dict()),state_digest(scheduler.state_dict()),rng_digest(torch))
    uninterrupted_next=next_probe_step()
    with torch.no_grad():
        for p in params:p.add_(1.)
        for state in optimizer.state.values():
            for value in state.values():
                if torch.is_tensor(value):value.add_(3.)
    scheduler.last_epoch=999
    import numpy as np
    torch.rand(5,device='cuda');torch.rand(5);random.random();np.random.rand()
    def restore(folder):set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
    step,consumed,_=ckpt.load(optimizer,scheduler,work/'restore_probe',probe_fp,restore,aux_head=head)
    current_params=[p for p in model.parameters() if p.requires_grad]+list(head.parameters())
    if {id(p) for g in optimizer.param_groups for p in g['params']}!={id(p) for p in current_params}:raise RuntimeError('Optimizer parameter bindings changed on restore')
    actual=parameter_digest([(n,p) for n,p in model.named_parameters() if p.requires_grad]+[('aux.'+n,p) for n,p in head.named_parameters()])
    restored=(actual==expected and state_digest(optimizer.state_dict())==expected_optimizer and state_digest(scheduler.state_dict())==expected_scheduler
        and step==consumed==1 and rng_digest(torch)==expected_rng)
    if not restored:raise RuntimeError('Real9B LoRA/head/Adam/scheduler/RNG restore failed')
    repeated_next=next_probe_step()
    next_step_exact=repeated_next==uninterrupted_next
    # BF16 GPU backward is not bitwise deterministic. The preserved5090
    # disk-repeat/in-memory diagnosis has exact initial state and identical
    # loss, with equal-scale numerical variation in both restore paths.
    # Exact LOAD, optimizer binding and finite continuation remain mandatory;
    # next-step bitwise equality is reported rather than claimed or required.
    if any(not torch.isfinite(p).all() for p in params):raise FloatingPointError('Nonfinite restored continuation parameters')
    del loss,batch
    # Recheck the longest full training row WITH populated Adam moments. The
    # initial backward alone omits optimizer-state residency on a32GB card.
    optimizer.zero_grad(set_to_none=True);batch,e=tensor_batch(tok,by[long['id']],torch)
    torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();begin=time.perf_counter()
    with torch.autocast('cuda',dtype=torch.bfloat16):long_loss,_=backbone_loss(model,batch,aux_head=head,chunk_tokens=config['training']['head_chunk_tokens'])
    long_loss.backward();torch.cuda.synchronize()
    if not torch.isfinite(long_loss) or not all(torch.isfinite(p.grad).all() for p in params if p.grad is not None):raise FloatingPointError('Longest row with Adam residency has nonfinite gradients')
    train_memory=memory_margin(torch)
    timings.append(dict(tokens=len(e['input_ids']),seconds=time.perf_counter()-begin,peak_allocated_bytes=torch.cuda.max_memory_allocated(),populated_Adam_resident=True))
    del long_loss,batch;model.zero_grad(set_to_none=True)
    # Inference does not retain an auxiliary head, gradients or Adam state.
    del next_probe_step,optimizer,scheduler,head,params
    import gc
    gc.collect();torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
    # No selection-case answer is generated by this technical probe. Repeated
    # training tokens supply the maximum formal input length and full384 decode.
    batches=c.read(a.bundle/'frozen/eval_batches.json')['batches'];batch_size=config['evaluation']['batch_size']
    if batch_size not in (1,2,8) or any(len(b['ids'])>batch_size for b in batches):raise ValueError('Evaluation batch exceeds frozen configured size')
    contexts=sorted(b['max_input_tokens'] for b in batches);max_eval=contexts[-1]
    train_ids=shared.prompt_ids(tok,by[long['id']]);pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    prefill=[];decode=[];inference_memory=None
    for target in sorted({contexts[0],contexts[len(contexts)//2],max_eval}):
        probe=(train_ids*((target+len(train_ids)-1)//len(train_ids)))[:target]
        ids=torch.tensor([probe]*batch_size,device='cuda');mask=torch.ones_like(ids)
        # Warm this input shape separately so JIT is charged in elapsed billing,
        # without treating one-off compilation as steady inference throughput.
        lengths=(4,4,128,384) if target==max_eval else (4,4)
        for ordinal,output_length in enumerate(lengths):
            require_budget(a.ledger,180);torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();begin=time.perf_counter()
            with torch.inference_mode():
                result=model.generate(input_ids=ids,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
                    max_new_tokens=output_length,min_new_tokens=output_length,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=tok.convert_tokens_to_ids('<|im_end|>'))
            torch.cuda.synchronize();elapsed=time.perf_counter()-begin
            if result.shape[1]-target!=output_length:raise RuntimeError('Full fixed-length technical decode incomplete')
            record=dict(input_tokens=target,batch_size=batch_size,output_tokens_each=output_length,seconds=elapsed,peak_allocated_bytes=torch.cuda.max_memory_allocated())
            if ordinal==1:prefill.append(record)
            if ordinal>1:decode.append(record)
            if output_length==384:inference_memory=memory_margin(torch)
            del result
        del ids,mask
    infer_seconds=decode[-1]['seconds'];infer_peak=decode[-1]['peak_allocated_bytes']
    old=c.read(a.bundle/'frozen/cost_estimate.json');throughput=sum(r['tokens'] for r in timings)/sum(r['seconds'] for r in timings)
    from cost107 import measured_remaining
    measured=measured_remaining(old['train_tokens_each'],timings,checkpoint_seconds,optimizer_seconds,prefill,decode,batches,config)
    c.put(a.work/'gpu_gate.json',dict(status='PASS',bundle_sha256=c.sha(a.bundle/'manifest.json'),initial_LoRA_sha256=initial,
        initial_RNG_sha256=c.read(work/'adapter_setup.json')['initial_RNG_sha256'],head_initialization_global_RNG_unchanged=True,
        causal_answer_suffix_max_abs_difference=difference,prompt_only_vs_full_max_abs_difference=prefix_difference,
        prompt_only_BF16_bridge_tolerance=dict(atol=.01,rtol=.01),auxiliary_only_LoRA_gradient_tensors=aux_grad,auxiliary_only_LoRA_B_gradient_tensors=aux_B_grad,
        real_restore_LoRA_head_Adam_scheduler_all_RNG_verified=restored,next_optimizer_step_exactly_matches_uninterrupted=next_step_exact,
        continuation_comparison='exact_checkpoint_load_and_bindings; finite_next_step; GPU_BF16_bitwise_variation_reported',
        continuation_hash_equal_by_component={name:a==b for name,a,b in zip(('parameters','optimizer','scheduler','RNG'),uninterrupted_next,repeated_next)},
        disposable_probe_optimizer_updates_executed=3,formal_optimizer_updates=0,
        training_probes=timings,measured_training_tokens_per_second=throughput,
        training_slowdown_vs105=old['measured_training_tokens_per_second105']/throughput,
        historical_A800_speed_ratio_not_used_for_current_budget=True,inference_batch_size=batch_size,inference_input_tokens=max_eval,
        training_memory_with_Adam_resident=train_memory,inference_memory=inference_memory,
        measured_run_estimate_seconds=measured,
        forced_decode_probes=decode,full384_decode_seconds=infer_seconds,inference_peak_allocated_bytes=infer_peak,
        forced_prefill_probes=prefill,budget_formula=measured['formula'],
        full384_is_memory_gate_and_incremental_decode_timing_not_A800_batch8_ratio=True,
        inference_probe='repeated_training_tokens_full384_not_selection_predictions',probe_not_reused_for_training=True,CPU_tests_not_efficacy=True))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','work','model-dir','ledger','session'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=['gate','train','eval'],required=True);p.add_argument('--arm',choices=c.ARMS,required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--execute-rented-gpu',action='store_true');a=p.parse_args()
    if not a.execute_rented_gpu or platform.system()!='Linux':raise PermissionError('Only the handed-off Linux rented instance may execute GPU')
    verify_bundle(a.bundle);verify_authorization(a.bundle,a.session);config=c.read(a.bundle/'frozen/config.json')
    if a.mode!='gate':
        gate_record=c.read(a.work/'gpu_gate.json');budget=c.read(a.work/'whole_run_budget_gate.json')
        if gate_record['status']!='PASS' or gate_record['bundle_sha256']!=c.sha(a.bundle/'manifest.json') or not budget['fits_complete_frozen_run']:raise ValueError('Real GPU and whole-budget gates must pass')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped);a.work.mkdir(parents=True,exist_ok=True);lock=a.work/'gpu_worker.lock'
    if lock.exists():
        pid=int(lock.read_text());cmdline=Path('/proc')/str(pid)/'cmdline'
        if cmdline.exists() and b'worker107.py' in cmdline.read_bytes():raise RuntimeError('Another107 GPU worker is live')
        lock.unlink()
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        model,tok,Fast,torch=load(a,config)
        if a.mode=='gate':gate(a,config,model,tok,Fast,torch)
        elif a.mode=='train':train(a,config,model,tok,Fast,torch)
        else:evaluate(a,config,model,tok,Fast,torch)
    finally:lock.unlink()


if __name__=='__main__':main()
