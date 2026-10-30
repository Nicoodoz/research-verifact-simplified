"""No-GPU package for the fixed conditional-state experiment."""
from collections import Counter
from pathlib import Path
import json,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT/'.local_models/126_conditional_state_readout'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as common
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(ROOT/'tasks/104_supervision_evidence'));import training104 as original

def main():
    if (PRIVATE/'preparation.json').exists():raise FileExistsError('Preserve prepared126 recipe')
    meta=common.rows(ROOT/'.local_models/117_verdict_probe/metadata.jsonl')
    assert Counter(r['role'] for r in meta)=={'train':1024,'validation':730,'screen':160}
    assert len({r['id'] for r in meta})==1914
    assert {role:len({str(r['sid']) for r in meta if r['role']==role}) for role in ('train','validation','screen')}=={'train':32,'validation':8,'screen':20}
    by={r['id']:r for r in common.rows(ROOT/'.local_models/106_label_preparation/training_pool.jsonl')}
    by.update({r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')})
    frozen={r['id']:r for r in common.rows(ROOT/'.local_models/117_verdict_probe/bundle/data/inputs.jsonl')}
    assert all(by[r['id']]['claim']==frozen[r['id']]['claim'] and by[r['id']]['reference']==frozen[r['id']]['reference'] for r in meta)
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    assert tok.encode('{"verdict":"',False)==[4754,415,8217,3147]
    assert tok.encode('{"verdict":"Not',False)==[4754,415,8217,3147,2536]
    for label in ['Not Supported','Not Addressed']:
        assert tok.encode(common.canonical({'verdict':label}),False)[:5]==[4754,415,8217,3147,2536]
    inputs=[];lengths=[]
    for row in meta:
        raw=by[row['id']];item=dict(id=row['id'],claim=raw['claim'],reference=raw['reference'])
        ids=original.prompt_ids(tok,item);item['expected_prompt_sha256']=common.digest(common.canonical(ids))
        inputs.append(item);lengths.append(dict(id=row['id'],role=row['role'],input_tokens=len(ids)+5))
    assert max(x['input_tokens'] for x in lengths)<=16384
    source=common.read(ROOT/'.local_models/117_verdict_probe/features_initial.json')
    job=dict(source,name='features126_initial',worker='extract126.py',ids=[r['id'] for r in meta],
        inputs='data/conditional126/inputs.jsonl',phase_limit_seconds=5400,batch_size=4)
    bundle=PRIVATE/'bundle';common.putl(bundle/'data/conditional126/inputs.jsonl',inputs)
    common.put(bundle/'data/features126_initial.json',job);common.put(PRIVATE/'job.json',job)
    common.putl(PRIVATE/'metadata.jsonl',meta);common.putl(PRIVATE/'lengths.jsonl',lengths)
    session=common.read(ROOT/'.local_models/122_balanced_pool_sft/runtime_session.json')
    common.put(bundle/'session.json',session)
    for name in ['tasks/126_conditional_state_readout/extract126.py','tasks/105_brief_supervision/common105.py','tasks/104_supervision_evidence/training104.py']:
        dest=bundle/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    source_cfg=common.read(ROOT/'.local_models/117_verdict_probe/mlp_initial/selection.json')['config']
    protocol=dict(task=126,candidate='conditional_state_readout',status='PREPARED_NOT_RUN',N=1914,
        split={'train':1024,'validation':730,'screen':160},model='frozen107 label_only',suffix_ids=[4754,415,8217,3147,2536],
        adapter_sha256=source['adapter_sha256'],original117_inputs_identical=True,
        suffix='same universal verdict JSON prefix followed by Not for every example',
        states={'verdict_prefix':'position before Not; cannot attend its future token','not_prefix':'position after fixed Not'},
        primary_feature='concat_verdict_prefix_not_prefix',feature_order=['verdict_prefix','not_prefix'],
        same_forward_prefix_control=True,MLP_config=source_cfg,one_candidate_no_search=True,
        evaluation='only fixed160 after internal730 epoch selection; no other1657 scores',
        session_copied_without_reset=session,remote_root='/root/autodl-tmp/verifact126',
        cost_basis='117 initial1914 historical wall3168.324s; all full prompts need prefill because noKV cache exists',
        estimated_GPU_minutes=[50,65],estimated_GPU_CNY_at1_58=[1.32,1.71],new_GPU_calls=0,new_API_calls=0)
    common.put(PRIVATE/'protocol.json',protocol)
    archive=PRIVATE/'bundle126.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as stream:
        for f in sorted(bundle.rglob('*')):
            if f.is_file():stream.add(f,arcname=f.relative_to(bundle).as_posix(),recursive=False)
    result=dict(N=1914,total_input_tokens=sum(x['input_tokens'] for x in lengths),max_input_tokens=max(x['input_tokens'] for x in lengths),
        bundle_bytes=archive.stat().st_size,expected_two_state_bytes=1914*4096*4*2,trained=False,GPU_started=False)
    common.put(PRIVATE/'preparation.json',result);print(common.canonical(result))

if __name__=='__main__':main()
