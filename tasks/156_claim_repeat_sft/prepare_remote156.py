"""Prepare the original120 schedule with136 prefixes, using existing local assets only."""
from pathlib import Path
import json,hashlib,shutil,sys,time
BASE=Path('/root/autodl-tmp');P=BASE/'verifact156_claim_repeat_sft';S=BASE/'verifact133_repeat20261031'
if (P/'data/job156.json').exists():raise FileExistsError('156 already prepared')
P.mkdir(exist_ok=True)
for sub in ('104_supervision_evidence','105_brief_supervision','107_support_aux'):
    shutil.copytree(S/'tasks'/sub,P/'tasks'/sub,dirs_exist_ok=True)
shutil.copytree(BASE/'verifact146_caption_transfer/tasks/136_claim_repeat_transfer',P/'tasks/136_claim_repeat_transfer',dirs_exist_ok=True)
for sub in ('104_supervision_evidence','105_brief_supervision','136_claim_repeat_transfer','156_claim_repeat_sft'):
    sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
from data105 import encode,shared,training_plan
from input156 import repeat_prompt_ids
shared.prompt_ids=repeat_prompt_ids
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True)
manifest=c.rows(P/'train_manifest.jsonl');source={r['id']:r for r in c.rows(S/'data/shuffle_repeat/train.jsonl')}
assert len(manifest)==len(source)==2945
rows=[];lengths=[]
for m in manifest:
    r=source[m['id']]
    assert r['GT']==m['GT'] and str(r['sid'])==m['sid']
    for name in ('claim','reference','answer'):assert hashlib.sha256(r[name].encode()).hexdigest()==m[name+'_sha256']
    item=encode(tok,r)
    if len(item['input_ids'])>16384:raise ValueError('Full training input too long')
    rows.append(r);lengths.append(dict(id=r['id'],prompt_tokens=item['prompt_tokens'],answer_tokens=item['answer_tokens'],total_tokens=len(item['input_ids']),prompt_token_sha256=item['prompt_token_sha256'],answer_sha256=item['answer_sha256']))
plan=c.read(P/'original_plan.json');assert training_plan([r['id'] for r in rows],1,8)==plan
screens=[dict(id=r['id'],claim=r['claim'],reference=r['reference']) for r in c.rows(BASE/'verifact136_claim_repeat_screen160/data/inputs.jsonl')]
assert len(screens)==160 and not {r['id'] for r in screens}&set(source)
sl=[]
for r in screens:
    ids=repeat_prompt_ids(tok,r);old=c.read(BASE/'verifact136_claim_repeat_screen160/results/claim_repeat'/(r['id']+'.json'))
    sha=c.digest(c.canonical(ids));assert sha==old['prompt_token_sha256']
    sl.append(dict(id=r['id'],input_tokens=len(ids),prompt_token_sha256=sha))
c.putl(P/'data/train.jsonl',rows);c.putl(P/'data/lengths.jsonl',lengths);c.put(P/'data/plan.json',plan)
c.putl(P/'data/screen.jsonl',screens);c.putl(P/'data/screen_lengths.jsonl',sl)
shutil.copy2(BASE/'verifact146_caption_transfer/data/session.json',P/'data/session.json')
source107=S/'source107/checkpoint_a';dest=P/'source107';dest.mkdir(exist_ok=True)
old=c.read(P/'source_job120.json')
assert c.sha(source107/'adapter_model.safetensors')==old['source_adapter_sha256']
for name in ('adapter_model.safetensors','adapter_config.json'):shutil.copy2(source107/name,dest/name)
job=dict(old,task=156,name='claim_repeat_sft',source107_adapter=str(dest),train_path='data/train.jsonl',lengths_path='data/lengths.jsonl',plan_path='data/plan.json',
    screen_inputs_path='data/screen.jsonl',screen_lengths_path='data/screen_lengths.jsonl',session_path='data/session.json',
    phase_limit_seconds=17400,save_reserve_seconds=180,expected_seconds_per_example=5.1,expected_screen_seconds=450,load_and_gate_reserve_seconds=600,
    scientific_change='136 prefix used during training; other120 data/order/optimizer/loss/seed unchanged',scheduled_midpoint_step=220)
