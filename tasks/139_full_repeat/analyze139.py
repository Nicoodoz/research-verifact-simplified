"""139 first-receipt evaluation; reused project metrics and paired comparison."""
from pathlib import Path
from collections import Counter
import argparse, json, statistics, sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision')); import common105 as c
sys.path.insert(0,str(R/'tasks/120_full_pool_sft')); from final_compare120 import metrics,paired,LABELS
sys.path.insert(0,str(R/'tasks/135_reason_first')); from analyze135 import collect
P=R/'.local_models/139_full_repeat'; DEFAULT_OUT=R/'outputs/139_full_repeat'


def compare(rows, reference, candidate, name, bootstrap=False):
    if not rows:return None
    value=paired(rows,{r['id']:dict(verdict=reference[r['id']]) for r in rows},
                 {r['id']:dict(verdict=candidate[r['id']]) for r in rows},name,bootstrap=bootstrap)
    value['scores']['full_repeat']=value['scores'].pop('candidate')
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=['screen160','old500','full1817'])
    p.add_argument('--results',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,default=DEFAULT_OUT)
    p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
    keys={r['id']:r for r in c.rows(P/'source/keys.jsonl')};screen=set(c.read(P/'source/screen160_ids.json'))
    targets=screen if a.scope=='screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope=='old500' else set(keys))
    raw=collect(a.results)
    if not set(raw)<=targets:raise ValueError('Receipts outside the requested frozen target')
    saved_inputs={r['id']:r for r in c.rows(P/'source/all1817_inputs.jsonl')}
    settings=c.read(P/'source/settings.json')
    for i,row in raw.items():
        if row.get('arm')!='full_repeat' or row.get('adapter_sha256')!=settings['adapter_sha256']:
            raise ValueError('Wrong139 candidate or source weights')
        if row.get('prompt_token_sha256')!=saved_inputs[i]['prompt_token_sha256']:
            raise ValueError('Not the frozen full_repeat input')
        if row['parsed']['valid'] and row['parsed']['verdict'] not in LABELS:raise ValueError('Unknown label')
    valid=sorted(i for i in targets if i in raw and raw[i]['parsed']['valid'])
    missing=sorted(targets-set(raw));invalid=sorted(i for i in targets&set(raw) if not raw[i]['parsed']['valid'])
    rows=[keys[i] for i in valid];new={i:raw[i]['parsed']['verdict'] for i in valid}
    specs=[('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),
           ('claim_repeat136',R/'outputs/136_claim_repeat_transfer/full1817_predictions_sanitized.jsonl','claim_repeat'),
           ('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl','verdict'),
           ('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132'),
           ('extra_steps137',R/'outputs/137_extra_steps/full1817_predictions_sanitized.jsonl','extra_steps')]
    models={};source_rows={}
    for name,path,field in specs:
        data={r['id']:r for r in c.rows(path)};source_rows[name]=data
        if not targets<=set(data):raise ValueError('Required baseline lacks requested IDs: '+name)
        models[name]={i:data[i][field] for i in targets}
    models['paper_r1']={i:keys[i]['paper_r1'] for i in targets}
    primary=compare(rows,models['full_pool120'],new,'full_pool120',a.bootstrap)
    versus136=compare(rows,models['claim_repeat136'],new,'claim_repeat136',a.bootstrap)
    groups={'all':rows,'natural':[r for r in rows if r['old_panel']=='natural'],
            'pressure':[r for r in rows if r['old_panel']=='pressure'],
            'new1317':[r for r in rows if r['subset']=='new'],
            'history103_180':[r for r in rows if r['history103_panel'] in ('natural','pressure')]}
    panels={name:compare(rs,models['full_pool120'],new,'full_pool120') for name,rs in groups.items() if rs}
    main_scores={name:metrics(rows,{r['id']:pred[r['id']] for r in rows}) for name,pred in models.items()} if rows else {}
    if rows:main_scores['full_repeat']=metrics(rows,new)
    B=R/'.local_models/134_author_baselines'
    author={name:collect([B/'bundle/results'/name,B/'evidence'/name]) for name in ['author_base9b','author_lora9b']}
    core=[r for r in rows if all(r['id'] in d and d[r['id']]['parsed']['valid'] for d in author.values())]
    core_scores={name:metrics(core,{r['id']:d[r['id']]['parsed']['verdict'] for r in core}) for name,d in author.items()} if core else {}
    if core:
        core_scores.update({name:metrics(core,{r['id']:pred[r['id']] for r in core}) for name,pred in models.items()})
        core_scores['full_repeat']=metrics(core,new)
    #104 same-prompt unfine-tuned9B is only shown on its actual valid overlap.
    base104={r['id']:r for r in c.rows(R/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r['arm']=='base_judge'}
    overlap=[r for r in rows if r['id'] in base104 and base104[r['id']]['parsed']['valid']]
    same_prompt=dict(N=len(overlap),scores={})
    if overlap:
        same_prompt['scores']={'base104_9b':metrics(overlap,{r['id']:base104[r['id']]['parsed']['verdict'] for r in overlap}),
            'full_pool120':metrics(overlap,models['full_pool120']),'full_repeat':metrics(overlap,new),
            'label_only107':metrics(overlap,models['label_only107']),
            'paper_r1':metrics(overlap,models['paper_r1'])}
    screening=dict(applicable=a.scope!='full1817',continue_signal=False,reason='No valid paired outputs')
    if primary and a.scope!='full1817':
        oldm=primary['scores']['full_pool120'];newm=primary['scores']['full_repeat'];small=a.scope=='screen160'
        quality=primary['delta_MCC']>=(.015 if small else .01) or (primary['delta_correct']>=(3 if small else 5) and primary['delta_MCC']>=-.01)
        risk=primary['delta_false_S']<=(-2 if small else -5) and primary['delta_correct']>=(-3 if small else -5) and primary['delta_MCC']>=(-.03 if small else -.02)
        guards=dict(valid_coverage=len(valid)/len(targets)>=.95,all_first_requests_returned=not missing,
            no_large_false_S_jump=primary['delta_false_S']<=(3 if small else 5),
            no_major_class_collapse=all(newm['per_class'][g]['tp']>=.5*oldm['per_class'][g]['tp'] for g in LABELS if oldm['per_class'][g]['tp']>=6),
            no_near_zero_class=all(oldm['per_class'][g]['recall'] is None or oldm['per_class'][g]['recall']<.1 or newm['per_class'][g]['recall']>=.05 for g in LABELS))
        screening=dict(applicable=True,quality_signal=quality,risk_signal=risk,guards=guards,continue_signal=bool(all(guards.values()) and (quality or risk)))
    elif a.scope=='full1817':screening=dict(applicable=False,continue_signal=None,reason='Completed fixed final cohort; report actual gains and costs')
    correct=main_scores.get('full_repeat',{}).get('correct',0)
    deltas=[raw[i]['input_tokens']-source_rows['full_pool120'][i]['input_tokens'] for i in raw]
    result=dict(task=139,candidate='full_repeat',scope=a.scope,expected_N=len(targets),joint_valid_N=len(valid),
        primary=primary,versus_claim_repeat136=versus136,scores=main_scores,panels=panels,
        by_author={label:compare([r for r in rows if r['author']==label],models['full_pool120'],new,'full_pool120') for label in sorted({r['author'] for r in rows})},
        three_baseline_common_N=len(core),three_baseline_common_scores=core_scores,same_prompt_unfinetuned_overlap=same_prompt,
        coverage=dict(received_N=len(raw),valid_N=len(valid),invalid_N=len(invalid),missing_N=len(missing),
            invalid_ids=invalid,missing_ids=missing,invalid_by_GT=dict(Counter(keys[i]['GT'] for i in invalid))),
        PA_full_target_bounds=[correct/len(targets),(correct+len(invalid)+len(missing))/len(targets)],
        screening=screening,input_cost=dict(received_N=len(raw),mean_extra_tokens=statistics.mean(deltas) if deltas else None,
            total_extra_tokens=sum(deltas),output_cap=384,batch_size=1,capacity=32768),
        no_label_rewrite=True,new_training=False,new_API=0,reason_consistency_proven=False)
    a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/(a.scope+'.json'),result)
    c.putl(a.out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],full_pool120=models['full_pool120'][i],claim_repeat136=models['claim_repeat136'][i],full_repeat=new[i]) for i in valid])
    c.putl(a.out/(a.scope+'_receipt_status_sanitized.jsonl'),[dict(id=i,GT=keys[i]['GT'],status='missing' if i not in raw else ('valid' if i in new else 'invalid'),
        valid=i in new,verdict=new.get(i),finish_reason=raw[i]['finish_reason'] if i in raw else None) for i in sorted(targets)])
    lines=['#139 full_repeat：'+a.scope,'',f'目标{len(targets)}，返回{len(raw)}，有效{len(valid)}，无效{len(invalid)}，缺失{len(missing)}。无效和缺失不补旧答案。','',
        '|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for name,m in main_scores.items():
        rec='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
        lines.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{rec}|")
    for name,value in [('120',primary),('136',versus136)]:
        if value:lines+=['',f"相对{name}：ΔMCC{value['delta_MCC']:+.4f}，Δ正确{value['delta_correct']:+d}，Δfalse-S{value['delta_false_S']:+d}。"]
    lines+=['',f"原作者提示两9B基线的共同覆盖为{len(core)}，104未微调9B共同覆盖为{len(overlap)}；独立同ID表见JSON，不跨覆盖作差。",'',
        '三类precision/recall/F1、混淆矩阵、false-S率和预测S假发现率、患者/作者/面板方向见JSON。完整1817按1000次患者bootstrap；不覆盖历史选型或新医院泛化。',
        '同120权重，完整原文；batch1和32768容量与原缓存运行设置不同，未声称逐位一致或理由自洽。','',
        '扩大信号：'+json.dumps(screening,ensure_ascii=False),'']
    (a.out/(a.scope+'.md')).write_bytes('\n'.join(lines).encode('utf-8'))
    print(c.canonical(dict(task=139,scope=a.scope,received=len(raw),valid=len(valid),missing=len(missing),invalid=len(invalid),
        delta_MCC=primary['delta_MCC'] if primary else None,delta_correct=primary['delta_correct'] if primary else None,
        delta_false_S=primary['delta_false_S'] if primary else None,screening=screening)))


if __name__=='__main__':main()
