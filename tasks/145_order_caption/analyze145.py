"""CPU analysis of the fixed caption-only145 contrast against original142."""
from pathlib import Path
import argparse
import statistics
import sys

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/142_relevance_order'))
from analyze142 import (c, indexed, collect142, valid_raw, coverage, metrics, paired_subset,
                        common_table, inference_cost, frozen_jobs, baseline136, SOURCE120_SHA, LABELS)
sys.path.insert(0,str(R/'tasks/140_kl_anchor'))
from analyze140 import flat_predictions
from caption145 import replace_caption, OLD, NEW

P=R/'.local_models/145_order_caption'
P142=R/'.local_models/142_relevance_order/screen160'
K=R/'.local_models/134_author_baselines'
O=R/'outputs/145_order_caption'


def frozen145(bundle, keys):
    folder=bundle/'data';job=c.read(folder/'job.json')
    old_folder=P142/'bundle/data';old_job=c.read(old_folder/'job.json')
    screen=set(c.read(K/'job.json')['phases'][0]['ids'])
    if (job.get('task')!=145 or job.get('arm')!='order_caption' or job.get('scope')!='screen160'
            or job.get('expected_N')!=160 or set(job['ids'])!=screen
            or job.get('adapter_sha256')!=SOURCE120_SHA or job.get('new_training') is not False
            or job.get('max_seq_length')!=16384 or job['generation']!=old_job['generation']
            or job['batches']!=old_job['batches']):
        raise ValueError('Not the fixed145 source, scope, runtime or original142 batching')
    if (job.get('source_job_sha256')!=c.sha(old_folder/'job.json')
            or job.get('source_inputs_sha256')!=c.sha(old_folder/'inputs.jsonl')):
        raise ValueError('Original142 source fingerprint changed')
    edits_path=bundle/job['caption_edits_file']
    if c.sha(edits_path)!=job['caption_edits_sha256']:
        raise ValueError('Caption edit manifest changed')
    old_inputs=indexed(old_folder/'inputs.jsonl');inputs=indexed(folder/'inputs.jsonl')
    lengths=indexed(folder/'lengths.jsonl');edits=indexed(edits_path)
    old_lengths,_,old_batches=frozen_jobs('screen160',keys)
    if any(set(data)!=screen for data in (old_inputs,inputs,lengths,edits)):
        raise ValueError('Fixed145 inputs/lengths/edits do not cover the same160')
    batches={i:len(batch) for batch in job['batches'] for i in batch}
    if len(batches)!=160 or batches!=old_batches:
        raise ValueError('Original142 batch assignments changed')
    for i in screen:
        old,new=old_inputs[i],inputs[i]
        reference,edit=replace_caption(old['reference'])
        if new['claim']!=old['claim'] or new['reference']!=reference:
            raise ValueError('A non-caption clinical character changed: '+i)
        if (any(edits[i].get(k)!=v for k,v in edit.items())
                or edits[i]['old_reference_sha256']!=c.digest(old['reference'])
                or edits[i]['new_reference_sha256']!=c.digest(reference)
                or lengths[i]['source_prompt_token_sha256']!=old_lengths[i]['prompt_token_sha256']
                or lengths[i]['source_input_tokens']!=old_lengths[i]['input_tokens']
                or lengths[i]['prompt_token_sha256']!=new['prompt_token_sha256']
                or new['source_prompt_token_sha256']!=old['prompt_token_sha256']
                or lengths[i]['claim_repeat_prompt_token_sha256']!=old_lengths[i]['source_prompt_token_sha256']
                or lengths[i]['input_tokens']+384>16384):
            raise ValueError('Caption/source/token manifest mismatch: '+i)
        if edits[i]['token_delta']!=lengths[i]['input_tokens']-lengths[i]['source_input_tokens']:
            raise ValueError('Token delta mismatch: '+i)
    return job,lengths,old_lengths,batches,dict(job_sha256=c.sha(folder/'job.json'),
        inputs_sha256=c.sha(folder/'inputs.jsonl'),lengths_sha256=c.sha(folder/'lengths.jsonl'),
        caption_edits_sha256=c.sha(edits_path),source142_job_sha256=c.sha(old_folder/'job.json'),
        exact_caption_only_verified_N=160,old_caption=OLD,new_caption=NEW)


