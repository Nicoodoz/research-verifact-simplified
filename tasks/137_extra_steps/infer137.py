"""Transfer of the existing claim-repeat input to120; reused134 runner with explicit prefix and budget protection."""
from pathlib import Path
from contextlib import nullcontext
import argparse,json,os,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c

from parse105 import parse as parse_content
from prompt137 import prompt_ids, RESPONSE_PREFIX, configure
STOP=False

def worker():
    global STOP
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True))
    signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    job=c.read(ROOT/'data/job.json');session=c.read(ROOT/'data/session.json')
    RESPONSE_PREFIX=configure(job['variant'])
    assert job.get('response_prefix','')==RESPONSE_PREFIX
    out=ROOT/'results';out.mkdir(exist_ok=True)
    started=time.time();deadline=min(session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],started+job['phase_limit_seconds'])-session['save_reserve_seconds']
    def put_progress(stage,**extra):
        counts={a:len(list((out/a).glob('*.json'))) for a in job['arms']}
        c.put(out/'progress.json',dict(stage=stage,counts=counts,total_per_arm=job['expected_N'],epoch=time.time(),elapsed_seconds=time.time()-started,
            GPU_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,API_CNY=0,no_shutdown=True,**extra))
    if time.time()+180>=deadline:raise TimeoutError('Insufficient budget to load and save')
    fingerprint=dict(job_sha256=c.sha(ROOT/'data/job.json'),inputs_sha256=c.sha(ROOT/'data/inputs.jsonl'))
    if (out/'identity.json').exists() and c.read(out/'identity.json')!=fingerprint:raise ValueError('Existing job identity mismatch')
    c.put(out/'identity.json',fingerprint)
    if (out/'inflight.json').exists():raise RuntimeError('Uncommitted generation exists; inspect before resuming')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
    put_progress('loading')
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    from peft import PeftModel
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):
            return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
    rows={r['id']:r for r in c.rows(ROOT/job['inputs'])}
    assert len(rows)==job['expected_N']
    assert all(set(r)=={'id','claim','reference','prompt_token_sha256'} for r in rows.values())
    tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
    encoded={i:prompt_ids(tokenizer,r) for i,r in rows.items()}
    for i,ids in encoded.items():
        assert c.digest(c.canonical(ids))==rows[i]['prompt_token_sha256']
        assert len(ids)+job['generation']['max_new_tokens']<=job['max_seq_length']
    model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=job['max_seq_length'],dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    assert (Path(job['adapter'])/'adapter_model.safetensors').stat().st_size==job['adapter_bytes']
    assert c.read(Path(job['adapter'])/'checkpoint_complete.json')['files']['adapter_model.safetensors']==job['adapter_sha256']
    model=PeftModel.from_pretrained(model,job['adapter'],adapter_name='author_lora9b',is_trainable=False)
    Fast.for_inference(model);model.eval();model.requires_grad_(False)
    eos=tokenizer.convert_tokens_to_ids('<|im_end|>');pad=tokenizer.pad_token_id or tokenizer.eos_token_id
    generated=0;seconds=0.
    for phase in job['phases']:
      for arm in job['arms']:
        model.set_adapter('author_lora9b')
        order=sorted([i for i in phase['ids'] if not (out/arm/(i+'.json')).exists()],key=lambda i:(len(encoded[i]),i))
        batches=[];cursor=0
        while cursor<len(order):
            size=2 if len(encoded[order[cursor]])<=job['generation']['single_if_prompt_above'] else 1
            ids=order[cursor:cursor+size]
            if max(len(encoded[i]) for i in ids)>job['generation']['single_if_prompt_above']:ids=ids[:1]
            batches.append(ids);cursor+=len(ids)
        for identifiers in batches:
            if STOP or time.time()+60>=deadline:raise TimeoutError('Budget reserve reached; no new generation')
            eta=(seconds/generated)*(sum(not (out/a/(i+'.json')).exists() for a in job['arms'] for i in rows)) if generated else None
            put_progress('inference',arm=arm,phase=phase['name'],remaining_seconds=eta)
            c.put(out/'inflight.json',dict(arm=arm,ids=identifiers,epoch=time.time()))
            width=max(len(encoded[i]) for i in identifiers)
            x=torch.tensor([[pad]*(width-len(encoded[i]))+encoded[i] for i in identifiers],device='cuda')
            mask=torch.tensor([[0]*(width-len(encoded[i]))+[1]*len(encoded[i]) for i in identifiers],device='cuda')
            torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()
            with torch.inference_mode(),(model.disable_adapter() if arm=='author_base9b' else nullcontext()):
                result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
                    max_new_tokens=job['generation']['max_new_tokens'],repetition_penalty=1.,use_cache=True,
                    pad_token_id=pad,eos_token_id=eos,stopping_criteria=StoppingCriteriaList([Deadline()]))
            torch.cuda.synchronize();elapsed=time.perf_counter()-began;peak=torch.cuda.max_memory_allocated()
            for n,i in enumerate(identifiers):
                tail=result[n,width:].tolist();finish='length'
                if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
                if STOP or time.time()>=deadline:finish='budget_stop'
                generated_content=tokenizer.decode(tail,skip_special_tokens=True);content=RESPONSE_PREFIX+generated_content;parsed=parse_content(content,finish)
                parsed['valid']=bool(parsed['valid'] and finish=='stop')
                dest=out/arm/(i+'.json')
                if dest.exists():raise FileExistsError('Never overwrite first response')
                c.put(dest,dict(id=i,arm=arm,content=content,generated_content=generated_content,response_prefix=RESPONSE_PREFIX,parsed=parsed,finish_reason=finish,
                    input_tokens=len(encoded[i]),output_tokens=len(tail),total_answer_tokens=len(tail)+job['prefix_tokens'],prompt_token_sha256=rows[i]['prompt_token_sha256'],
                    adapter_state='all_disabled' if arm=='author_base9b' else arm,seconds=elapsed/len(identifiers),
                    batch_seconds=elapsed,batch_size=len(identifiers),peak_allocated_bytes=peak,epoch=time.time(),adapter_sha256=job['adapter_sha256'],checkpoint_step=518))
            (out/'inflight.json').unlink();generated+=len(identifiers);seconds+=elapsed
            del x,mask,result
        c.put(out/(phase['name']+'_'+arm+'_complete.json'),dict(epoch=time.time(),N=len(phase['ids'])))
    put_progress('complete',remaining_seconds=0)
    c.put(out/'complete.json',dict(epoch=time.time(),N_per_arm=job['expected_N'],new_training=False,new_API=0,no_shutdown=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:
        try:worker()
        except BaseException as e:
            c.put(ROOT/'results/failure.json',dict(type=type(e).__name__,error=str(e),epoch=time.time(),no_shutdown=True));raise
    else:
        if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
        s=c.read(ROOT/'data/session.json');remaining=s['start_epoch']+3600*s['GPU_cap_CNY']/s['hourly_CNY']-time.time()-120
        child=subprocess.Popen([sys.executable,'-u','-B',__file__,'--worker'],cwd=ROOT,start_new_session=True)
        try:code=child.wait(timeout=max(1,remaining))
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=35)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            raise TimeoutError('Budget watchdog ended only the compute process; no shutdown')
        c.put(ROOT/'controller_done.json',dict(exit_code=code,epoch=time.time(),no_shutdown=True))
        raise SystemExit(code)

if __name__=='__main__':main()
