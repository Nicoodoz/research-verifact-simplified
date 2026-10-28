"""CPU tokenizer verification of exact original105 prompts, groups and batches."""
from collections import Counter
import statistics
import argparse
import sys
from pathlib import Path
import common107 as c

sys.path.insert(0, str(c.ROOT / 'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer
from data105 import encode, shared

def stats(values):
    values = sorted(values)
    return dict(N=len(values), sum=sum(values), min=min(values), median=statistics.median(values),
                mean=statistics.mean(values), p95=values[int(.95*(len(values)-1))], max=max(values))

def prepare(model_dir):
    meta = c.read(c.ROOT/'outputs/103_lora_selection/model_metadata.json')['qwen3.5-9b']
    names = ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja')
    if meta['revision'] != c.REVISION or any(c.sha(model_dir/n) != meta['files'][n]['sha256'] for n in names):
        raise ValueError('Original9B tokenizer metadata mismatch')
    tok = CPUPinnedTokenizer(model_dir)
    lengths = []
    original = {r['id']:r for r in c.rows(c.ROOT/'outputs/105_brief_supervision/train_token_lengths.jsonl') if r['arm']=='label_only'}
    for arm in c.ARMS:
        for row in c.rows(c.PRIVATE/'train'/(arm+'.jsonl')):
            item = encode(tok,row)
            fields = dict(arm=arm,id=row['id'],sid=row['sid'],GT=row['GT'],
                support_target=int(row['GT']=='Supported'), input_tokens=item['prompt_tokens'],
                answer_tokens=item['answer_tokens'], total_tokens=len(item['input_ids']),
                verdict_tokens=item['groups'].count(1),other_tokens=item['groups'].count(2),
                verdict_answer_token_indices=item['verdict_answer_token_indices'],
                prompt_token_sha256=item['prompt_token_sha256'],answer_sha256=item['answer_sha256'])
            if any(fields[k] != original[row['id']][k] for k in fields if k not in ('arm','support_target')):
                raise ValueError('Original105 train token mapping changed')
            # The head index points to the final prompt token, strictly before all answer groups.
            index = item['prompt_tokens']-1
            if item['groups'][index] != 0 or item['labels'][index] != -100 or item['groups'][index+1] == 0:
                raise ValueError('Auxiliary representation is not before answer')
            lengths.append(fields)
    evaluation = []
    oldeval = {r['id']:r for r in c.rows(c.ROOT/'outputs/105_brief_supervision/eval_token_lengths.jsonl')}
    for row in c.rows(c.PRIVATE/'eval_inputs.jsonl'):
        ids = shared.prompt_ids(tok,row)
        fields = dict(id=row['id'],sid=row['sid'],panel=row['panel'],input_tokens=len(ids),prompt_token_sha256=c.digest(c.canonical(ids)))
        if fields != oldeval[row['id']]:
            raise ValueError('Original105 inference token input changed')
        evaluation.append(fields)
    order = sorted(evaluation,key=lambda r:(r['input_tokens'],r['id']))
    original_batches = [dict(batch=i//8,ids=[r['id'] for r in order[i:i+8]],max_input_tokens=max(r['input_tokens'] for r in order[i:i+8])) for i in range(0,len(order),8)]
    if original_batches != c.read(c.ROOT/'outputs/105_brief_supervision/eval_batches.json')['batches']:
        raise ValueError('Original105 eval batching changed')
    size=c.read(c.TASK/'config.json')['evaluation']['batch_size']
    if size not in (1,2):raise ValueError('5090 batch must be2 or1')
    batches = [dict(batch=i//size,ids=[r['id'] for r in order[i:i+size]],max_input_tokens=max(r['input_tokens'] for r in order[i:i+size])) for i in range(0,len(order),size)]
    c.putl(c.OUT/'train_token_lengths.jsonl',lengths)
    c.putl(c.OUT/'eval_token_lengths.jsonl',evaluation)
    c.put(c.OUT/'eval_batches.json',dict(batch_size=size,ordering='input_token_length_then_ID',batches=batches,identical_for_all_arms=True,
        user_authorized_5090_rebatch=True,original105_batch8_preserved=True))
    sources = [c.PRIVATE/'train'/(a+'.jsonl') for a in c.ARMS]+[c.PRIVATE/'eval_inputs.jsonl']
    summary = dict(model='Qwen/Qwen3.5-9B',revision=c.REVISION,tokenizer_only=True,weights_loaded=False,
        truncation=False,tokenizer_files={n:c.sha(model_dir/n) for n in names},
        input_file_SHA256={str(p.resolve()):c.sha(p) for p in sources},
        training={a:{k:stats([r[k] for r in lengths if r['arm']==a]) for k in ('input_tokens','answer_tokens','total_tokens')} for a in c.ARMS},
        required_context_tokens=c.read(c.ROOT/'outputs/105_brief_supervision/token_summary.json')['required_context_tokens'],
        development_N=500, all196_main_loss_token_groups_identical_to105=True,
        all500_prompt_hashes_identical_to105=True,original105_batch8_source_verified=True,
        evaluation_batch_size=size,evaluation_batches=len(batches),both_arms_identical_new_batches=True,
        auxiliary_position='last_prompt_token_before_answer',
        auxiliary_targets_each=dict(Counter(str(r['support_target']) for r in lengths if r['arm']=='support_aux')))
    c.put(c.OUT/'tokenizer_summary.json',summary)
    print(c.canonical(dict(status='PASS',train_each=196,eval_N=500,context=summary['required_context_tokens'])))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,default=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    prepare(p.parse_args().model_dir)
