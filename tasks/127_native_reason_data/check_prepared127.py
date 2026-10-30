"""Check added real pairs with the pinned tokenizer; reuse unchanged old checks."""
from pathlib import Path
import argparse,json,sys
from data_contract127 import ROOT,assert_pair,encode
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer

def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def pairs(folder):
    labels=[];reasons=[]
    for role in ('train','validation'):
        labels+=rows(folder/'paired'/(role+'_label_only.jsonl'))
        reasons+=rows(folder/'paired'/(role+'_verdict_reason.jsonl'))
    assert [x['id'] for x in labels]==[x['id'] for x in reasons]
    return {a['id']:(a,b) for a,b in zip(labels,reasons)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--reuse-dataset',type=Path,required=True);a=p.parse_args()
    old_check=json.loads((a.reuse_dataset/'encoding_check.json').read_text())
    assert old_check['status']=='PASS'
    old=pairs(a.reuse_dataset);current=pairs(a.dataset)
    assert set(old)<=set(current)
    for i,(label,reason) in old.items():
        assert_pair(*current[i])
        for arm,reference in zip(current[i],(label,reason)):
            assert all(arm[k]==reference[k] for k in ('id','sid','GT','claim','reference','fit_role','answer'))
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    detail=[]
    for i in sorted(set(current)-set(old)):
        label,reason=current[i];assert_pair(label,reason)
        left,right=encode(tok,label),encode(tok,reason)
        assert left['prompt_token_sha256']==right['prompt_token_sha256']
        assert len(right['input_ids'])<=16384
        for item,encoded in ((label,left),(reason,right)):
            prefix=encoded['prompt_tokens'];suffix=encoded['input_ids'][prefix:]
            assert tok.decode(suffix[:-1],skip_special_tokens=False)==item['answer']
            assert tok.decode([suffix[k] for k in encoded['verdict_answer_token_indices']],skip_special_tokens=False)==item['GT']
            assert all(x==-100 for x in encoded['labels'][:prefix])
            assert all(x==0 for x in encoded['groups'][:prefix])
            assert encoded['groups'][-1]==2 and suffix[-1]==tok.convert_tokens_to_ids('<|im_end|>')
        detail.append(dict(id=i,GT=label['GT'],fit_role=label['fit_role'],prompt_tokens=right['prompt_tokens'],
            total_tokens=len(right['input_ids']),same_prompt=True,verdict_span_correct=True))
    result=dict(status='PASS',pairs=len(current),unchanged_prior_checks_reused=len(old),new_pairs_encoded=len(detail),
        old_source_and_target_equal=True,full_input_no_truncation=True,original_GT_preserved=True,
        GPU_calls=0,API_calls=0,model_loaded=False,details=detail)
    (a.dataset/'encoding_check.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
