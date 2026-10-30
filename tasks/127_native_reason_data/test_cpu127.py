"""Synthetic127 encoding/loss tests; no clinical-reason creation or model fit."""
from pathlib import Path
import copy,json,sys
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from data_contract127 import (ROOT,LABELS,VERSION,INSTRUCTIONS,OUTPUT_RULE,build_record,
    construct_answer,digest,encode,inference_input,messages,pad_encoded,prompt_ids,reason_issues,training_plan)
from prepare127 import load_pool
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer
from loss105 import segmented_hidden_loss


def annotation(row):
    return dict(id=row['id'],GT=row['GT'],ai_assisted=True,
        reason_sentences=['Synthetic code fixture: Supported, Not Supported and Not Addressed are words.',
                          'Escaped "quotes", a backslash \\ and a newline\nremain text.'],
        evidence_sources=[dict(kind='whole_reference',reference_sha256=digest(row['reference']),
                               fully_read=True,review_record='synthetic unit fixture, not clinical review')],
        review=dict(status='approved',reviewer='synthetic_test_only',verdict_consistent=True,
                    input_grounded=True,na_not_absence_checked=True,teacher_disagreement_reviewed=True,
                    complete_sentences=True,sentence_count=2))


def main():
    torch.set_num_threads(1)
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    encoded=[]
    for j,label in enumerate(LABELS):
        row=dict(id='synthetic-'+str(j),sid='synthetic-train',GT=label,author='test',
                 claim='Synthetic "claim" \\ text.',reference='Synthetic reference.\nNot an actual clinical record.',paper_r1=label)
        ann=annotation(row);assert not reason_issues(row,ann)
        a=build_record(row,'train','label_only',ann);b=build_record(row,'train','verdict_reason',ann)
        ea,eb=encode(tok,a),encode(tok,b);encoded.extend([ea,eb])
        assert ea['prompt_token_sha256']==eb['prompt_token_sha256']
        assert json.loads(a['answer'])=={'verdict':label}
        assert set(json.loads(b['answer']))=={'verdict','reason'}
        assert json.loads(b['answer'])['reason']==' '.join(ann['reason_sentences'])
        for target,value in [(a,ea),(b,eb)]:
            suffix=value['input_ids'][value['prompt_tokens']:]
            assert tok.decode(suffix[:-1],skip_special_tokens=False)==target['answer']
            assert suffix[-1]==tok.convert_tokens_to_ids('<|im_end|>') and value['groups'][-1]==2
            assert all(x==-100 for x in value['labels'][:value['prompt_tokens']])
            assert all(x==0 for x in value['groups'][:value['prompt_tokens']])
            only_verdict=[suffix[k] for k in value['verdict_answer_token_indices']]
            assert tok.decode(only_verdict,skip_special_tokens=False)==label
            assert sum(x==1 for x in value['groups'])==len(value['verdict_answer_token_indices'])
        # Deliberately corrupt non-input metadata: actual inference token IDs stay unchanged.
        corrupt=dict(b,GT=LABELS[(j+1)%3],answer='SECRET',reason_metadata={'reason':'SECRET'},issue_codes=['SECRET'])
        assert prompt_ids(tok,corrupt)==prompt_ids(tok,row)
        assert set(inference_input(corrupt))=={'id','claim','reference'}
        bad=copy.deepcopy(ann);bad['review']['status']='needs_review'
        assert 'review_not_approved' in reason_issues(row,bad)
        try:build_record(row,'train','verdict_reason',bad)
        except ValueError:pass
        else:raise AssertionError('Draft was promoted')
        bad=copy.deepcopy(ann);bad['ai_assisted']=False
        assert 'ai_assisted_must_be_true_for_this_batch' in reason_issues(row,bad)
        bad=copy.deepcopy(ann);bad['review'].pop('complete_sentences')
        assert 'complete_sentence_count_not_attested' in reason_issues(row,bad)
        bad=copy.deepcopy(ann);bad['review']['unresolved_issues']=['ambiguous','unsupported_modifier']
        assert {'ambiguous','unsupported_modifier'}<=set(reason_issues(row,bad))
        bad=copy.deepcopy(ann);bad['evidence_sources'][0]['fully_read']=False
        assert 'whole_reference_review_unverified' in reason_issues(row,bad)
        bad=copy.deepcopy(ann);bad['evidence_sources'][0]['review_record']=True
        assert 'whole_reference_review_unverified' in reason_issues(row,bad)
        discord=dict(row,paper_r1=LABELS[(j+1)%3]);bad=copy.deepcopy(ann);bad['review'].pop('teacher_disagreement_reviewed')
        assert 'teacher_disagreement_requires_review' in reason_issues(discord,bad)
        assert reason_issues(row,None)==['missing_reason']
    padded=pad_encoded(encoded,tok.convert_tokens_to_ids('<|im_end|>'))
    for source,ids,labels,groups,mask in zip(encoded,padded['input_ids'],padded['labels'],padded['groups'],padded['attention_mask']):
        end=len(source['input_ids'])
        assert all(x==-100 for x in labels[end:]) and all(x==0 for x in groups[end:]) and all(x==0 for x in mask[end:])
    import training104
    assert INSTRUCTIONS.split('\n4. ')[0]==training104.INSTRUCTIONS.split('\n4. ')[0]
    assert messages('x','y')[0]==training104.messages('x','y')[0]
    assert 'optional key "reason"' in OUTPUT_RULE
    # Exercise the unchanged105 loss using a small synthetic vocabulary.
    torch.manual_seed(127);hidden=torch.randn(1,8,4,requires_grad=True)
    head=nn.Linear(4,13,bias=False);head.weight.requires_grad_(False)
    tokens=torch.tensor([[1,2,3,4,5,6,7,8]])
    groups=torch.tensor([[0,0,0,2,1,1,2,0]])
    loss,info=segmented_hidden_loss(hidden,head,tokens,groups,chunk_tokens=2,checkpoint_head=False)
    logits=head(hidden[:,:-1]);ce=F.cross_entropy(logits.reshape(-1,13),tokens[:,1:].reshape(-1),reduction='none').reshape(1,-1)
    kind=groups[:,1:];expected=ce[kind==1].mean()+ce[kind==2].mean()
    torch.testing.assert_close(loss,expected)
    loss.backward();assert hidden.grad[:,:2].abs().sum()==0 and hidden.grad[:,2:6].abs().sum()>0
    assert info['verdict_tokens']==2 and info['other_tokens']==2
    plan=training_plan([str(i) for i in range(9)],epochs=1,accumulation=8)
    assert [r['loss_divisor'] for r in plan]==[8,1]
    pool,roles=load_pool()
    assert len(pool)==3675 and len(roles)==40
    assert sum(roles[str(r['sid'])]=='train' for r in pool)==2945
    assert sum(roles[str(r['sid'])]=='validation' for r in pool)==730
    result=dict(status='PASS',contract_version=VERSION,real_reason_generated=False,real_model_fitted=False,
        GPU_calls=0,API_calls=0,exact_verdict_span_with_label_words_in_reason=True,
        JSON_escaping_and_EOS=True,prompt_and_pad_masks=True,GT_free_input=True,
        unchanged105_segmented_loss=True,tail_divisor=True,patient32_8_isolation=True,
        unapproved_reason_rejected=True,original104_task_and_classes_preserved=True)
    out=ROOT/'.local_models/127_native_reason_data/cpu_contract_selfcheck.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
