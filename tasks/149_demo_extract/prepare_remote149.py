"""Encode complete target136 inputs plus the two extracted demonstrations."""
from pathlib import Path
import json,shutil,sys,time
BASE=Path('/root/autodl-tmp');P=BASE/'verifact149_demo_extract';S=BASE/'verifact136_claim_repeat_screen160';OLD=BASE/'verifact146_caption_transfer'
if (P/'data/job.json').exists():raise FileExistsError('149 already prepared')
P.mkdir(exist_ok=True)
shutil.copytree(OLD/'tasks',P/'tasks',dirs_exist_ok=True)
T=P/'tasks/149_demo_extract';T.mkdir(exist_ok=True);shutil.copy2(P/'prompt149.py',T/'prompt149.py')
for sub in ('105_brief_supervision','104_supervision_evidence','136_claim_repeat_transfer','149_demo_extract'):sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
from prompt149 import prompt_ids
from prompt136 import prompt_ids as base_ids
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True)
data=c.rows(S/'data/inputs.jsonl');assert len(data)==160
encoded={};records=[];lengths=[]
for row in data:
    before=base_ids(tok,row)
    if hasattr(before,'get'):before=before['input_ids']
    if before and isinstance(before[0],list):before=before[0]
    source=c.read(S/'results/claim_repeat'/(row['id']+'.json'))
    assert c.digest(c.canonical(before))==source['prompt_token_sha256']
    after=prompt_ids(tok,row)
    if len(after)+384>16384:raise ValueError('Complete target plus extracted demos exceeds context')
    encoded[row['id']]=after
    record=dict(id=row['id'],claim=row['claim'],reference=row['reference'],prompt_token_sha256=c.digest(c.canonical(after)),source_prompt_token_sha256=source['prompt_token_sha256'])
    records.append(record);lengths.append(dict(id=row['id'],input_tokens=len(after),source_input_tokens=len(before),prompt_token_sha256=record['prompt_token_sha256']))
ls={r['id']:r['input_tokens'] for r in lengths};order=sorted(ls,key=lambda i:(ls[i],i));batches=[]
while order:
    batch=order[:2] if ls[order[0]]<=12701 else order[:1]
    if max(ls[i] for i in batch)>12701:batch=batch[:1]
    batches.append(batch);order=order[len(batch):]
job=dict(c.read(OLD/'data/job.json'),task=149,arm='demo_extract',scope='screen160',expected_N=160,target_N=160,prior_N=0,
    ids=[r['id'] for r in records],batches=batches,compute_limit_seconds=900,save_reserve_seconds=180,new_training=False,
    transform='extractive_demo_reference_only',source_task=141,selection_rule='original134 screen160')
c.putl(P/'data/inputs.jsonl',records);c.putl(P/'data/lengths.jsonl',lengths);c.put(P/'data/job.json',job)
shutil.copy2(OLD/'data/session.json',P/'data/session.json')
worker=(OLD/'tasks/145_order_caption/worker145.py').read_text()
worker=worker.replace("assert job['task']==146 and arm=='order_caption'","assert job['task']==149 and arm=='demo_extract'").replace('task=146','task=149')
worker=worker.replace("sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids","sys.path.insert(0,str(R/'tasks/149_demo_extract'));from prompt149 import prompt_ids")
(T/'worker149.py').write_text(worker,encoding='utf-8')
c.put(P/'preparation.json',dict(N=160,input_tokens_total=sum(ls.values()),max_input_tokens=max(ls.values()),
    added_demo_tokens_per_item=sorted({r['input_tokens']-r['source_input_tokens'] for r in lengths}),
    batch2_items=sum(len(b) for b in batches if len(b)==2),batch1_items=sum(len(b) for b in batches if len(b)==1),
    target_reference_changed=False,GT_used_in_target_inputs=False,prepared_epoch=time.time()))
print(json.dumps(c.read(P/'preparation.json')))
