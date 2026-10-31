"""Generate a short rationale conditional on a frozen model verdict, without GT."""
from pathlib import Path
import os,sys,json,time,signal,subprocess,hashlib
R=Path(__file__).resolve().parent
BASE=Path('/root/autodl-tmp')
SOURCE=BASE/'verifact136_claim_repeat_full1817'
for sub in ('104_supervision_evidence','105_brief_supervision','136_claim_repeat_transfer'):
    sys.path.insert(0,str(SOURCE/'tasks'/sub))
import common105 as c
from prompt136 import messages
STOP=False
LABELS=('Supported','Not Supported','Not Addressed')
FOLLOWUP='The verdict in the preceding assistant message is fixed. Do not reclassify it or change it. Give one sentence of at most 35 words stating the minimum decisive reference evidence for that verdict. Supported means the assertion is fully supported. Not Supported means it is addressed but contradicted or only partly supported. Not Addressed means the specific assertion is not addressed; it does not mean the patient lacks that fact. Do not confuse partial support with not addressed. Omit unnecessary details and dates. Only when a date is essential to explaining a temporal assertion, copy its exact original representation from the reference, including deidentified years and brackets; never convert, normalize, infer or replace a year. Do not invent facts, quotations, or causal or temporal connections. Explain the evidence direction rather than repeating a label or adding a conclusion to an opposite explanation. If no honest short explanation in the fixed direction can be given, return status "unable" and reason null. Return only JSON: {"status":"explained","reason":"brief reason"} or {"status":"unable","reason":null}.'

def prepare():
    if (R/'inputs.jsonl').exists():return
    allrows={};pred={}
    for scope in ('screen160','old500','full1817'):
        p=BASE/('verifact136_claim_repeat_'+scope)
        for row in c.rows(p/'data/inputs.jsonl'):
            allrows[row['id']]=dict(id=row['id'],claim=row['claim'],reference=row['reference'])
        for f in (p/'results/claim_repeat').glob('*.json'):
            row=c.read(f)
            if row.get('parsed',{}).get('valid'):pred[row['id']]=row['parsed']['verdict']
    assert len(allrows)==1817 and len(pred)==1817
    selected=[]
    for g in LABELS:
        ids=sorted([i for i in pred if pred[i]==g],key=lambda i:hashlib.sha256(('fixed_reason|'+i).encode()).hexdigest())[:20]
        assert len(ids)==20
        for i in ids:selected.append(dict(allrows[i],fixed_verdict=pred[i]))
    assert all(set(r)=={'id','claim','reference','fixed_verdict'} for r in selected)
    c.putl(R/'inputs.jsonl',selected)
    c.put(R/'selection.json',dict(N=60,by_predicted_class={g:20 for g in LABELS},ids=[r['id'] for r in selected],
         GT_used=False,rule='smallest20 SHA256(fixed_reason|ID) within each136 predicted label',prepared_epoch=time.time()))

def main():
    global STOP
    R.mkdir(parents=True,exist_ok=True);prepare()
    if '--prepare-only' in sys.argv:print(json.dumps(c.read(R/'selection.json')));return
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True));signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    started=time.time();session=c.read(BASE/'verifact146_caption_transfer/data/session.json')
    deadline=min(started+900,session['end_epoch']-180)
    O=R/'results';O.mkdir(exist_ok=True)
    if (O/'inflight.json').exists():raise RuntimeError('Preserve prior uncommitted attempt')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR=str(BASE/'verifact134/cache/triton'),TORCHINDUCTOR_CACHE_DIR=str(BASE/'verifact134/cache/inductor'))
    from unsloth import FastLanguageModel as Fast
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
    modeldir='/root/verifact_image/models/qwen3.5-9b'
    tok=AutoTokenizer.from_pretrained(modeldir,local_files_only=True)
    data=c.rows(R/'inputs.jsonl');encoded={}
    for row in data:
        msg=messages(row)+[dict(role='assistant',content=c.canonical({'verdict':row['fixed_verdict']})),dict(role='user',content=FOLLOWUP)]
        ids=tok.apply_chat_template(msg,tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
        if hasattr(ids,'get'):ids=ids['input_ids']
        if ids and isinstance(ids[0],list):ids=ids[0]
        if len(ids)+192>16384:raise ValueError('Complete target too long')
        encoded[row['id']]=ids
    model,_=Fast.from_pretrained(model_name=modeldir,max_seq_length=16384,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    model=PeftModel.from_pretrained(model,BASE/'verifact134/adapter120',is_trainable=False)
    Fast.for_inference(model);model.eval();model.requires_grad_(False)
    eos=tok.convert_tokens_to_ids('<|im_end|>');pad=tok.pad_token_id or tok.eos_token_id
    c.put(O/'runtime.json',dict(started_epoch=started,loaded_epoch=time.time(),deadline_epoch=deadline,N=100,arms=['reason_base9b'],GT_in_inputs=False))
    completed=0;generated_seconds=0
    for arm in ('reason_base9b',):
        context=model.disable_adapter() if arm=='reason_base9b' else __import__('contextlib').nullcontext()
        with context:
            for row in sorted(data,key=lambda r:(len(encoded[r['id']]),r['id'])):
                path=O/arm/(row['id']+'.json')
                if path.exists():raise FileExistsError('First answer already exists')
                if STOP or time.time()+45>=deadline:raise TimeoutError('Stop before next attempt')
                c.put(O/'progress.json',dict(stage='generating',arm=arm,completed=completed,total=100,epoch=time.time()))
                ids=encoded[row['id']];x=torch.tensor([ids],device='cuda');mask=torch.ones_like(x)
                c.put(O/'inflight.json',dict(id=row['id'],arm=arm,epoch=time.time()))
                torch.cuda.synchronize();begin=time.perf_counter()
                with torch.inference_mode():
                    generated=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,
                        max_new_tokens=192,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos,
                        stopping_criteria=StoppingCriteriaList([Deadline()]))
                torch.cuda.synchronize();seconds=time.perf_counter()-begin;tail=generated[0,len(ids):].tolist()
                finish='stop' if eos in tail else ('budget_stop' if STOP or time.time()>=deadline else 'length')
                if eos in tail:tail=tail[:tail.index(eos)+1]
                content=tok.decode(tail,skip_special_tokens=True);parsed=None;error=None
                try:
                    value=json.loads(content)
                    if not isinstance(value,dict) or value.get('status') not in ('explained','unable'):raise ValueError('Invalid schema')
                    if value['status']=='explained' and not (isinstance(value.get('reason'),str) and value['reason'].strip()):raise ValueError('Missing reason')
                    if value['status']=='unable' and value.get('reason') is not None:raise ValueError('Unable must have null reason')
                    parsed=value
                except (ValueError,TypeError) as exc:error=str(exc)
                record=dict(id=row['id'],arm=arm,fixed_verdict=row['fixed_verdict'],label_changed=False,content=content,
                    parsed=parsed,parse_error=error,finish_reason=finish,input_tokens=len(ids),output_tokens=len(tail),
                    seconds=seconds,batch_size=1,prompt_token_sha256=c.digest(c.canonical(ids)),epoch=time.time())
                c.put(path,record);(O/'inflight.json').unlink();completed+=1;generated_seconds+=seconds
                del x,mask,generated
    c.put(O/'complete.json',dict(completed=completed,generated_seconds=generated_seconds,worker_wall_seconds=time.time()-started,epoch=time.time(),no_shutdown=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        c.put(R/'results/failure.json',dict(error_type=type(error).__name__,error=str(error),epoch=time.time()));raise
