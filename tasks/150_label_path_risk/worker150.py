"""Use the existing106 complete-label likelihood operator as a selective score."""
from pathlib import Path
import json,sys,time,os,signal,hashlib,math,subprocess
BASE=Path('/root/autodl-tmp');R=Path(__file__).resolve().parent;STOP=False
SOURCE=BASE/'verifact136_claim_repeat_screen160'
for sub in ('104_supervision_evidence','105_brief_supervision','136_claim_repeat_transfer'):
    sys.path.insert(0,str(SOURCE/'tasks'/sub))
sys.path.insert(0,str(R))
import common105 as c
from prompt136 import prompt_ids
LABELS=('Supported','Not Supported','Not Addressed')

def prepare():
    if (R/'inputs.jsonl').exists():return
    inputs={};pred={}
    for scope in ('screen160','old500'):
        p=BASE/('verifact136_claim_repeat_'+scope)
        for r in c.rows(p/'data/inputs.jsonl'):inputs[r['id']]=r
        for path in (p/'results/claim_repeat').glob('*.json'):
            r=c.read(path)
            if r.get('parsed',{}).get('valid'):pred[r['id']]=r
    assert len(inputs)==500 and len(pred)==500
    ids=sorted(i for i,r in pred.items() if r['parsed']['verdict']=='Supported')
    selected=[dict(id=i,claim=inputs[i]['claim'],reference=inputs[i]['reference'],
                   source_prompt_token_sha256=pred[i]['prompt_token_sha256']) for i in ids]
    assert len(selected)==352
    c.putl(R/'inputs.jsonl',selected)
    c.put(R/'selection.json',dict(N=352,pool='original500 native136 predicted Supported',GT_used=False,ids=ids,prepared_epoch=time.time()))

def main():
    global STOP
    R.mkdir(exist_ok=True);prepare()
    if '--prepare-only' in sys.argv:print(json.dumps(dict(prepared=True,N=352)));return
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
    started=time.time();session=c.read(BASE/'verifact146_caption_transfer/data/session.json');end=min(started+2600,session['end_epoch']-180)
    O=R/'results';O.mkdir(exist_ok=True)
    if (O/'inflight.json').exists():raise RuntimeError('Inspect previous uncommitted scoring attempt')
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True));signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR=str(BASE/'verifact134/cache/triton'),TORCHINDUCTOR_CACHE_DIR=str(BASE/'verifact134/cache/inductor'))
    from unsloth import FastLanguageModel as Fast
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer
    from loss106 import complete_path_scores
    modeldir='/root/verifact_image/models/qwen3.5-9b';tok=AutoTokenizer.from_pretrained(modeldir,local_files_only=True)
    data=c.rows(R/'inputs.jsonl');encoded={}
    for r in data:
        ids=prompt_ids(tok,r)
        if hasattr(ids,'get'):ids=ids['input_ids']
        if ids and isinstance(ids[0],list):ids=ids[0]
        if c.digest(c.canonical(ids))!=r['source_prompt_token_sha256']:raise ValueError('136 input changed')
        encoded[r['id']]=ids
    eos=tok.convert_tokens_to_ids('<|im_end|>');seq={g:tok.encode(c.canonical({'verdict':g}),add_special_tokens=False)+[eos] for g in LABELS}
    model,_=Fast.from_pretrained(model_name=modeldir,max_seq_length=16384,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
    model=PeftModel.from_pretrained(model,BASE/'verifact134/adapter120',is_trainable=False)
    Fast.for_inference(model);model.eval();model.requires_grad_(False)
    c.put(O/'runtime.json',dict(started_epoch=started,loaded_epoch=time.time(),deadline_epoch=end,label_sequences=seq,forward_calls_per_case=3,new_training=False))
    completed=0;total=0.
    for r in sorted(data,key=lambda r:(len(encoded[r['id']]),r['id'])):
        i=r['id'];out=O/'scores'/(i+'.json')
        if out.exists():raise FileExistsError('First score already exists')
        if STOP or time.time()+45>=end:raise TimeoutError('150 fixed compute deadline')
        c.put(O/'progress.json',dict(stage='scoring',completed=completed,total=352,remaining_seconds=(total/completed*(352-completed) if completed else None),epoch=time.time()))
        c.put(O/'inflight.json',dict(id=i,epoch=time.time()))
        torch.cuda.synchronize();begin=time.perf_counter()
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
            values=complete_path_scores(model,encoded[i],seq,4,{'S':33490,'Not':2536},'cuda',16)
        torch.cuda.synchronize();seconds=time.perf_counter()-begin;ss=values['complete_JSON_EOS_sum_logP']
        assert all(math.isfinite(v) and v<=0 for v in ss.values())
        maximum=max(ss['Not Supported'],ss['Not Addressed']);nons=maximum+math.log(math.exp(ss['Not Supported']-maximum)+math.exp(ss['Not Addressed']-maximum))
        c.put(out,dict(id=i,scores=ss,legal_odds=ss['Supported']-nons,complete_S_logP=ss['Supported'],
            first_branch=values['first_value_branch_raw_full_vocab_probabilities'],input_tokens=len(encoded[i]),
            actual_forward_input_tokens=sum(len(encoded[i])+len(seq[g]) for g in LABELS),
            answer_positions_projected=sum(len(seq[g]) for g in LABELS),output_generation_tokens=0,
            forward_calls=3,seconds=seconds,prompt_token_sha256=r['source_prompt_token_sha256'],epoch=time.time()))
        (O/'inflight.json').unlink();completed+=1;total+=seconds
    c.put(O/'complete.json',dict(N=completed,forward_calls=completed*3,score_seconds=total,worker_wall_seconds=time.time()-started,epoch=time.time(),no_shutdown=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        c.put(R/'results/failure.json',dict(error_type=type(error).__name__,error=str(error),epoch=time.time()));raise
