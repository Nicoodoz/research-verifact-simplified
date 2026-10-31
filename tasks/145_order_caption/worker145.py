"""Native120 with the corrected sort caption; first answers only, no training."""
from pathlib import Path
import argparse,json,os,signal,subprocess,sys,time
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids
from parse105 import parse
STOP=False


def deadlines(started,session,job):
    end=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']
    if 'duration_seconds' in session:end=min(end,session['start_epoch']+session['duration_seconds'])
    return dict(global_end=end,compute_end=min(started+job['compute_limit_seconds'],end-job['save_reserve_seconds']),
                stage_end=min(started+job['compute_limit_seconds']+job['save_reserve_seconds'],end),save_reserve_seconds=job['save_reserve_seconds'])


def batches_for(ids,lengths,threshold=12701):
    order=sorted(ids,key=lambda i:(lengths[i],i));result=[];cursor=0
    while cursor<len(order):
        ids=order[cursor:cursor+(2 if lengths[order[cursor]]<=threshold else 1)]
        if max(lengths[i] for i in ids)>threshold:ids=ids[:1]
        result.append(ids);cursor+=len(ids)
    return result


def worker():
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True))
    signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    job=c.read(R/'data/job.json');session=c.read(R/'data/session.json');arm=job['arm']
    assert job['task']==145 and arm=='order_caption' and job['new_training'] is False
    out=R/'results';out.mkdir(exist_ok=True);started=time.time();timing=deadlines(started,session,job);deadline=timing['compute_end']
    c.put(out/'deadlines.json',dict(started=started,**timing))
    if time.time()+300>=deadline:raise TimeoutError('Insufficient computation and180-second global save reserve')
    fingerprint=dict(job_sha256=c.sha(R/'data/job.json'),inputs_sha256=c.sha(R/job['inputs']))
    if (out/'identity.json').exists() and c.read(out/'identity.json')!=fingerprint:raise ValueError('Changed identity')
    c.put(out/'identity.json',fingerprint)
    if (out/'inflight.json').exists():raise RuntimeError('Uncommitted request exists; preserve and inspect, never auto resend')
    def progress(stage,**extra):
        c.put(out/'progress.json',dict(task=145,arm=arm,scope=job['scope'],stage=stage,
            completed=len(list((out/arm).glob('*.json'))),expected_N=job['expected_N'],target_N=job['target_N'],prior_N=job['prior_N'],
            epoch=time.time(),compute_deadline=deadline,GPU_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,
            new_API=0,no_shutdown=True,**extra))
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
    progress('loading')
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    from peft import PeftModel
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):
            return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
    rows={r['id']:r for r in c.rows(R/job['inputs'])};lengths={r['id']:r for r in c.rows(R/'data/lengths.jsonl')}
    assert len(rows)==job['expected_N'] and set(rows)==set(lengths)==set(job['ids'])
    assert all(set(row)=={'id','claim','reference','prompt_token_sha256','source_prompt_token_sha256'} for row in rows.values())
    tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
    encoded={i:prompt_ids(tokenizer,row) for i,row in rows.items()}
    for i,ids in encoded.items():
        assert c.digest(c.canonical(ids))==rows[i]['prompt_token_sha256']==lengths[i]['prompt_token_sha256']
        assert len(ids)==lengths[i]['input_tokens'] and len(ids)+384<=16384
    model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    checkpoint=Path(job['adapter'])
    assert c.sha(checkpoint/'adapter_model.safetensors')==job['adapter_sha256']
    assert (checkpoint/'adapter_model.safetensors').stat().st_size==job['adapter_bytes']
    model=PeftModel.from_pretrained(model,job['adapter'],adapter_name=arm,is_trainable=False)
    Fast.for_inference(model);model.eval();model.requires_grad_(False);model.set_adapter(arm)
    eos=tokenizer.convert_tokens_to_ids('<|im_end|>');pad=tokenizer.pad_token_id or tokenizer.eos_token_id
    batches=job['batches'];assert sorted(i for b in batches for i in b)==sorted(rows);generated=0;seconds=0.
    for batch_no,identifiers in enumerate(batches):
        if any((out/arm/(i+'.json')).exists() for i in identifiers):raise FileExistsError('First receipt already exists')
        if STOP or time.time()+60>=deadline:raise TimeoutError('Computation limit reached; preserve receipts')
        eta=seconds/generated*(job['expected_N']-generated) if generated else None
        progress('inference',remaining_seconds=eta)
        c.put(out/'inflight.json',dict(arm=arm,ids=identifiers,epoch=time.time()))
        width=max(len(encoded[i]) for i in identifiers)
        x=torch.tensor([[pad]*(width-len(encoded[i]))+encoded[i] for i in identifiers],device='cuda')
        mask=torch.tensor([[0]*(width-len(encoded[i]))+[1]*len(encoded[i]) for i in identifiers],device='cuda')
        torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
                max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos,
                stopping_criteria=StoppingCriteriaList([Deadline()]))
        torch.cuda.synchronize();elapsed=time.perf_counter()-began;peak=torch.cuda.max_memory_allocated();records=[]
        for n,i in enumerate(identifiers):
            tail=result[n,width:].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            if finish!='stop' and (STOP or time.time()>=deadline):finish='budget_stop'
            content=tokenizer.decode(tail,skip_special_tokens=True);parsed=parse(content,finish)
            parsed['valid']=bool(parsed['valid'] and finish=='stop')
            records.append(dict(id=i,arm=arm,content=content,parsed=parsed,finish_reason=finish,
                input_tokens=len(encoded[i]),output_tokens=len(tail),prompt_token_sha256=rows[i]['prompt_token_sha256'],
                adapter_sha256=job['adapter_sha256'],source_checkpoint='120_final369',source_prompt_token_sha256=rows[i]['source_prompt_token_sha256'],seconds=elapsed/len(identifiers),batch_seconds=elapsed,
                batch_size=len(identifiers),peak_allocated_bytes=peak,epoch=time.time()))
        c.put(out/'batches'/f'{batch_no:05d}.json',dict(ids=identifiers,records=records))
        for row in records:c.put(out/arm/(row['id']+'.json'),row)
        (out/'inflight.json').unlink();generated+=len(identifiers);seconds+=elapsed;del x,mask,result
    progress('complete',remaining_seconds=0)
    c.put(out/'complete.json',dict(task=145,arm=arm,scope=job['scope'],N=generated,source_checkpoint='120_final369',
        adapter_sha256=job['adapter_sha256'],epoch=time.time(),new_training=False,new_API=0,no_shutdown=True))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',action='store_true');args=ap.parse_args()
    if args.worker:
        try:worker()
        except BaseException as error:
            c.put(R/'results/failure.json',dict(error=str(error),type=type(error).__name__,epoch=time.time(),no_shutdown=True));raise
        return
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied; no overlap')
    job=c.read(R/'data/job.json');session=c.read(R/'data/session.json');timing=deadlines(time.time(),session,job)
    if time.time()+300>=timing['compute_end']:raise RuntimeError('Insufficient computation plus180-second global save reserve')
    child=subprocess.Popen([sys.executable,'-u','-B',__file__,'--worker'],cwd=R,start_new_session=True)
    try:code=child.wait(timeout=max(1,timing['compute_end']-time.time()+45))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=30)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        code=124
    c.put(R/'controller_done.json',dict(task=145,arm=job['arm'],scope=job['scope'],exit_code=code,epoch=time.time(),no_shutdown=True))
    raise SystemExit(code)


if __name__=='__main__':main()
