"""CPU-only preparation of one fixed training-only NA replacement; no model call."""
from pathlib import Path
import argparse,json,shutil,sys,time
BASE=Path('/root/autodl-tmp');S=BASE/'verifact136_claim_repeat_screen160';OLD=BASE/'verifact152_demo_na'
from types import SimpleNamespace
a=SimpleNamespace(arm='train_demo_na')
P=BASE/'verifact162_train_demo_na'
if (P/'data/job.json').exists():raise FileExistsError('162 arm already prepared')
P.mkdir(exist_ok=True);shutil.copytree(OLD/'tasks',P/'tasks',dirs_exist_ok=True);T=P/'tasks/162_train_demo_pool';T.mkdir(exist_ok=True)
shutil.copy2(P/'prompt162.py',T/'prompt162.py')
shutil.copytree(BASE/'verifact155_train_error_risk/tasks/144_native_confidence',P/'tasks/144_native_confidence',dirs_exist_ok=True)
for sub in ('105_brief_supervision','104_supervision_evidence','136_claim_repeat_transfer','162_train_demo_pool'):sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
examples=c.rows(P/'examples_source.jsonl');assert len(examples)==3 and [r['GT'] for r in examples]==['Supported','Not Supported','Not Addressed']
c.putl(P/'data/examples.jsonl',examples)
from prompt162 import prompt_ids
from prompt136 import prompt_ids as original_ids
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True)
records=[];lengths=[]
for r in c.rows(S/'data/inputs.jsonl'):
    before=original_ids(tok,r)
    if hasattr(before,'get'):before=before['input_ids']
    if before and isinstance(before[0],list):before=before[0]
    after=prompt_ids(tok,r);assert len(after)+384<=16384
    source=c.read(S/'results/claim_repeat'/(r['id']+'.json'));assert c.digest(c.canonical(before))==source['prompt_token_sha256']
    sha=c.digest(c.canonical(after));records.append(dict(id=r['id'],claim=r['claim'],reference=r['reference'],prompt_token_sha256=sha,source_prompt_token_sha256=source['prompt_token_sha256']))
    lengths.append(dict(id=r['id'],input_tokens=len(after),source_input_tokens=len(before),prompt_token_sha256=sha))
assert len(records)==160
ls={r['id']:r['input_tokens'] for r in lengths};order=sorted(ls,key=lambda i:(ls[i],i));batches=[]
while order:
    batch=order[:2] if ls[order[0]]<=12701 else order[:1]
    if max(ls[i] for i in batch)>12701:batch=batch[:1]
    batches.append(batch);order=order[len(batch):]
old=c.read(OLD/'data/job.json');job=dict(old,task=162,arm=a.arm,scope='screen160',ids=[r['id'] for r in records],batches=batches,expected_N=160,target_N=160,prior_N=0,compute_limit_seconds=900,save_reserve_seconds=180,demonstration_change='replace_NA_with_new_training_patient')
c.putl(P/'data/inputs.jsonl',records);c.putl(P/'data/lengths.jsonl',lengths);c.put(P/'data/job.json',job);shutil.copy2(OLD/'data/session.json',P/'data/session.json')
worker=(BASE/'verifact155_train_error_risk/tasks/155_train_error_risk/worker155.py').read_text().replace("job['task']==155 and arm=='native_train'","job['task']==162 and arm=='train_demo_na'").replace('task=155','task=162').replace("sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids","sys.path.insert(0,str(R/'tasks/162_train_demo_pool'));from prompt162 import prompt_ids")
(T/'worker162.py').write_text(worker,encoding='utf-8');compile(worker,str(T/'worker162.py'),'exec')
c.put(P/'preparation.json',dict(arm=a.arm,N=160,input_tokens_total=sum(ls.values()),max_input_tokens=max(ls.values()),added_demo_tokens=sorted({r['input_tokens']-r['source_input_tokens'] for r in lengths}),target_reference_changed=False,new_GT=False,model_calls=0,prepared_epoch=time.time()))
print(json.dumps(c.read(P/'preparation.json')))
