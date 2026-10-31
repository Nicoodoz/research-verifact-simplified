"""Freeze only the authorized two examples and reuse136 target inventories."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/141_two_demos'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
from prompt141 import EXAMPLE_IDS,ANSWERS,prompt_ids,original136_messages,validate_examples


def read_source136():
    inputs={};lengths={};base=R/'.local_models/136_claim_repeat_transfer'
    for scope in ('screen160','old500','full1817'):
        for row in c.rows(base/('claim_repeat_'+scope)/'bundle/data/inputs.jsonl'):
            i=row['id']
            if i in inputs and row!=inputs[i]:raise ValueError('136 input conflict')
            inputs[i]=row
        for file in (base/'evidence'/scope/'claim_repeat').glob('*.json'):
            row=c.read(file)
            if 'id' not in row:continue
            value=dict(id=row['id'],target_input_tokens=row['input_tokens'],target_prompt_token_sha256=row['prompt_token_sha256'])
            if value['id'] in lengths and value!=lengths[value['id']]:raise ValueError('136 length conflict')
            lengths[value['id']]=value
    assert len(inputs)==1817 and set(inputs)==set(lengths)
    assert all(inputs[i]['prompt_token_sha256']==lengths[i]['target_prompt_token_sha256'] for i in inputs)
    return inputs,lengths


def freeze(tokenizer=None):
    source=P/'source'
    if (source/'freeze.json').exists():raise FileExistsError('141 source already frozen; preserve it')
    data=R/'.local_models/127_native_reason_data/dataset_v12_support20261031/paired'
    label={r['id']:r for r in c.rows(data/'train_label_only.jsonl')}
    reasons={r['id']:r for r in c.rows(data/'train_verdict_reason.jsonl')}
    assert len(label)==len(reasons)==63
    train={str(r['sid']) for r in c.rows(R/'.local_models/138_rationale_tasks/label_replay/bundle/data/train.jsonl')}
    keys=c.rows(R/'.local_models/134_author_baselines/keys.jsonl');evaluation={str(r['sid']) for r in keys}
    assert len(train)==32 and len(evaluation)==20 and not train&evaluation
    examples=[]
    for i,gt,answer in zip(EXAMPLE_IDS,('Supported','Not Supported'),ANSWERS):
        row=label[i];reason=reasons[i];review=reason['reason_metadata']['review']
        assert row['GT']==reason['GT']==gt and row['answer']==answer and row['fit_role']=='train'
        assert str(row['sid']) in train-evaluation and review['status']=='approved' and review['primary_full_reference_read']
        assert not review['unresolved_issues'] and all(row[k]==reason[k] for k in ('claim','reference','sid'))
        examples.append({k:row[k] for k in ('id','sid','GT','claim','reference','answer')})
    validate_examples(examples);assert len({str(r['sid']) for r in examples})==2
    inputs,lengths=read_source136()
    tok=tokenizer or CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
    kw=dict(tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
    longest=max(lengths,key=lambda i:lengths[i]['target_input_tokens'])
    base_ids=tok.apply_chat_template(original136_messages(inputs[longest]),**kw)
    assert c.digest(c.canonical(base_ids))==lengths[longest]['target_prompt_token_sha256']
    complete=prompt_ids(tok,inputs[longest],examples);delta=len(complete)-len(base_ids)
    assert len(base_ids)==13447 and delta==14515 and len(complete)+384==28346
    #A second independent content/length fixture checks the fixed prefix cost.
    fixture=dict(claim='A short verification target.',reference='An unrelated short reference.')
    assert len(prompt_ids(tok,fixture,examples))-len(tok.apply_chat_template(original136_messages(fixture),**kw))==delta
    for i,row in lengths.items():row['input_token_upper_bound']=row['target_input_tokens']+delta
    assert max(r['input_token_upper_bound']+384 for r in lengths.values())<=32768
    c.putl(source/'examples.jsonl',examples);c.putl(source/'inputs136.jsonl',[inputs[i] for i in sorted(inputs)])
    c.putl(source/'lengths136.jsonl',[lengths[i] for i in sorted(lengths)])
    original_job=c.read(R/'.local_models/134_author_baselines/job.json')
    c.put(source/'screen160_ids.json',original_job['phases'][0]['ids'])
    c.put(source/'old500_ids.json',[r['id'] for r in keys if r['old_panel'] in ('natural','pressure')])
    settings=c.read(R/'.local_models/139_full_repeat/source/settings.json')
    assert settings['adapter_sha256']=='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a'
    c.put(source/'settings.json',settings)
    session=c.read(R/'.local_models/139_full_repeat/source/session.json');session['save_reserve_seconds']=600
    c.put(source/'session.json',session)
    proof=dict(task=141,status='CPU_SOURCE_FROZEN',example_ids=list(EXAMPLE_IDS),demos_sha256=c.sha(source/'examples.jsonl'),
        source_dataset='dataset_v12_support20261031 train_label_only',source_label_file_sha256=c.sha(data/'train_label_only.jsonl'),
        train_patients=32,eval_patients=20,example_patient_overlap=0,full_reference_preserved=True,
        token_prefix_delta=delta,max_target_tokens=len(base_ids),max_combined_tokens=len(complete),
        max_with384=len(complete)+384,capacity=32768,remaining_tokens=32768-len(complete)-384,
        exact_longest_target_ID=longest,exact_longest_prompt_sha256=c.digest(c.canonical(complete)),
        all_other_targets_are_length_upper_bounds=True,no_full1817_retokenization=True,no_model_loaded=True)
    c.put(source/'freeze.json',proof);return proof


if __name__=='__main__':print(c.canonical(freeze()))
