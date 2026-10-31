"""Explicit future paired generation; importing/help performs no GPU work."""
from pathlib import Path
import argparse
import hashlib
import json
import signal
import subprocess
import sys
import time
import os

STOP=False


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(v,ensure_ascii=False)+'\n',encoding='utf-8');tmp.replace(p)
def append(p,v):
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps(v)+'\n');f.flush()


def run(bundle):
    global STOP
    bundle=Path(bundle).resolve();job=read(bundle/'data/job.json');session=read(bundle/job['session']);start=time.time()
    end=min(session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],
            session['start_epoch']+session.get('duration_seconds',float('inf')))
    deadline=min(start+job['compute_limit_seconds'],end-job['save_reserve_seconds'],job.get('absolute_compute_deadline',float('inf')))
    if time.time()+300>=deadline:raise TimeoutError('Insufficient original authorized window')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
        raise RuntimeError('GPU occupied; no overlap')
    out=bundle.parent/'results';out.mkdir(exist_ok=True)
    if (out/'inflight.json').exists():raise RuntimeError('Inspect uncommitted prior call; no automatic resend')
    identity=dict(job_sha256=sha(bundle/'data/job.json'),input_sha256=sha(bundle/job['input']))
    if (out/'identity.json').exists() and read(out/'identity.json')!=identity:raise ValueError('Changed frozen identity')
    put(out/'identity.json',identity)
    for rel,h in job['source_files_sha256'].items():
        if sha(bundle/rel)!=h:raise ValueError('Bundled code changed')
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True));signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
    for sub in ('104_supervision_evidence','136_claim_repeat_transfer','105_brief_supervision','144_native_confidence'):
        sys.path.insert(0,str(bundle/'tasks'/sub))
    import common105 as c
    import training104,prompt136
    from parse105 import parse
    from capture_native_score import NativeBranchCapture,CANONICAL_PREFIX,BRANCH_TOKENS
    from unsloth import FastLanguageModel as Fast
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList,LogitsProcessorList
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):
            return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
    records={(r['variant'],r['id']):r for r in map(json.loads,(bundle/job['input']).read_text().splitlines())}
    selection={(r['variant'],r['id']):r for r in map(json.loads,(bundle/job['selection']).read_text().splitlines())}
    tok=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
    if tuple(tok.encode('{"verdict":"',add_special_tokens=False))!=CANONICAL_PREFIX:raise ValueError('Prefix tokenizer changed')
    if (tok.encode('Supported',add_special_tokens=False)[0],tok.encode('Not Supported',add_special_tokens=False)[0])!=BRANCH_TOKENS:
        raise ValueError('Branch token identities changed')
    encoded={}
    for key,r in records.items():
        ids=(training104 if key[0]=='native120' else prompt136).prompt_ids(tok,r)
        if len(ids)!=r['expected_prompt_tokens'] or c.digest(c.canonical(ids))!=r['expected_prompt_token_sha256']:
            raise ValueError('Original prompt differs')
        if len(ids)+384>16384:raise ValueError('Input exceeds fixed complete context')
        encoded[key]=ids
    if sha(Path(job['adapter'])/'adapter_model.safetensors')!=job['adapter_sha256']:raise ValueError('Wrong120 adapter')
    model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    model=PeftModel.from_pretrained(model,job['adapter'],adapter_name='source120',is_trainable=False)
    Fast.for_inference(model);model.eval();model.requires_grad_(False);model.set_adapter('source120')
    eos=tok.convert_tokens_to_ids('<|im_end|>');pad=tok.pad_token_id or tok.eos_token_id
    put(out/'runtime.json',dict(worker_started_epoch=start,preparation_and_load_seconds=time.time()-start))
    for call in job['calls']:
        key=(call['variant'],call['id']);path=out/call['variant']/call['mode']/(call['id']+'.json')
        if path.exists():
            if read(path).get('job_sha256')!=identity['job_sha256']:raise ValueError('Wrong prior first answer identity')
            continue
        if STOP or time.time()+45>=deadline:raise TimeoutError('Stop before next first call')
        observer=NativeBranchCapture(len(encoded[key]),[call['id']]) if call['mode']=='capture' else None
        x=torch.tensor([encoded[key]],device='cuda');mask=torch.ones_like(x)
        event=dict(call,epoch=time.time());put(out/'inflight.json',event);append(out/'attempts.jsonl',dict(event,event='started'))
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();began=time.perf_counter()
        with torch.inference_mode():
            result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
                max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos,
                stopping_criteria=StoppingCriteriaList([Deadline()]),return_dict_in_generate=True,
                output_logits=True,output_scores=False,
                logits_processor=LogitsProcessorList([observer] if observer else []))
        torch.cuda.synchronize();seconds=time.perf_counter()-began
        sequences=result.sequences if hasattr(result,'sequences') else result
        tail=sequences[0,len(encoded[key]):].tolist();finish='length'
        if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
        if finish!='stop' and (STOP or time.time()>=deadline):finish='budget_stop'
        content=tok.decode(tail,skip_special_tokens=True);parsed=parse(content,finish)
        parsed['valid']=bool(parsed['valid'] and finish=='stop')
        canonical=tuple(tail[:4])==CANONICAL_PREFIX
        raw=None
        if canonical and getattr(result,'logits',None) is not None and len(result.logits)>4:
            pair=result.logits[4][0,list(BRANCH_TOKENS)].detach().float().cpu().tolist()
            raw=dict(S=pair[0],Not=pair[1])
        capture=observer.records()[0] if observer else None
        difference=None
        if raw is not None and capture and capture['status']=='captured':
            difference=max(abs(raw[g]-capture['branch_logits'][g]) for g in ('S','Not'))
        record=dict(call,job_sha256=identity['job_sha256'],adapter_sha256=job['adapter_sha256'],
            prompt_token_sha256=records[key]['expected_prompt_token_sha256'],input_tokens=len(encoded[key]),
            content=content,content_sha256=hashlib.sha256(content.encode()).hexdigest(),
            generated_token_sha256=c.digest(c.canonical(tail)),output_tokens=len(tail),parsed=parsed,finish_reason=finish,
            generation_seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            actual_canonical_prefix=canonical,raw_branch_logits=raw,capture=capture,processor_vs_raw_max_abs_difference=difference,
            raw_logits_returned=raw is not None,
            matches_original_cached_label=parsed.get('verdict')==selection[key]['original_prediction'],
            matches_original_cached_content=hashlib.sha256(content.encode()).hexdigest()==selection[key]['original_content_sha256'],
            audit_output_logits=True,no_vocabulary_arrays_saved=True)
        put(path,record);append(out/'attempts.jsonl',dict(event,event='completed',seconds=seconds,epoch=time.time()))
        (out/'inflight.json').unlink();del result,x,mask,observer
    put(out/'complete.json',dict(expected_calls=24,worker_started_epoch=start,worker_completed_epoch=time.time(),
                                worker_wall_seconds=time.time()-start,no_shutdown=True))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true')
    parser.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    if not args.execute:print('Prepared only; explicit future execution required');return
    start=time.time()
    try:run(args.bundle)
    finally:put(args.bundle.resolve().parent/'results/run_exit.json',dict(started=start,ended=time.time(),wall_seconds=time.time()-start))


if __name__=='__main__':main()
