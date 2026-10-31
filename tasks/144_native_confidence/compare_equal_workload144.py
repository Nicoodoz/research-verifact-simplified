"""Fixed equal-workload144 comparison; k comes only from the143 disagreement rule.

No new score/threshold search, predictions, training, or changes to the five-point grid.
Requires an already complete144 effect analysis for the same frozen scope/job.
"""
from pathlib import Path
import argparse

import analyze144 as a
from analyze143 import EXPECTED_SHA, FILES


def compare(bundle, results, prior_analysis):
    job,inputs,data=a.read_job(bundle)
    prior=a.c.read(prior_analysis)
    if (job['scope']=='pilot' or job.get('evaluation_metrics_allowed') is not True
            or prior.get('effect_metrics_generated') is not True
            or prior.get('job_sha256')!=a.c.sha(data/'job.json')):
        raise ValueError('Require completed144 effect analysis for this exact frozen job')
    valid,invalid,missing,_,_,_=a.collect(results,set(inputs),inputs,job)
    if invalid or missing:
        raise ValueError('All prescribed scores must be valid; never use a scored subset')
    keys={row['id']:row for row in a.c.rows(a.KEYS)}
    targets=set(job['evaluation_ids'])
    native,source_info,problems=a.load_native(job,data,keys)
    if any(problems.values()):
        raise ValueError('Native predictions incomplete or invalid')
    path107=FILES['label_only107']
    if a.c.sha(path107)!=EXPECTED_SHA['label_only107']:
        raise ValueError('Original107 source fingerprint changed')
    raw107={row['id']:row for row in a.c.rows(path107)}
    if not targets<=raw107.keys() or any(raw107[i].get('valid') is not True for i in targets):
        raise ValueError('107 predictions do not cover the frozen target')
    for i in targets:
        if (raw107[i]['verdict'] not in a.LABELS or raw107[i]['GT']!=keys[i]['GT']
                or str(raw107[i]['sid'])!=str(keys[i]['sid'])):
            raise ValueError('107 source identity/label mismatch')
    auxiliary={i:raw107[i]['verdict'] for i in targets}
    rows=[keys[i] for i in sorted(targets)]
    output=dict(task=144,kind='fixed_equal_workload_retrospective',scope=job['evaluation_scope'],N=len(rows),
        prior_analysis_sha256=a.c.sha(prior_analysis),job_sha256=prior['job_sha256'],
        source107_sha256=EXPECTED_SHA['label_only107'],native_sources=source_info,
        workload_rule='k = count(native Supported and107 not Supported); GT never selects k',
        score_rule='ascending logit_S_minus_Not then ID; select exactly k original native Supported IDs',
        original_grid_unchanged=True,native_labels_unchanged=True,clinician_review_performed=False,
        new_GPU_calls=0,new_API_calls=0,variants={})
    for variant in job['variants']:
        labels=native[variant]
        supported={i for i in targets if labels[i]=='Supported'}
        if not supported<=set(job['score_ids_by_variant'][variant]):
            raise ValueError('Scoring job omits part of the original native S pool')
        disagreement={i for i in supported if auxiliary[i]!='Supported'}
        k=len(disagreement)
        margins={i:valid[(variant,i)]['logit_S_minus_Not'] for i in supported}
        ordered=sorted(supported,key=lambda i:(margins[i],i))
        score_review=set(ordered[:k])
        by107=a.selective_summary(rows,labels,disagreement)
        byscore=a.selective_summary(rows,labels,score_review)
        assert by107['automatic_N']==byscore['automatic_N']==len(rows)-k
        assert by107['review']['N']==byscore['review']['N']==k
        if by107['native']['confusion_matrix']!=prior['effects'][variant]['native']['confusion_matrix']:
            raise ValueError('Native metrics changed from the fixed144 analysis')
        events=[event for event in prior['cost']['attempt_events'] if event.get('variant')==variant and event.get('event')=='completed']
        costs=dict(native_S_pool=len(supported),
            disagreement_deployment=dict(main_generations=len(rows),conditional107_generations=len(supported),
                                         logical_generation_calls=len(rows)+len(supported)),
            margin_current_extraction=dict(score_records=len(supported),
                score_forward_seconds_all_records=sum(valid[(variant,i)]['seconds'] for i in supported),
                new_completed_events=len(events),new_completed_forward_seconds=sum(event['seconds'] for event in events if a.finite(event.get('seconds'))),
                frozen_reused_score_N=len(job.get('reused_score_ids_by_variant',{}).get(variant,[]))),
            prospective_same_prefill_capture='Could avoid a second prefill, but not implemented or benchmarked; do not claim zero marginal cost.',
            note='107 requires extra generation/adapter; current margin scores required separate same-model forwards. Shared loading/wall time is not allocated per variant.')
        overlap=disagreement&score_review
        output['variants'][variant]=dict(k=k,review_fraction_of_original_S=a.ratio(k,len(supported)),
            native=by107['native'],disagreement107=by107,native_margin=byscore,
            disagreement_review_ids=sorted(disagreement),margin_review_ids=ordered[:k],
            margin_boundary=margins[ordered[k-1]] if k else None,
            margin_boundary_id=ordered[k-1] if k else None,
            overlap_review_N=len(overlap),overlap_intercepted_FS=sum(keys[i]['GT']!='Supported' for i in overlap),
            margin_minus_disagreement=dict(intercepted_FS=byscore['review']['intercepted_false_S']-by107['review']['intercepted_false_S'],
                remaining_FS=byscore['remaining_automatic_false_S']-by107['remaining_automatic_false_S'],
                correct_S_reviewed=byscore['review']['deferred_correct_S']-by107['review']['deferred_correct_S']),
            cost=costs)
    output['recorded_stage_cost']=dict(worker_wall_seconds=prior['cost']['worker_wall_seconds'],
        controller_wall_seconds=prior['cost']['controller_wall_seconds'],
        recorded_completed_forward_seconds=prior['cost']['recorded_completed_forward_seconds'])
    return output


