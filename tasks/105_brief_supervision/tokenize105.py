"""CPU pinned-tokenizer verification; no weights, requests, or GPU."""
from collections import Counter
import statistics
import sys
import common105 as c
from data105 import encode,shared

sys.path.insert(0,str(c.ROOT/'tasks/104_supervision_evidence'))
from tokenize104 import LocalTokenizer

def stats(values):
    ordered=sorted(values)
    return dict(N=len(values),sum=sum(values),mean=statistics.mean(values),min=min(values),median=statistics.median(values),p95=ordered[int(.95*(len(values)-1))],max=max(values))

def main():
    model=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b'
    meta=c.read(c.ROOT/'outputs/103_lora_selection/model_metadata.json')['qwen3.5-9b']
    assert meta['revision']==c.REVISION
    for name in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja'):
        assert c.sha(model/name)==meta['files'][name]['sha256']
    tok=LocalTokenizer(model);lengths=[];fields=c.rows(c.PRIVATE/'answer_fields.jsonl');fmap={(r['arm'],r['id']):r for r in fields}
    encoded_private=[]
    for arm in c.ARMS[1:]:
        for row in c.rows(c.PRIVATE/'train'/(arm+'.jsonl')):
            encoded=encode(tok,row);field=fmap[(arm,row['id'])]
            assert encoded['answer_sha256']==field['answer_sha256'] and encoded['verdict_value_chars']==field['verdict_value_chars']
            lengths.append(dict(id=row['id'],sid=row['sid'],GT=row['GT'],arm=arm,input_tokens=encoded['prompt_tokens'],answer_tokens=encoded['answer_tokens'],
                                total_tokens=len(encoded['input_ids']),verdict_tokens=encoded['groups'].count(1),other_tokens=encoded['groups'].count(2),
                                verdict_value_chars=encoded['verdict_value_chars'],verdict_answer_token_indices=encoded['verdict_answer_token_indices'],
                                prompt_token_sha256=encoded['prompt_token_sha256'],answer_sha256=encoded['answer_sha256']))
            # Persist exact maps locally for optional inspection, not in the sync package.
            encoded_private.append(dict(id=row['id'],arm=arm,answer_token_offsets=encoded['answer_token_offsets'],verdict_value_chars=encoded['verdict_value_chars'],verdict_answer_token_indices=encoded['verdict_answer_token_indices']))
    labels={r['id']:r for r in lengths if r['arm']=='label_only'}
    assert all(r['prompt_token_sha256']==labels[r['id']]['prompt_token_sha256'] for r in lengths)
    evaluation=[]
    for row in c.rows(c.PRIVATE/'eval_inputs.jsonl'):
        ids=shared.prompt_ids(tok,row)
        evaluation.append(dict(id=row['id'],sid=row['sid'],panel=row['panel'],input_tokens=len(ids),prompt_token_sha256=c.digest(c.canonical(ids))))
    order=sorted(evaluation,key=lambda r:(r['input_tokens'],r['id']))
    batches=[dict(batch=index//8,ids=[r['id'] for r in order[index:index+8]],max_input_tokens=max(r['input_tokens'] for r in order[index:index+8])) for index in range(0,len(order),8)]
    c.putl(c.OUT/'train_token_lengths.jsonl',lengths);c.putl(c.OUT/'eval_token_lengths.jsonl',evaluation)
    c.putl(c.PRIVATE/'answer_token_maps.jsonl',encoded_private)
    c.put(c.OUT/'eval_batches.json',dict(batch_size=8,ordering='input_token_length_then_ID',batches=batches,identical_for_all_arms=True))
    result=dict(model='qwen3.5-9b',revision=c.REVISION,CPU_only=True,no_weights_loaded=True,no_truncation=True,
                verdict_mapping='construction character span -> exact token offsets; mixed JSON/value boundary tokens forbidden',
                input_identical_per_training_ID=True,
                training={arm:{key:stats([r[key] for r in lengths if r['arm']==arm]) for key in ('input_tokens','answer_tokens','total_tokens','verdict_tokens','other_tokens')} for arm in c.ARMS[1:]},
                evaluation={panel:stats([r['input_tokens'] for r in evaluation if r['panel']==panel]) for panel in ('natural','pressure')},
                required_context_tokens=max(max(r['total_tokens'] for r in lengths),max(r['input_tokens'] for r in evaluation)+384)+32,
                tokenizer_files={name:c.sha(model/name) for name in ('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja')},
                raw_104_pair_bytes_unchanged=True,answer_maps_count=len(encoded_private),eval_batches=len(batches))
    c.put(c.OUT/'token_summary.json',result)
    print(c.canonical(dict(train_N=len(labels),eval_N=len(evaluation),required_context_tokens=result['required_context_tokens'],pure_verdict_boundaries=True)))

if __name__=='__main__':main()
