"""Freeze20 native-pair diagnostic cases; optionally bind actual final369 proof."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT/'.local_models/120_full_pool_sft/native_reason_check'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as common
from tokenizer_cpu105 import CPUPinnedTokenizer
from native_reason_check import prompt_ids,parse_pair

def rank(row):return hashlib.sha256(('120/native_reason_check_v1/'+row['id']).encode()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--bind-final369',type=Path);args=p.parse_args()
    keys=[r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl') if r.get('old_panel') in ('natural','pressure')]
    inputs={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')}
    old={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    midpoint={r['id']:r for r in common.rows(ROOT/'outputs/120_full_pool_sft/midpoint220_1817_predictions_sanitized.jsonl')}
    def group(r):
        a=old[r['id']]['verdict'];b=midpoint[r['id']]['verdict'];g=r['GT']
        return 'rescued' if a!=g and b==g else 'harmed' if a==g and b!=g else 'unchanged' if a==b else 'changed_still_wrong'
    selected=[]
    for label,n in [('Supported',12),('Not Supported',4),('Not Addressed',4)]:
        pool=sorted([dict(r,selection_group=group(r)) for r in keys if r['GT']==label],key=rank)
        quota={'rescued':4 if n==12 else 1,'harmed':4 if n==12 else 1,'unchanged':4 if n==12 else 2}
        chosen=[]
        for name,q in quota.items():chosen.extend([r for r in pool if r['selection_group']==name][:q])
        have={r['id'] for r in chosen};chosen.extend([r for r in pool if r['id'] not in have][:n-len(chosen)])
        assert len(chosen)==n;selected.extend(chosen)
    selected=sorted(selected,key=rank);assert len({r['id'] for r in selected})==20
    if (PRIVATE/'metadata.jsonl').exists():assert common.rows(PRIVATE/'metadata.jsonl')==selected
    common.putl(PRIVATE/'metadata.jsonl',selected)
    common.putl(PRIVATE/'paper_r1_history.jsonl',[dict(id=r['id'],verdict=r['paper_r1'],
        source='author historical prediction; no required historical reason') for r in selected])
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    raw=[];lengths=[]
    for r in selected:
        source=inputs[r['id']];item=dict(id=r['id'],claim=source['claim'],reference=source['reference'])
        tokens=prompt_ids(tok,item);item['expected_prompt_sha256']=common.digest(common.canonical(tokens));raw.append(item)
        lengths.append(dict(id=r['id'],input_tokens=len(tokens)))
    assert max(r['input_tokens']+768 for r in lengths)<=16384
    common.putl(PRIVATE/'lengths.jsonl',lengths)
    bundle=PRIVATE/'bundle';common.putl(bundle/'data/native_reason_check/inputs.jsonl',raw)
    source=common.read(ROOT/'.local_models/117_verdict_probe/features_initial.json')
    proof=None
    if args.bind_final369:
        done=common.read(args.bind_final369)
        assert done['steps']==369 and done['consumed']==2945
        proof={k:done[k] for k in ('steps','consumed','final_checkpoint','adapter_sha256')}
    job=dict(name='native_reason_check',model_dir=source['model_dir'],inputs='data/native_reason_check/inputs.jsonl',
        ids=[r['id'] for r in selected],max_seq_length=16384,phase_limit_seconds=1200,final369_proof=proof,
        arms=[dict(name='base_original9b',mode='base',adapter=None,adapter_sha256=None),
              dict(name='label_only107',mode='adapter',adapter=source['adapter_path'],adapter_sha256=source['adapter_sha256']),
              dict(name='final369_120',mode='adapter',adapter=proof['final_checkpoint'] if proof else None,adapter_sha256=proof['adapter_sha256'] if proof else None)])
    common.put(PRIVATE/'job.json',job);common.put(bundle/'data/native_reason_check/job.json',job)
    for rel in ['tasks/120_full_pool_sft/native_reason_check.py','tasks/103_lora_selection/prompt103.py','tasks/103_lora_selection/parse103.py','tasks/105_brief_supervision/common105.py']:
        dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest)
    protocol=dict(name='native_reason_check',status='BOUND_NOT_RUN' if proof else 'WAITING_FOR_ACTUAL_FINAL369',
        diagnostic_only=True,GT_counts=dict(Counter(r['GT'] for r in selected)),patients=len({r['sid'] for r in selected}),
        selection='Only old500; class12/4/4; quota rescued/harmed/unchanged=4/4/4 forS and1/1/2 forNS,NA using existing107 vs220; shortages filled by fixed hash',
        actual_selection_groups={g:dict(Counter(r['selection_group'] for r in selected if r['GT']==g)) for g in common.LABELS},
        future369_outputs_used_in_selection=False,prompt='unchanged103 author-style native reason-required prompt',
        decoding=dict(dtype='BF16',greedy=True,thinking=False,max_new_tokens=768,batch_size=1),
        first_responses=60,actual_generation_arms=['base_original9b','label_only107','final369_120'],
        historical_fourth_row='paper_r1_history.jsonl; not supplied to GPU',
        one_shared_base=True,base_all_adapters_disabled=True,adapter_arms_activated_separately=True,
        invalid_responses_retained=True,old_reason_reused=False,label_rewrite=False,
        review_fields=['reason_label_consistency:consistent/inconsistent/unclear','input_support:supported/contradicted/insufficient/ambiguous'],
        interpretation='Logical consistency is necessary only; not evidence of faithful internal reasoning or clinical correctness. Not population accuracy.',
        faithfulness_caution_source='https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract.html',
        main120_prompt_loss_outputs_and_scores_unchanged=True,new_training=False,new_GPU=False,new_API=False)
    common.put(PRIVATE/'protocol.json',protocol)
    with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():archive.add(path,arcname=path.relative_to(bundle).as_posix(),recursive=False)
    assert parse_pair('{"verdict":"Supported","reason":"The record explicitly supports it."}','stop')['diagnostic_pair_valid']
    assert not parse_pair('{"verdict":"Supported"}','stop')['diagnostic_pair_valid']
    assert not parse_pair('{"verdict":"Supported","reason":"Text"}','length')['diagnostic_pair_valid']
    print(common.canonical(dict(status=protocol['status'],N=20,GT=protocol['GT_counts'],patients=protocol['patients'],groups=protocol['actual_selection_groups'],
        total_input_tokens=sum(r['input_tokens'] for r in lengths),max_input_tokens=max(r['input_tokens'] for r in lengths),bundle_bytes=(PRIVATE/'bundle.tar.gz').stat().st_size)))

if __name__=='__main__':main()