def verify(raw, arm, lengths, batches, source_field='source_prompt_token_sha256'):
    for i,row in raw.items():
        expected=lengths[i]
        if (row.get('arm')!=arm or row.get('adapter_sha256')!=SOURCE120_SHA
                or row.get('source_checkpoint')!='120_final369'
                or row.get('prompt_token_sha256')!=expected['prompt_token_sha256']
                or row.get(source_field)!=expected['source_prompt_token_sha256']
                or row.get('input_tokens')!=expected['input_tokens'] or row.get('batch_size')!=batches[i]
                or (valid_raw(row) and row.get('finish_reason')!='stop')):
            raise ValueError('Actual receipt differs from frozen source/prompt/batch: '+i)


def analyze(bundle, paths, bootstrap=False):
    keys=indexed(K/'keys.jsonl');target=set(c.read(K/'job.json')['phases'][0]['ids'])
    job,lengths,old_lengths,batches,provenance=frozen145(bundle,keys)
    paths=paths or [P/'screen160/evidence/order_caption']
    old_paths=[P142/'evidence/relevance_order']
    raw=collect142(paths);old_raw=collect142(old_paths)
    if (set(raw)|set(old_raw))-target:
        raise ValueError('Receipt outside fixed145/142 screen160')
    verify(raw,'order_caption',lengths,batches)
    verify(old_raw,'relevance_order',old_lengths,batches)
    candidate={i:r['parsed']['verdict'] for i,r in raw.items() if valid_raw(r)}
    old={i:r['parsed']['verdict'] for i,r in old_raw.items() if valid_raw(r)}
    joint=sorted(candidate.keys()&old.keys())
    if not joint:
        raise ValueError('No valid actual145/142 paired first outputs; no fabricated result')
    primary=paired_subset(joint,old,candidate,'relevance_order142',keys,bootstrap)
    base136,base_provenance=baseline136()
    pred136={i:r['parsed']['verdict'] for i,r in base136.items() if i in target and valid_raw(r)}
    history={'claim_repeat136':pred136,'paper_r1':{i:keys[i]['paper_r1'] for i in target}}
    for name,path in [('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl'),
                           ('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')]:
        history[name]=flat_predictions(indexed(path),keys,'verdict','valid')
    sources=dict(order_caption145=candidate,relevance_order142=old,**history)
    groups=dict(natural=[i for i in joint if keys[i]['old_panel']=='natural'],
                pressure=[i for i in joint if keys[i]['old_panel']=='pressure'],
                new1317=[i for i in joint if keys[i]['subset']=='new'],
                history103_180=[i for i in joint if keys[i]['history103_panel'] in ('natural','pressure')])
    result=dict(task=145,arm='order_caption',scope='screen160',expected_N=160,valid_N=len(candidate),
        joint_valid_N=len(joint),source_adapter_sha256=SOURCE120_SHA,primary=primary,
        standalone_candidate=metrics([keys[i] for i in sorted(candidate)],candidate),
        coverage=dict(candidate=coverage(target,raw),relevance_order142=coverage(target,old_raw),
                      claim_repeat136=coverage(target,base136)),
        historical_common=common_table(joint,sources,keys),
        panels={name:paired_subset(ids,old,candidate,'relevance_order142',keys) for name,ids in groups.items() if ids},
        by_author={name:paired_subset([i for i in joint if keys[i]['author']==name],old,candidate,'relevance_order142',keys)
                   for name in sorted({keys[i]['author'] for i in joint})},
        by_patient={str(sid):paired_subset([i for i in joint if keys[i]['sid']==sid],old,candidate,'relevance_order142',keys)
                    for sid in sorted({keys[i]['sid'] for i in joint})},
        source_artifacts=provenance,baseline136_provenance=base_provenance,
        bootstrap=dict(performed=bootstrap,iterations=1000 if bootstrap else 0),
        inference_cost=dict(order_caption145=inference_cost(raw,target,paths),
                            relevance_order142=inference_cost(old_raw,target,old_paths)),
        input_cost=dict(paired_N=len(joint),mean_extra_tokens=statistics.mean(lengths[i]['input_tokens']-lengths[i]['source_input_tokens'] for i in joint),
                        total_extra_tokens=sum(lengths[i]['input_tokens']-lengths[i]['source_input_tokens'] for i in joint)),
        no_new_training=True,no_new_API=True,no_label_rewrite=True,no_postprocessing=True,
        reason_consistency_proven=False,analysis_only=True)
    author_paths=[K/'bundle/results/author_base9b',K/'evidence/author_base9b']
    author=collect142(author_paths)
    author_pred={i:r['parsed']['verdict'] for i,r in author.items() if i in target and valid_raw(r)}
    result['author_base9b_common']=common_table(joint,dict(sources,author_base9b=author_pred),keys)
    result['author_base9b_coverage']=coverage(target,author)
    predictions=[dict(keys[i],order_caption=candidate[i],relevance_order142=old.get(i),primary_joint_valid=i in old)
                 for i in sorted(candidate)]
    receipts=[dict(id=i,GT=keys[i]['GT'],received=i in raw,valid=i in candidate,baseline_received=i in old_raw,
                   baseline_valid=i in old,verdict=candidate.get(i),finish_reason=raw[i].get('finish_reason') if i in raw else None)
              for i in sorted(target)]
    return result,predictions,receipts