c.put(P/'data/job156.json',job)
worker=(P/'worker120_source.py').read_text()
worker=worker.replace("fingerprint = dict(task=120, candidate='full_pool_sft'","fingerprint = dict(task=156, candidate='claim_repeat_sft'")
worker=worker.replace('from data105 import encode, shared, training_plan','from data105 import encode, shared, training_plan\nsys.path.insert(0,str(ROOT/\'tasks/156_claim_repeat_sft\'))\nfrom input156 import repeat_prompt_ids\nshared.prompt_ids=repeat_prompt_ids')
worker=worker.replace("started+job['phase_limit_seconds']","common.read(ROOT/'runtime156.json')['phase_deadline_epoch']")
worker=worker.replace('/root/autodl-tmp/verifact109/results/cache/','/root/autodl-tmp/verifact134/cache/')
oldgate="            if consumed-starting_consumed >= 32 and step < 369:\n                budget(eta)"
assert oldgate in worker
worker=worker.replace(oldgate,"            # Hard original stage/window deadlines remain; cold ETA is diagnostic only.\n            if step == 220 and not (out/'midpoint_ready.json').exists():\n                save()\n                pointer=common.read(work/'resume.json')\n                common.put(out/'midpoint_ready.json',dict(step=step,consumed=consumed,checkpoint=str(work/pointer['slot']),epoch=time.time()))\n                progress('midpoint_saved_for_evaluation',step,369,eta)\n                return 75")
worker=worker.replace("            with torch.inference_mode():\n                outputs = model.generate", "            torch.cuda.synchronize(); inference_begin=time.perf_counter()\n            with torch.inference_mode():\n                outputs = model.generate")
worker=worker.replace('            records = []\n            for index, identifier in enumerate(identifiers):','            torch.cuda.synchronize(); batch_seconds=time.perf_counter()-inference_begin\n            records = []\n            for index, identifier in enumerate(identifiers):')
worker=worker.replace('source_prompt_sha256_104=screen_lengths','prompt_token_sha256=screen_lengths')
worker=worker.replace('adapter_sha256=adapter_sha))','adapter_sha256=adapter_sha,output_tokens=len(tail),seconds=batch_seconds/len(identifiers),batch_seconds=batch_seconds,batch_size=len(identifiers)))')
worker=worker.replace("default='data/full_pool_sft120.json'","default='data/job156.json'").replace('    run(job, out)\n','    raise SystemExit(run(job, out) or 0)\n')
T=P/'tasks/156_claim_repeat_sft';T.mkdir(exist_ok=True);(T/'worker156.py').write_text(worker,encoding='utf-8');compile(worker,str(T/'worker156.py'),'exec')
assert 'shared.prompt_ids=repeat_prompt_ids' in worker and 'return 75' in worker
shutil.copytree(BASE/'verifact155_train_error_risk/tasks/144_native_confidence',P/'tasks/144_native_confidence',dirs_exist_ok=True)
shutil.copy2(BASE/'verifact155_train_error_risk/tasks/155_train_error_risk/worker155.py',P/'inference_template.py')
c.put(P/'preparation.json',dict(N=2945,patients=32,steps=369,initial_source107_SHA=job['source_adapter_sha256'],source133_trained_checkpoint_used=False,
    max_training_total_tokens=max(r['total_tokens'] for r in lengths),total_training_tokens=sum(r['total_tokens'] for r in lengths),
    original_data_order_preserved=True,new_GT=False,new_reason=False,prefix='136',seed=job['seed'],prepared_epoch=time.time(),phase_limit_seconds=17400))
print(json.dumps(c.read(P/'preparation.json')))
