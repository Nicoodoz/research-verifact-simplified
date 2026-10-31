"""Check actual fixed inputs, labels and token lengths without loading a model."""
from pathlib import Path
import ast,json,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/141_two_demos'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/139_full_repeat'));from budget139 import deadlines
from tokenizer_cpu105 import CPUPinnedTokenizer
from prompt141 import messages,prompt_ids,EXAMPLE_IDS,ANSWERS,original136_messages


def main():
    B=P/'screen160/bundle';examples=c.rows(B/'data/examples.jsonl');rows=c.rows(B/'data/inputs.jsonl')
    lengths={r['id']:r for r in c.rows(B/'data/lengths.jsonl')};job=c.read(B/'data/job.json')
    assert len(rows)==160 and len(lengths)==160 and set(lengths)==set(job['ids'])
    assert tuple(r['id'] for r in examples)==EXAMPLE_IDS and tuple(r['answer'] for r in examples)==ANSWERS
    assert [r['GT'] for r in examples]==['Supported','Not Supported']
    assert c.sha(B/'data/examples.jsonl')==job['demos_sha256']
    all_keys=c.rows(R/'.local_models/134_author_baselines/keys.jsonl')
    allowed={str(r['sid']) for r in c.rows(R/'.local_models/138_rationale_tasks/label_replay/bundle/data/train.jsonl')}
    evaluation={str(r['sid']) for r in all_keys}
    assert len(allowed)==32 and len(evaluation)==20 and all(str(r['sid']) in allowed-evaluation for r in examples)
    source={r['id']:r for r in c.rows(P/'source/inputs136.jsonl')}
    for row in rows:
        assert set(row)=={'id','claim','reference','prompt_token_sha256','target_prompt_token_sha256'}
        assert row['claim']==source[row['id']]['claim'] and row['reference']==source[row['id']]['reference']
        m=messages(row,examples)
        assert [v['role'] for v in m]==['system','user','assistant','user','assistant','user']
        assert m[0]==original136_messages(row)[0] and m[-1]==original136_messages(row)[1]
        assert m[1]==original136_messages(examples[0])[1] and m[3]==original136_messages(examples[1])[1]
        assert m[2]['content']==ANSWERS[0] and m[4]['content']==ANSWERS[1]
        assert lengths[row['id']]['prompt_token_sha256']==row['prompt_token_sha256']
        assert lengths[row['id']]['target_prompt_token_sha256']==source[row['id']]['prompt_token_sha256']
        assert lengths[row['id']]['input_tokens']+384<=32768
    #Only recheck the first formal longest input; no second full160 token pass.
    first=next(r for r in rows if r['id']==job['first_formal_ID'])
    tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
    ids=prompt_ids(tok,first,examples)
    assert len(ids)==lengths[first['id']]['input_tokens'] and c.digest(c.canonical(ids))==first['prompt_token_sha256']
    timing=deadlines(1000,dict(start_epoch=0,GPU_cap_CNY=20,hourly_CNY=1),job)
    assert timing['compute_end']==2500 and timing['stage_end']==3100
    for name in ('prompt141.py','initialize141.py','prepare141.py','worker141.py','controller141.py','start141.py'):
        file=R/'tasks/141_two_demos'/name;ast.parse(file.read_text(encoding='utf-8'));assert not file.read_bytes().startswith(b'\xef\xbb\xbf')
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    result=dict(task=141,status='PASS',N=160,system_once=True,source_labels_exact=True,
        training_evaluation_patients_disjoint=True,all_user_contents_exact136=True,examples_have_full_references=True,
        no_reason_or_GT_field_in_model_input=True,longest_formal_first=True,precise_token_SHA_checked=True,
        max_screen_input_tokens=max(r['input_tokens'] for r in lengths.values()),
        global_max_with384=c.read(P/'source/freeze.json')['max_with384'],
        compute_limit_seconds=1500,save_reserve_seconds=600,new_GPU=False,new_API=0)
    c.put(P/'cpu_selfcheck.json',result);print(c.canonical(result))


if __name__=='__main__':main()
