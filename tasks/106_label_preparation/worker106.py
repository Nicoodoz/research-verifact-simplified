"""Future GPU entry. Import/help is inert; no cloud, API, download or CPU 9B path."""
from pathlib import Path
import argparse
import os
import random
import signal
import time
import sys
import platform
import common106 as c
sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
from run106 import require_budget,verify_bundle,verify_authorization
from data105 import encode,shared,training_plan,validate_cursor
from parse105 import parse

STOP=False
def stopped(sig,frame):
    global STOP
    STOP=True

def append(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('ab') as f:f.write((c.canonical(value)+'\n').encode('utf-8'));f.flush();os.fsync(f.fileno())

def load(a,config):
    require_budget(a.ledger,120)
    preflight=c.read(a.work/'preflight106.json')
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
    expected_runtime=c.read(a.bundle/'frozen/expected_runtime105.json')
    authorization=verify_authorization(a.bundle,a.authorization)
    current_gpu=torch.cuda.get_device_name()
    if authorization['baseline_cache_mode']=='reuse' and current_gpu!=expected_runtime['GPU_name']:
        raise RuntimeError('105 baseline cache invalid on this GPU; obtain explicit rerun authorization and account for extra baseline500 cost before any training')
    cross_hardware=current_gpu!=expected_runtime['GPU_name']
    if cross_hardware and authorization.get('accept_cross_hardware_training_diagnostic_only') is not True:
        raise PermissionError('Rerun aligns inference only; frozen mean training used105 A800. Explicit cross-hardware-diagnostic-only authorization is required; no automatic mean retraining.')
    random.seed(config['seed']);np.random.seed(config['seed']);torch.manual_seed(config['seed']);torch.cuda.manual_seed_all(config['seed'])
    if (a.model_dir/'adapter_config.json').exists():raise ValueError('Do not initialize from the 103 adapter')
    for name,sha in c.read(a.bundle/'frozen/tokenizer_summary.json')['tokenizer_files'].items():assert c.sha(a.model_dir/name)==sha,name
    length=c.read(a.bundle/'frozen/tokenizer_summary.json')['required_context_tokens']
    # Longer training rows do not silently change the cached baseline's model
    # loading/context condition for development evaluation.
    if a.mode=='eval' and a.panel=='development':length=c.read(a.bundle/'frozen/baseline_token_summary.json')['required_context_tokens']
    tok=AutoTokenizer.from_pretrained(str(a.model_dir),trust_remote_code=False,local_files_only=True)
    begin=time.perf_counter()
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model_dir),max_seq_length=length,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    assert not getattr(model,'is_loaded_in_4bit',False) and not getattr(model,'is_loaded_in_8bit',False)
    assert all(p.device.type=='cuda' for p in model.parameters())
    append(a.work/'loads.jsonl',dict(mode=a.mode,arm=a.arm,seconds=time.perf_counter()-begin,revision=c.REVISION,
                                    gpu=torch.cuda.get_device_name(),context_tokens=length,quantized=False,CPU_offload=False,
                                    training_hardware_comparison='non_strict_training_hardware_comparison' if cross_hardware else 'same_GPU_family_and_pinned_backend'))
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
    from loss106 import backbone_sum_loss
    import checkpoint105 as ckpt
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    work=a.work/'train'/a.arm;work.mkdir(parents=True,exist_ok=True)
    if a.arm!='label_sum':raise ValueError('label_mean is the frozen105 control adapter, never retrained')
    rows=c.rows(a.bundle/'data/train'/(a.arm+'.jsonl'));by_id={r['id']:r for r in rows}
    expected_lengths={r['id']:r for r in c.rows(a.bundle/'frozen/train_token_lengths.jsonl') if r['arm']==a.arm}
    plan=training_plan([r['id'] for r in rows],config['training']['epochs'],config['training']['gradient_accumulation'])
    expected_steps=((len(rows)+config['training']['gradient_accumulation']-1)//config['training']['gradient_accumulation'])*config['training']['epochs']
    if len(rows)!=196 or len(plan)!=expected_steps or plan[-1]['consumed']!=len(rows)*config['training']['epochs']:raise ValueError('Frozen train196 schedule mismatch')
    fp=fingerprint(a)
    if (work/'training_done.json').exists():
        done=c.read(work/'training_done.json');assert done['fingerprint']==fp and done['step']==len(plan)
        return
    if (work/'resume.json').exists() and not a.resume:raise ValueError('Existing task106 state: explicitly --resume, never restart from base')
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
        require_budget(a.ledger,120)
        optimizer.zero_grad(set_to_none=True);begin=time.perf_counter();losses=[];positions=0;tokens=0
        torch.cuda.reset_peak_memory_stats()
        for identifier in entry['ids']:
            batch,encoded=tensor_batch(tok,by_id[identifier],torch)
            expected=expected_lengths[identifier]
            assert encoded['prompt_token_sha256']==expected['prompt_token_sha256'] and encoded['answer_sha256']==expected['answer_sha256']
            with torch.autocast('cuda',dtype=torch.bfloat16):
                loss,info=backbone_sum_loss(model,batch,config['training']['value_token_mean_normalizer'],config['training']['head_chunk_tokens'])
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
    assert state['step']==len(plan) and state['consumed']==len(rows)*config['training']['epochs']
    updated=sum(int(p.detach().count_nonzero())>0 for n,p in model.named_parameters() if p.requires_grad and 'lora_B' in n)
    assert updated>0,'No LoRA-B update'
    c.put(work/'training_done.json',dict(step=state['step'],consumed=state['consumed'],epochs=config['training']['epochs'],final_slot=state['slot'],fingerprint=fp,
                                        chosen_by='fixed_final_epoch_not_evaluation',scheduler_last_epoch=scheduler.last_epoch,updated_lora_B_tensors=updated))

def evaluate(a,config,model,tok,Fast,torch):
    if a.arm!='base_judge':
        from peft import PeftModel
        if a.arm=='label_mean':
            folder=a.bundle/'control/label_mean/checkpoint_a'
            for name,sha in c.read(a.bundle/'frozen/mean_control_adapter.json')['files'].items():
                if c.sha(folder/name)!=sha:raise ValueError('Frozen105 mean control adapter changed')
        else:
            work=a.work/'train'/a.arm;done=c.read(work/'training_done.json');pointer=c.read(work/'resume.json')
            assert done['step']==50 and done['consumed']==392 and pointer['slot']==done['final_slot']
            assert done['fingerprint']==fingerprint(a)
            folder=work/pointer['slot'];complete=c.read(folder/'checkpoint_complete.json')
            assert c.sha(folder/'checkpoint_complete.json')==pointer['complete_sha256']
            for name,sha in complete['files'].items():assert c.sha(folder/name)==sha
        model=PeftModel.from_pretrained(model,folder,is_trainable=False)
    Fast.for_inference(model);model.eval()
    prefix='eval' if a.panel=='development' else 'diagnostic'
    file='eval_inputs.jsonl' if a.panel=='development' else 'diagnostic_inputs.jsonl'
    rows={r['id']:r for r in c.rows(a.bundle/'data'/file)}
    lengths={r['id']:r for r in c.rows(a.bundle/'frozen'/(prefix+'_token_lengths.jsonl'))}
    batches=c.read(a.bundle/'frozen'/(prefix+'_batches.json'))['batches']
    work=a.work/'eval'/a.arm/a.panel;work.mkdir(parents=True,exist_ok=True)
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    eos=tok.convert_tokens_to_ids('<|im_end|>')
    for entry in batches:
        path=work/f"batch-{entry['batch']:04d}.json"
        if path.exists():
            saved=c.read(path);assert saved['ids']==entry['ids'] and saved['bundle_sha256']==c.sha(a.bundle/'manifest.json')
            continue # includes bad/truncated first answers, never content retries
        if STOP:raise InterruptedError('Preserve complete inference batches')
        require_budget(a.ledger,120)
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
    if a.panel=='diagnostic':
        from loss106 import complete_path_scores
        label_maps=c.read(a.bundle/'frozen/tokenizer_labels.json')['labels']
        eos=tok.convert_tokens_to_ids('<|im_end|>')
        paths={label:tok.encode(c.canonical({'verdict':label}),add_special_tokens=False)+[eos] for label in c.LABELS}
        branch_ids={'S_token':label_maps['Supported']['verdict_ids'][0],'Not_token':label_maps['Not Supported']['verdict_ids'][0]}
        first=label_maps['Supported']['verdict_indices'][0]
        for identifier,row in rows.items():
            score_path=work/'complete_label_paths'/(identifier+'.json')
            if score_path.exists():
                existing=c.read(score_path)
                assert existing['bundle_sha256']==c.sha(a.bundle/'manifest.json') and existing['arm']==a.arm and existing['id']==identifier
                continue
            require_budget(a.ledger,120)
            ids=shared.prompt_ids(tok,row)
            scores=complete_path_scores(model,ids,paths,first,branch_ids,'cuda',config['training']['head_chunk_tokens'])
            c.put(score_path,dict(id=identifier,arm=a.arm,prompt_token_sha256=lengths[identifier]['prompt_token_sha256'],
                bundle_sha256=c.sha(a.bundle/'manifest.json'),scoring_context='canonical_label_only_JSON_prefix_not_free_greedy_interface',**scores))

def gate(a,config,model,tok,Fast,torch):
    from loss106 import backbone_sum_loss
    training=c.rows(a.bundle/'data/train'/('label_mean.jsonl'))+c.rows(a.bundle/'data/train'/('label_sum.jsonl'))
    lengths=c.rows(a.bundle/'frozen/train_token_lengths.jsonl')
    longest=max(lengths,key=lambda r:r['total_tokens'])['id']
    work=a.work/'gate';work.mkdir(exist_ok=True)
    model=adapt(model,Fast,config,work);row=next(r for r in training if r['id']==longest)
    batch,encoded=tensor_batch(tok,row,torch);torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
    with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_sum_loss(model,batch,config['training']['value_token_mean_normalizer'],config['training']['head_chunk_tokens'])
    loss.backward();torch.cuda.synchronize()
    finite=bool(torch.isfinite(loss)) and all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None)
    assert finite
    nonzero_grad=sum(bool(p.grad.count_nonzero()) for p in model.parameters() if p.requires_grad and p.grad is not None)
    assert nonzero_grad>0,'No adapter gradient through the selected backbone path'
    train_peak=torch.cuda.max_memory_allocated();train_seconds=time.perf_counter()-begin
    model.zero_grad(set_to_none=True);del loss,batch;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
    eval_rows={r['id']:r for r in c.rows(a.bundle/'data/eval_inputs.jsonl')+c.rows(a.bundle/'data/diagnostic_inputs.jsonl')}
    # Training diagnostics can be longer than development500. Gate the longest
    # complete batch over BOTH input sets; never assume development is longest.
    candidates=[]
    for prefix in ('eval','diagnostic'):
        for b in c.read(a.bundle/'frozen'/(prefix+'_batches.json'))['batches']:
            candidates.append(dict(b,panel=prefix))
    full=[b for b in candidates if len(b['ids'])==8]
    longest_batch=max(full or candidates,key=lambda b:b['max_input_tokens'])
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
        inference_panel=longest_batch['panel'],both_development_and_training_diagnostic_batches_considered=True,
        head_projection=info,optimizer_updates=0,probe_not_reused_for_training=True,
        full_384_decode_memory_and_average_formal_throughput_not_yet_verified=True))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--mode',choices=['gate','train','eval'],required=True);p.add_argument('--arm',choices=['base_judge','label_mean','label_sum'],default='base_judge');p.add_argument('--resume',action='store_true')
    p.add_argument('--panel',choices=['development','diagnostic'],default='development')
    p.add_argument('--authorization',type=Path,required=True);p.add_argument('--execute-authorized-gpu',action='store_true')
    # No model library is imported, directory created or GPU touched until a
    # future explicit user authorization binds this exact frozen package.
    a=p.parse_args()
    if not a.execute_authorized_gpu:raise PermissionError('A new explicit GPU authorization is required')
    if platform.system()!='Linux':raise RuntimeError('Future GPU worker is Linux-only')
    verify_authorization(a.bundle,a.authorization)
    a.work.mkdir(parents=True,exist_ok=True);verify_bundle(a.bundle)
    config=c.read(a.bundle/'frozen/config.json')
    if a.mode=='train' and a.arm!='label_sum':p.error('Only label_sum is newly trained; base and frozen mean control are not')
    if a.mode!='gate':
        check=c.read(a.work/'gpu_gate.json');assert check['status']=='PASS_training_path' and check['bundle_sha256']==c.sha(a.bundle/'manifest.json')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    lock=a.work/'gpu_worker.lock'
    if lock.exists():
        pid=int(lock.read_text());cmdline=Path('/proc')/str(pid)/'cmdline'
        if cmdline.exists() and b'worker106.py' in cmdline.read_bytes():raise RuntimeError('Another106 GPU worker is live')
        lock.unlink() # only our verified stale lock; no checkpoint/result removed
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        model,tok,Fast,torch=load(a,config)
        if a.mode=='gate':gate(a,config,model,tok,Fast,torch)
        elif a.mode=='train':train(a,config,model,tok,Fast,torch)
        else:evaluate(a,config,model,tok,Fast,torch)
    finally:lock.unlink()

if __name__=='__main__':main()