def num(value,percent=False):
    return 'NA' if value is None else (f'{value:.2%}' if percent else f'{value:.4f}')


def table(scores):
    lines=['|配置|MCC|PA|正确|false-S/非S|Macro-F1|','|---|---:|---:|---:|---:|---:|']
    for name,m in scores.items():
        label='order_caption145' if name=='candidate' else name
        lines.append(f"|{label}|{num(None if m.get('mcc_denominator_zero') else m['mcc'])}|{num(m['percent_agreement'],True)}|{m['correct']}|{m['false_S']}/{m['non_S']}|{num(m['macro_F1'])}|")
    return lines


def render(v):
    p=v['primary'];lines=['# 145：排序说明修正的固定160比较','',
        f"目标160，145有效{v['valid_N']}，与142共同有效{v['joint_valid_N']}。只更改全局caption，完整片段及顺序、claim、GT、模型与批次均已核验不变。",'',
        '## 主比较：145对原142','']+table(p['scores'])
    lines += ['',f"ΔMCC {p['delta_MCC']:+.4f}，ΔPA {p['delta_PA']:+.2%}，正确{p['delta_correct']:+d}，false-S {p['delta_false_S']:+d}。",'',
              f"## 其余基线共同{v['historical_common']['N']}条",'']+table(v['historical_common']['scores'])
    lines += ['',f"## 作者提示未微调9B共同{v['author_base9b_common']['N']}条",'']+table(v['author_base9b_common']['scores'])
    lines += ['', '作者9B为原作者prompt和768输出预算；145/142为相同120权重与104体系、384上限。仅145对142可直接归因于此次caption差异。', '',
              '|GT|救回|误伤|净正确|','|---|---:|---:|---:|']
    for label,x in p['changes']['by_class'].items():lines.append(f"|{label}|{x['rescued']}|{x['harmed']}|{x['rescued']-x['harmed']:+d}|")
    lines += ['',f"false-S新增{p['changes']['false_S_new']}、避免{p['changes']['false_S_avoided']}。",'',
              '|面板/作者|N|ΔMCC|Δ正确|ΔFS|','|---|---:|---:|---:|---:|']
    for family in ('panels','by_author'):
        for name,x in v[family].items():lines.append(f"|{name}|{x['N']}|{x['delta_MCC']:+.4f}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
    lines += ['', '|患者|N|Δ正确|ΔFS|','|---|---:|---:|---:|']
    for name,x in v['by_patient'].items():lines.append(f"|{name}|{x['N']}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
    for name,m in p['scores'].items():
        lines += ['',name+'三类表现','', '|GT|Precision|Recall|F1|','|---|---:|---:|---:|']
        for g in LABELS:lines.append('|'+g+'|'+'|'.join(num(m['per_class'][g][f]) for f in ('precision','recall','f1'))+'|')
        lines += ['', '混淆矩阵（行GT、列预测：S/NS/NA）','', '|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
        lines += ['|'+g+'|'+'|'.join(map(str,row))+'|' for g,row in zip(('S','NS','NA'),m['confusion_matrix'])]
    if 'patient_bootstrap' in p:
        for key in ('mcc','percent_agreement'):
            lo,hi=p['patient_bootstrap']['metrics'][key]['ci95'];lines += ['',f'患者配对Δ{key} 95%区间[{lo:+.4f},{hi:+.4f}]。']
        lines += ['1000次患者cluster bootstrap，不覆盖历史选型、再次运行或新医院泛化。']
    else:lines += ['', '未请求bootstrap，不虚构区间。']
    lines += ['', '## 覆盖与实测成本','', '|配置|收到/有效|缺失/无效|输入tokens|输出tokens|生成秒数|','|---|---:|---:|---:|---:|---:|']
    walls=[]
    for name,key in [('order_caption145','candidate'),('relevance_order142','relevance_order142')]:
        cov=v['coverage'][key];cost=v['inference_cost'][name]
        lines.append(f"|{name}|{cov['received_N']}/{cov['valid_N']}|{len(cov['missing_ids'])}/{len(cov['invalid_ids'])}|{cost['input_tokens']['sum']}|{cost['output_tokens']['sum']}|{num(cost['complete_generation_total'])}|")
        for wall in cost['phase_walls']:walls.append(f"{name}记录墙钟：{wall['kind']}，{num(wall['seconds'])}秒；单独呈现，不与生成秒数相加。")
    lines += ['',*walls]
    lines += ['',f"同ID输入额外tokens：平均{v['input_cost']['mean_extra_tokens']:.2f}，合计{v['input_cost']['total_extra_tokens']}。",'',
              '生成seconds已按实际batch分摊，不重复累加每条batch_seconds；缺失时间字段为未知。进程/worker时间不包含全部准备、传输及等待，不能代替统一GPU账本。', '',
              '缺失/无效不填旧答案；只用原20名历史暴露患者，不改变医生GT或142旧结果，不借旧reason给新标签。本项是说明修正对照，不是新算法；标签成绩不证明reason自洽，160结果不自动授权扩大。', '',
              '[完整统计](order_caption_screen160.json) · [固定方案](../../tasks/145_order_caption/PROTOCOL.md)']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=P/'screen160/bundle')
    parser.add_argument('--results',type=Path,nargs='+')
    parser.add_argument('--bootstrap',action='store_true')
    parser.add_argument('--out',type=Path,default=O)
    args=parser.parse_args()
    result,predictions,receipts=analyze(args.bundle,args.results,args.bootstrap)
    prefix='order_caption_screen160'
    c.put(args.out/(prefix+'.json'),result)
    c.putl(args.out/(prefix+'_predictions_sanitized.jsonl'),predictions)
    c.putl(args.out/(prefix+'_receipt_status_sanitized.jsonl'),receipts)
    (args.out/'report.md').write_bytes(render(result).encode('utf-8'))
    p=result['primary'];print(c.canonical(dict(N=p['N'],delta_MCC=p['delta_MCC'],delta_correct=p['delta_correct'],delta_false_S=p['delta_false_S'])))


if __name__=='__main__':main()
