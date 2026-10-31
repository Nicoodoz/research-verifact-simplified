"""Encode training-side136 requests and reuse ordinary generation with a read-only margin observer."""
from pathlib import Path
import json,shutil,sys,time
BASE=Path('/root/autodl-tmp');P=BASE/'verifact155_train_error_risk';OLD=BASE/'verifact146_caption_transfer'
if (P/'data/job.json').exists():raise FileExistsError('155 already prepared')
P.mkdir(exist_ok=True);shutil.copytree(OLD/'tasks',P/'tasks',dirs_exist_ok=True)
for sub in ('105_brief_supervision','104_supervision_evidence','136_claim_repeat_transfer'):sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
from prompt136 import prompt_ids
from transformers import AutoTokenizer
data=c.rows(P/'inputs_source.jsonl');assert len(data)==512 and all(set(r)=={'id','claim','reference'} for r in data)
tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True);records=[];lengths=[]
for r in data:
    ids=prompt_ids(tok,r)
    if hasattr(ids,'get'):ids=ids['input_ids']
    if ids and isinstance(ids[0],list):ids=ids[0]
    if len(ids)+384>16384:raise ValueError('Complete training-side native input exceeds context')
    sha=c.digest(c.canonical(ids));records.append(dict(r,prompt_token_sha256=sha,source_prompt_token_sha256=sha));lengths.append(dict(id=r['id'],input_tokens=len(ids),prompt_token_sha256=sha))
ls={r['id']:r['input_tokens'] for r in lengths};order=sorted(ls,key=lambda i:(ls[i],i));batches=[]
while order:
    batch=order[:2] if ls[order[0]]<=12701 else order[:1]
    if max(ls[i] for i in batch)>12701:batch=batch[:1]
    batches.append(batch);order=order[len(batch):]
old=c.read(OLD/'data/job.json');job={k:old[k] for k in ('model_dir','adapter','adapter_bytes','adapter_sha256','max_seq_length','generation')}
job.update(task=155,arm='native_train',scope='train512',inputs='data/inputs.jsonl',expected_N=512,target_N=512,prior_N=0,
           ids=[r['id'] for r in records],batches=batches,compute_limit_seconds=1500,save_reserve_seconds=180,new_training=False,no_shutdown=True,
           role='original120 training32 only',GT_in_model_inputs=False,score_readout='same generate branch logits read-only')
c.putl(P/'data/inputs.jsonl',records);c.putl(P/'data/lengths.jsonl',lengths);c.put(P/'data/job.json',job);shutil.copy2(OLD/'data/session.json',P/'data/session.json')
worker=(OLD/'tasks/145_order_caption/worker145.py').read_text()
worker=worker.replace("assert job['task']==146 and arm=='order_caption'","assert job['task']==155 and arm=='native_train'").replace('task=146','task=155')
worker=worker.replace('from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList','from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList,LogitsProcessorList')
worker=worker.replace("from peft import PeftModel","from peft import PeftModel\n    sys.path.insert(0,str(R/'tasks/144_native_confidence'))\n    from capture_native_score import NativeBranchCapture")
worker=worker.replace('torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()',"observer=NativeBranchCapture(width,identifiers)\n        torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()")
worker=worker.replace('stopping_criteria=StoppingCriteriaList([Deadline()]))','stopping_criteria=StoppingCriteriaList([Deadline()]),logits_processor=LogitsProcessorList([observer]))')
worker=worker.replace('records=[]\n        for n,i in enumerate(identifiers):',"records=[]\n        captured={r['id']:r for r in observer.records()}\n        for n,i in enumerate(identifiers):")
worker=worker.replace("adapter_sha256=job['adapter_sha256'],source_checkpoint=", "native_capture=captured[i],native_margin=captured[i].get('logit_S_minus_Not'),adapter_sha256=job['adapter_sha256'],source_checkpoint=")
T=P/'tasks/155_train_error_risk';T.mkdir(exist_ok=True);(T/'worker155.py').write_text(worker,encoding='utf-8');compile(worker,str(T/'worker155.py'),'exec')
assert 'NativeBranchCapture(width,identifiers)' in worker and 'captured[i]' in worker
c.put(P/'preparation.json',dict(N=512,max_input_tokens=max(ls.values()),input_tokens_total=sum(ls.values()),GT_in_model_inputs=False,
    read_only_observer=True,batch2_items=sum(len(b) for b in batches if len(b)==2),prepared_epoch=time.time()))
print(json.dumps(c.read(P/'preparation.json')))
