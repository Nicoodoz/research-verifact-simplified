"""Native verdict/reason diagnostic only; never changes a verdict or trains."""
from pathlib import Path
import argparse,json,os,re,signal,sys,time
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/103_lora_selection'))
from prompt103 import messages
from parse103 import parse_content
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as common
STOP=False

def prompt_ids(tokenizer,row):
    return tokenizer.apply_chat_template(messages(row['claim'],row['reference'],'native'),
        tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')

def parse_pair(content,finish):
    """Format checks only: consistency/faithfulness require later source review."""
    parsed=parse_content(content,finish)
    match=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',content,re.S|re.I)
    text=match[1] if match else content
    try:obj=json.loads(text)
    except (ValueError,TypeError):obj={}
    reason=obj.get('reason') if isinstance(obj,dict) else None
    return dict(verdict=parsed.get('verdict'),reason=reason if isinstance(reason,str) else None,
        label_parse_valid=parsed['valid'],diagnostic_pair_valid=bool(parsed['valid'] and
            isinstance(reason,str) and reason.strip() and finish=='stop'),
        reason_label_consistency='UNREVIEWED',input_support='UNREVIEWED',
        reason_from_same_generation=True,verdict_modified=False)

def stop(*_):
    global STOP
    STOP=True

def run(job,session_path):
    proof=job.get('final369_proof')
    if not proof or proof.get('steps')!=369 or proof.get('consumed')!=2945:
        raise ValueError('Bind a genuinely completed120 final369 checkpoint before any GPU work')
    assert [a['mode'] for a in job['arms']]==['base','adapter','adapter']
    session=common.read(session_path)
    start=time.time();deadline=min(session['start_epoch']+session['duration_seconds'],start+job['phase_limit_seconds'])-90
    if time.time()>deadline-60:raise TimeoutError('No authorized time remains; do not load GPU')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    out=ROOT/'results/native_reason_check';out.mkdir(parents=True,exist_ok=True)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    from peft import PeftModel
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):
            return torch.full((input_ids.shape[0],),STOP or time.time()>deadline,dtype=torch.bool,device=input_ids.device)
    tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
    rows={r['id']:r for r in common.rows(ROOT/job['inputs'])}
    if len(rows)!=20 or set(rows)!=set(job['ids']):raise ValueError('Expected frozen20 diagnostic inputs')
    encoded={}
    for i in job['ids']:
        row=rows[i];assert not {'GT','sid','panel','verdict','reason','prediction'}&set(row)
        encoded[i]=prompt_ids(tokenizer,row)
        assert common.digest(common.canonical(encoded[i]))==row['expected_prompt_sha256']
        assert len(encoded[i])+768<=job['max_seq_length']
    adapted=[a for a in job['arms'] if a['mode']=='adapter']
    for arm in adapted:
        assert common.sha(Path(arm['adapter'])/'adapter_model.safetensors')==arm['adapter_sha256']
    model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=job['max_seq_length'],
        dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    first=adapted[0]
    model=PeftModel.from_pretrained(model,first['adapter'],adapter_name=first['name'],is_trainable=False)
    for arm in adapted[1:]:model.load_adapter(arm['adapter'],adapter_name=arm['name'],is_trainable=False)
    pad=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    eos=tokenizer.convert_tokens_to_ids('<|im_end|>')
    for arm in job['arms']:
        if arm['mode']=='adapter':model.set_adapter(arm['name'])
        Fast.for_inference(model);model.eval()
        for i in job['ids']:
            dest=out/arm['name']/(i+'.json');inflight=dest.with_suffix('.inflight.json')
            if dest.exists():
                saved=common.read(dest)
                assert saved['adapter_sha256']==arm['adapter_sha256']
                assert saved['prompt_token_sha256']==rows[i]['expected_prompt_sha256']
                continue # Keep every first response, including invalid ones.
            if inflight.exists():raise RuntimeError('Uncommitted earlier generation; inspect before any repeat')
            if STOP or time.time()>deadline-30:raise TimeoutError('Preserve completed first receipts')
            common.put(inflight,dict(id=i,arm=arm['name'],epoch=time.time()))
            x=torch.tensor([encoded[i]],device='cuda');mask=torch.ones_like(x)
            torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()
            # Base uses the same BF16 backbone with every adapter disabled.
            # Adapter arms activate exactly one named adapter; nothing is merged.
            with torch.inference_mode(), (model.disable_adapter() if arm['mode']=='base' else nullcontext()):
                result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,
                    num_return_sequences=1,max_new_tokens=768,repetition_penalty=1.,use_cache=True,
                    pad_token_id=pad,eos_token_id=eos,stopping_criteria=StoppingCriteriaList([Deadline()]))
            torch.cuda.synchronize();tail=result[0,len(encoded[i]):].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            if STOP or time.time()>deadline:finish='budget_stop'
            content=tokenizer.decode(tail,skip_special_tokens=True)
            common.put(dest,dict(id=i,arm=arm['name'],content=content,parsed=parse_pair(content,finish),
                finish_reason=finish,input_tokens=len(encoded[i]),output_tokens=len(tail),seconds=time.perf_counter()-began,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),adapter_sha256=arm['adapter_sha256'],
                adapter_state='all_disabled' if arm['mode']=='base' else arm['name'],
                prompt_token_sha256=rows[i]['expected_prompt_sha256']))
            inflight.unlink();del x,mask,result
    common.put(out/'complete.json',dict(N_per_arm=20,arms=[a['name'] for a in job['arms']],
        first_receipts=60,wall_seconds=time.time()-start,diagnostic_only=True,main_evaluation_unchanged=True,
        no_new_training=True,no_API=True,no_shutdown=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);parser.add_argument('--session',type=Path,required=True)
    args=parser.parse_args();run(common.read(args.job),args.session)