def render(result):
    n=a.number
    lines=['# 144：与107分歧规则等送审量的固定回顾', '',
        f"范围{result['scope']}，N={result['N']}。每个主模型先用main=S且107非S得到k，再让原生margin最低的k条送审。k不依据GT，未扫描其他阈值；原五点及原标签不改。", '',
        '|主模型/策略|k|自动N/覆盖|自动MCC|自动PA|拦截FS|残留FS/原非S|残留FS/自动非S|自动S FDR|送审正确S|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,value in result['variants'].items():
        for strategy in ('disagreement107','native_margin'):
            x=value[strategy];m=x['automatic']
            lines.append(f"|{name}/{strategy}|{value['k']}|{x['automatic_N']}/{n(x['automatic_coverage'],True)}|{n(m['mcc_display_value'] if m else None)}|{n(m['percent_agreement'] if m else None,True)}|{x['review']['intercepted_false_S']}|{x['remaining_automatic_false_S']}/{x['original_non_S']}|{x['remaining_automatic_false_S']}/{x['automatic_non_S']}|{n(x['automatic_predicted_S_FDR'],True)}|{x['review']['deferred_correct_S']}|")
    lines += ['', '自动处理N相同，但保留的ID可以不同，自动集MCC/PA不能当作同ID配对的全量原生提升。所有三类指标及分母在JSON中保留；没有假设人工复核后全部正确。', '',
              '## 部署与实际评分成本', '',
              '|主模型|107方案主调用+条件107生成|margin评分记录数|该模型汇总score forward秒数（含复用）|本段新completed/forward秒数|',
              '|---|---:|---:|---:|---:|']
    for name,value in result['variants'].items():
        cost=value['cost'];calls=cost['disagreement_deployment'];score=cost['margin_current_extraction']
        lines.append(f"|{name}|{calls['main_generations']}+{calls['conditional107_generations']}={calls['logical_generation_calls']}|{score['score_records']}|{score['score_forward_seconds_all_records']:.4f}|{score['new_completed_events']}/{score['new_completed_forward_seconds']:.4f}|")
    stage=result['recorded_stage_cost']
    lines += ['',f"本段评分worker墙钟并集{n(stage['worker_wall_seconds']['total'])}秒，controller {n(stage['controller_wall_seconds']['total'])}秒单列不相加；加载与墙钟不按模型强行平摊。", '',
              '当前margin来自额外同模型prefill/forward；107方案需要额外107生成。两者逻辑调用相同不表示实际时间相同。未来在原生生成中同步捕获logits可能免第二次prefill，但本项目未实现或实测，不能把它写成已经零额外成本。', '',
              '这是既有开发患者上的固定等工作量回顾，不是独立验证、CP保证或人工复核效果；不改变原无拒答基线及0/5/10/20/30%五点。', '',
              '[附加完整统计]('+result['scope']+'_equal_workload.json)']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--results',type=Path,nargs='+',required=True)
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=a.R/'outputs/144_native_confidence')
    args=parser.parse_args()
    before=args.analysis.read_bytes()
    result=compare(args.bundle,args.results,args.analysis)
    prefix=result['scope']+'_equal_workload'
    a.c.put(args.out/(prefix+'.json'),result)
    (args.out/(prefix+'.md')).write_bytes(render(result).encode('utf-8'))
    assert args.analysis.read_bytes()==before
    print(a.c.canonical({name:dict(k=v['k'],disagreement_FS=v['disagreement107']['review']['intercepted_false_S'],
        margin_FS=v['native_margin']['review']['intercepted_false_S'],disagreement_remaining=v['disagreement107']['remaining_automatic_false_S'],
        margin_remaining=v['native_margin']['remaining_automatic_false_S']) for name,v in result['variants'].items()}))


if __name__=='__main__':main()
