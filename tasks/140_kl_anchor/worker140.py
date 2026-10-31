"""138 label replay with fixed120 teacher-cache KL; one student backbone pass."""
from pathlib import Path
import json,os,random,re,signal,sys,time
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
sys.path.insert(0,str(R/'tasks/107_support_aux'))
import common105 as c
from parse105 import parse
STOP=False


def unique_training_rows(rows):
    unique={}
    for row in rows:
        i=row['original_id']
        if row['kind']!='label' or not re.fullmatch(r'[A-Za-z0-9-]+',i):raise ValueError('Original label task/ID required')
        if len(row['input_ids'])!=len(row['groups']):raise ValueError('Token/group length mismatch')
        if i in unique and any(row[k]!=unique[i][k] for k in ('input_ids','groups','kind')):
            raise ValueError('Repeated ID has different original token input or labels')
        unique[i]=row
    return unique


def validate_cache_identity(manifest,identity,resuming):
    if manifest is None:
        if resuming:raise RuntimeError('Teacher cache missing during student resume; never rebuild from student')
        return
    if manifest['identity']!=identity:raise RuntimeError('Teacher source/head/data identity changed')
    if resuming and not manifest.get('complete'):raise RuntimeError('Incomplete teacher cache during student resume')


def main():
    global STOP
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True))
    signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    job=c.read(R/'data/job.json');session=c.read(R/'data/session.json')
    assert job['arm']=='kl_anchor' and job['seed']==138031
    assert job['lambda_kl']==0.5 and job['temperature']==1.0
    out=R/'results';out.mkdir(exist_ok=True);work=out/'train';work.mkdir(exist_ok=True)
    cache=out/'teacher_cache';cache.mkdir(exist_ok=True)
    start=time.time();reserve=job['save_reserve_seconds']
    global_end=min(session['start_epoch']+session['duration_seconds'],
                   session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'])
    deadline=min(start+job['phase_limit_seconds']-reserve,global_end-reserve)
    optimizer=scheduler=model=save_current=None;step=consumed=0;partial=updating=False;partial_rng=None;stage='starting'
    def budget(seconds=0):
        if STOP or time.time()+seconds>=deadline:raise TimeoutError('140 compute boundary; retain cache and complete state')
    def progress(value,n,total,eta=None):
        nonlocal stage
        stage=value;c.put(out/'progress.json',dict(stage=value,completed=n,total=total,remaining_seconds=eta,
            epoch=time.time(),GPU_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,no_shutdown=True))
    try:
        #Refuse missing/partial cache before even loading a resumed student.
        resuming=(work/'resume.json').exists();manifest_path=cache/'manifest.json'
        if resuming and (not manifest_path.exists() or not c.read(manifest_path).get('complete')):
            raise RuntimeError('A resumed140 student requires its original complete teacher cache')
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
            TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
        progress('loading',0,48);budget(120)
        from unsloth import FastLanguageModel as Fast
        import torch,numpy as np
        from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        import checkpoint107 as ckpt
        from loss140 import backbone_loss,teacher_states,sampled_head_fingerprint,label_indices
        assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        random.seed(job['seed']);np.random.seed(job['seed']);torch.manual_seed(job['seed']);torch.cuda.manual_seed_all(job['seed'])
        records=c.rows(R/'data/train_tokens.jsonl');tokens={r['sample_id']:r for r in records}
        original=c.rows(R/'data/train.jsonl');metadata={r['sample_id']:r for r in original}
        plan=c.read(R/'data/plan.json');evals={r['id']:r for r in c.rows(R/'data/eval_tokens.jsonl')}
        assert len(records)==len(tokens)==len(original)==192 and set(metadata)==set(tokens)
        assert len(plan)==48 and plan[-1]['consumed']==384 and len(evals)==160
        assert all(len(x['input_ids'])<=16384 and metadata[s]['id']==x['original_id'] and metadata[s]['kind']=='label' for s,x in tokens.items())
        unique=unique_training_rows(records);assert len(unique)==156
        assert len({str(r['sid']) for r in original})==32
        source=Path(job['source_adapter']);assert c.sha(source/'adapter_model.safetensors')==job['source_sha256']
        config=c.read(source/'adapter_config.json');assert config.get('lora_dropout',0.)==0.
        model_config=c.read(Path(job['model_dir'])/'config.json');text_config=model_config.get('text_config',model_config)
        assert text_config.get('attention_dropout',0.)==0. and text_config.get('hidden_dropout',0.)==0.
        tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
        model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,
            load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
        model=Fast.get_peft_model(model,r=config['r'],lora_alpha=config['lora_alpha'],lora_dropout=config.get('lora_dropout',0.),
            bias=config.get('bias','none'),target_modules=config['target_modules'],use_gradient_checkpointing=True,
            random_state=job['seed'],use_rslora=config.get('use_rslora',False),finetune_vision_layers=False,finetune_language_layers=True)
        def restore(folder):
            result=set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
            assert not any('lora_' in x for x in getattr(result,'missing_keys',[])) and not getattr(result,'unexpected_keys',[])
        restore(source);Fast.for_training(model)
        base=model.get_base_model();assert all(not p.requires_grad for p in base.lm_head.parameters())
        def rng():return torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate(),np.random.get_state()
        def restore_rng(state):
            torch.set_rng_state(state[0]);torch.cuda.set_rng_state_all(state[1]);random.setstate(state[2]);np.random.set_state(state[3])
        def tensor(row):
            return dict(input_ids=torch.tensor([row['input_ids']],device='cuda'),
                attention_mask=torch.ones((1,len(row['input_ids'])),dtype=torch.long,device='cuda'),
                groups=torch.tensor([row['groups']],device='cuda'))
        identity=dict(version=1,source120_sha256=job['source_sha256'],
            source_adapter_config_sha256=c.sha(source/'adapter_config.json'),
            model_config_sha256=c.sha(Path(job['model_dir'])/'config.json'),
            train_tokens_sha256=c.sha(R/'data/train_tokens.jsonl'),train_rows_sha256=c.sha(R/'data/train.jsonl'),
            plan_sha256=c.sha(R/'data/plan.json'),loss140_sha256=c.sha(Path(__file__).parent/'loss140.py'),
            sampled_frozen_head_sha256=sampled_head_fingerprint(base.lm_head),
            head_fingerprint_method='sampled up to2048 evenly spaced elements per tensor; not full head SHA',
            head_parameters=[dict(name=n,shape=list(p.shape),dtype=str(p.dtype),frozen=not p.requires_grad) for n,p in base.lm_head.named_parameters()],
            definition='full vocabulary T1, groups[t+1]==1 -> hidden[t], original output dtype',unique_IDs=sorted(unique))
        manifest=c.read(manifest_path) if manifest_path.exists() else None
        validate_cache_identity(manifest,identity,resuming)
        if manifest is None:manifest=dict(identity=identity,complete=False,files={});c.put(manifest_path,manifest)
        teacher={};cache_rng=rng();model.eval()
        try:
            for n,i in enumerate(sorted(unique)):
                budget(5);row=unique[i];batch=tensor(row);positions=label_indices(batch['groups'])[0].tolist()
                seq_sha=c.digest(c.canonical(dict(input_ids=row['input_ids'],groups=row['groups'])))
                path=cache/(i+'.pt');entry=manifest['files'].get(i)
                if entry is not None:
                    if entry['filename']!=path.name or not path.exists() or c.sha(path)!=entry['sha256']:
                        raise RuntimeError('Teacher cache file integrity failure')
                    value=torch.load(path,map_location='cpu',weights_only=True)
                    if value['original_id']!=i or value['sequence_sha256']!=seq_sha or value['hidden_indices']!=positions:
                        raise RuntimeError('Teacher cache token/causal-position mismatch')
                    state=value['hidden_states']
                else:
                    if resuming:raise RuntimeError('Missing teacher row during student resume')
                    #Still source120 weights: no optimizer or student restore yet.
                    progress('teacher_cache',n,len(unique))
                    state=teacher_states(model,batch)[0]
                    value=dict(original_id=i,sequence_sha256=seq_sha,hidden_indices=positions,
                        source120_sha256=job['source_sha256'],hidden_states=state,dtype=str(state.dtype))
                    temporary=path.with_suffix('.pt.tmp');torch.save(value,temporary);temporary.replace(path)
                    manifest['files'][i]=dict(filename=path.name,sha256=c.sha(path),dtype=str(state.dtype),shape=list(state.shape))
                    c.put(manifest_path,manifest)
                if state.requires_grad or state.ndim!=2 or state.shape[0]!=len(positions) or str(state.dtype)!=value['dtype']:
                    raise RuntimeError('Invalid detached teacher states')
                teacher[i]=state;del batch
            if set(manifest['files'])!=set(unique):raise RuntimeError('Teacher cache has extra or missing IDs')
            if not manifest['complete']:
                manifest['complete']=True;c.put(manifest_path,manifest)
        finally:
            Fast.for_training(model);restore_rng(cache_rng)
        assert len(teacher)==156
        params=[p for p in model.parameters() if p.requires_grad];assert params and all(not p.requires_grad for p in base.lm_head.parameters())
        optimizer=torch.optim.AdamW(params,lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0.)
        scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda _:1.)
        fp=dict(job=c.sha(R/'data/job.json'),data=identity['train_tokens_sha256'],train_rows=identity['train_rows_sha256'],
            plan=identity['plan_sha256'],eval=c.sha(R/'data/eval_tokens.jsonl'),source=job['source_sha256'],
            code=c.sha(Path(__file__)),loss=identity['loss140_sha256'],loss105=c.sha(R/'tasks/105_brief_supervision/loss105.py'),
            teacher_manifest=c.sha(manifest_path),sampled_frozen_head=identity['sampled_frozen_head_sha256'])
        def save():return ckpt.save(model,optimizer,scheduler,work,step,consumed,fp)
        save_current=save
        if resuming:step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore)
        else:save()
        def loss_for(row):
            batch=tensor(row)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                return backbone_loss(model,batch,teacher[row['original_id']],chunk_tokens=16,
                    lambda_kl=job['lambda_kl'],temperature=job['temperature'])
        gate=out/'gpu_gate.json'
        if gate.exists():
            if c.read(gate)['fingerprint']!=fp:raise RuntimeError('Different140 GPU gate identity')
        else:
            progress('longest_backward',step,48);partial_rng=rng();partial=True
            reserve_state=[] if optimizer.state else [torch.zeros_like(p) for p in params for _ in range(2)]
            longest=max(tokens.values(),key=lambda r:len(r['input_ids']));torch.cuda.reset_peak_memory_stats()
            loss,info=loss_for(longest)
            tolerance=job.get('initial_kl_tolerance',0.01)
            if step==0 and abs(float(info['kl']))>tolerance:
                raise RuntimeError('Initial KL exceeds declared numerical tolerance; inspect eval/train kernels and cache identity')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.);torch.cuda.synchronize()
            assert bool(torch.isfinite(loss) and torch.isfinite(norm)) and float(norm)>0
            c.put(gate,dict(tokens=len(longest['input_ids']),initial_KL=float(info['kl']),initial_KL_tolerance=tolerance,
                LoRA_and_attention_dropout_zero=True,teacher_cache_preserves_dtype=True,no_optimizer_update=True,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),gradient_norm=float(norm),fingerprint=fp))
            del reserve_state,loss;optimizer.zero_grad(set_to_none=True);restore_rng(partial_rng);partial=False;torch.cuda.empty_cache()
        train_start=time.time();start_step=step
        for item in plan[step:]:
            budget(60);partial_rng=rng();partial=True;optimizer.zero_grad(set_to_none=True);began=time.time();losses=[];ces=[];kls=[]
            for i in item['ids']:
                budget(10);loss,info=loss_for(tokens[i]);assert bool(torch.isfinite(loss))
                (loss/item['loss_divisor']).backward();losses.append(float(loss.detach()));ces.append(float(info['ce']));kls.append(float(info['kl']));del loss
            norm=torch.nn.utils.clip_grad_norm_(params,1.);assert bool(torch.isfinite(norm))
            updating=True;optimizer.step();scheduler.step();torch.cuda.synchronize();updating=partial=False
            step,consumed=item['step'],item['consumed']
            if step%16==0 or step==48:save()
            with (out/'steps.jsonl').open('ab') as stream:
                stream.write((c.canonical(dict(step=step,consumed=consumed,ids=item['ids'],loss=sum(losses)/len(losses),
                    ce=sum(ces)/len(ces),kl=sum(kls)/len(kls),gradient_norm=float(norm),seconds=time.time()-began))+'\n').encode());stream.flush()
            progress('training',step,48,(time.time()-train_start)/max(1,step-start_step)*(48-step)+500)
        pointer=c.read(work/'resume.json');assert (pointer['step'],pointer['consumed'])==(48,384)
        final=work/pointer['slot'];sha=c.read(final/'checkpoint_complete.json')['files']['adapter_model.safetensors']
        c.put(out/'training_done.json',dict(steps=48,consumed=384,final_checkpoint=str(final),adapter_sha256=sha,
            epoch=time.time(),arm=job['arm'],teacher_manifest_sha256=fp['teacher_manifest'],source120_sha256=job['source_sha256']))
        optimizer.zero_grad(set_to_none=True);optimizer=scheduler=None;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
        class Deadline(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):
                return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
        eos=tokenizer.convert_tokens_to_ids('<|im_end|>');pad=tokenizer.pad_token_id or tokenizer.eos_token_id
        order=sorted(evals,key=lambda i:(len(evals[i]['input_ids']),i));done=0
        for n in range(0,len(order),2):
            ids=order[n:n+2];path=out/'batches'/f'{n//2:04d}.json'
            if path.exists():
                old=c.read(path);assert old['ids']==ids and all(r['adapter_sha256']==sha for r in old['records'])
                for row in old['records']:
                    dest=out/'predictions'/(row['id']+'.json')
                    if dest.exists():assert c.read(dest)==row
                    else:c.put(dest,row)
                if (out/'inflight.json').exists() and c.read(out/'inflight.json')['ids']==ids:(out/'inflight.json').unlink()
                done+=len(ids);continue
            if (out/'inflight.json').exists():raise RuntimeError('Uncommitted evaluation first request; no automatic resend')
            budget(30);progress('evaluation',done,160);width=max(len(evals[i]['input_ids']) for i in ids)
            c.put(out/'inflight.json',dict(ids=ids,adapter_sha256=sha,epoch=time.time()))
            x=torch.tensor([[pad]*(width-len(evals[i]['input_ids']))+evals[i]['input_ids'] for i in ids],device='cuda')
            mask=torch.tensor([[0]*(width-len(evals[i]['input_ids']))+[1]*len(evals[i]['input_ids']) for i in ids],device='cuda')
            with torch.inference_mode():result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,
                num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos,
                stopping_criteria=StoppingCriteriaList([Deadline()]))
            records=[]
            for j,i in enumerate(ids):
                tail=result[j,width:].tolist();finish='length'
                if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
                if STOP or time.time()>=deadline:finish='budget_stop'
                content=tokenizer.decode(tail,skip_special_tokens=True);parsed=parse(content,finish);parsed['valid']=bool(parsed['valid'] and finish=='stop')
                records.append(dict(id=i,arm=job['arm'],content=content,finish_reason=finish,parsed=parsed,
                    input_tokens=len(evals[i]['input_ids']),prompt_token_sha256=evals[i]['prompt_token_sha256'],adapter_sha256=sha))
            c.put(path,dict(ids=ids,records=records))
            for row in records:c.put(out/'predictions'/(row['id']+'.json'),row)
            (out/'inflight.json').unlink();done+=len(ids);del x,mask,result
        assert done==160;c.put(out/'complete.json',dict(N=160,steps=48,consumed=384,epoch=time.time(),arm=job['arm'],no_shutdown=True));progress('complete',160,160,0)
    except BaseException as error:
        save_error=None
        if optimizer is not None and save_current is not None and not updating:
            try:
                if partial and partial_rng is not None:restore_rng(partial_rng)
                optimizer.zero_grad(set_to_none=True);save_current()
            except BaseException as problem:save_error=repr(problem)
        c.put(out/'failure.json',dict(stage=stage,error=repr(error),step=step,consumed=consumed,
            checkpoint_error=save_error,epoch=time.time(),no_shutdown=True));raise


if __name__=='__main__':main()
