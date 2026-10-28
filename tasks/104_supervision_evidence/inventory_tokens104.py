"""Actual CPU-token lengths for all original512 training cases only."""
from collections import Counter
import json
import common104 as c
from tokenize104 import LocalTokenizer, stats
from training104 import messages, canonical, encode_lists

def main():
    rows=c.lines(c.PRIVATE/'train512_original.jsonl')
    assert len(rows)==512
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
    assert {str(r['sid']) for r in rows}<=set(roles['train'])
    folder=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b'
    meta=c.read(c.ROOT/'outputs/103_lora_selection/model_metadata.json')['qwen3.5-9b']
    for name in ('tokenizer.json','tokenizer_config.json','chat_template.jinja'):
        assert c.sha(folder/name)==meta['files'][name]['sha256'],name
    tok=LocalTokenizer(folder)
    results=[]
    for row in rows:
        record=dict(row,answer=canonical(dict(verdict=row['GT'])))
        record.setdefault('reference_sha256',c.digest(record['reference']))
        ids,mask,supervised=encode_lists(tok,record)
        assert mask[:-supervised]==[-100]*(len(ids)-supervised)
        results.append(dict(id=row['id'],sid=row['sid'],author=row['author'],GT=row['GT'],
                            reference_chars=len(row['reference']),reference_tokens=len(tok.encode(row['reference'])),
                            shared_prompt_tokens=len(ids)-supervised,label_answer_tokens=supervised,total_label_tokens=len(ids)))
    c.putl(c.OUT/'inventory_token_lengths512.jsonl',results)
    c.put(c.OUT/'inventory_token_summary.json',dict(N=512,model='qwen3.5-9b',revision=meta['revision'],
          tokenizer_sha256=c.sha(folder/'tokenizer.json'),reference_truncated=False,new_GPU=0,new_paid_API=0,
          note='104 shared prompt; same original claim/reference; not identical instructions to historical103 label prompt.',
          fields={k:stats([r[k] for r in results]) for k in ('reference_chars','reference_tokens','shared_prompt_tokens','label_answer_tokens','total_label_tokens')},
          by_GT={label:dict(N=sum(r['GT']==label for r in results),input_tokens=stats([r['shared_prompt_tokens'] for r in results if r['GT']==label])) for label in c.LABELS}))
    print(c.canonical(dict(N=len(results),max_total=max(r['total_label_tokens'] for r in results),total_input=sum(r['shared_prompt_tokens'] for r in results),patient_scope='103 train40 only')))

if __name__=='__main__':main()
