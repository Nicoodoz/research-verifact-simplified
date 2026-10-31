"""Reproduce the cache-only142 extension to the fixed143 review rule.

No GPU, network, threshold selection, original143 mutation, or default execution.
After readiness, supply the two actual142 SHA256 fingerprints and --execute.
Use --out for an independent reproduction; original143 artifacts are never changed.
"""
from collections import Counter
from pathlib import Path
import argparse
import importlib.util
import json

R = Path(__file__).resolve().parents[2]
HERE = R / 'outputs/143_selective_verification'
CODE143 = R / 'tasks/143_selective_verification/analyze143.py'
RESULT143 = R / 'outputs/143_selective_verification/results.json'
EXPECTED_CODE143_SHA = '0e73fb8364762c63473d0a6054566ebcadda065319ee28ef9f05033f49451ba8'
# Set from the published143 snapshot during preparation, never from142 outcomes.
EXPECTED_RESULT143_SHA = '1c9b148a61cc58e9875b11b2aa40693776d2c485c81abeb208f3779ed17aa77f'
NAME = 'relevance_order142'


def digest(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helper():
    if digest(CODE143) != EXPECTED_CODE143_SHA:
        raise ValueError('143 helper changed; inspect the new version before reuse')
    spec = importlib.util.spec_from_file_location('fixed143_helper', CODE143)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def supported_set_relations(keys, predictions):
    supported = {name: {i for i,label in values.items() if label=='Supported'}
                 for name,values in predictions.items()}
    anchor = supported['label_only107']
    anchor_errors = {i for i in anchor if keys[i]['GT']!='Supported'}
    comparisons = {}
    for name in ('full_pool120','claim_repeat136',NAME):
        current=supported[name]
        lost=anchor-current
        added=current-anchor
        retained=current&anchor
        retained_errors={i for i in retained if keys[i]['GT']!='Supported'}
        comparisons[name]=dict(native_supported_N=len(current),
            original107_S_lost_N=len(lost),original107_S_lost_ids=sorted(lost),
            original107_S_lost_by_GT=dict(Counter(keys[i]['GT'] for i in lost)),
            extra_S_beyond107_N=len(added),extra_S_beyond107_ids=sorted(added),
            automatic_supported_N=len(retained),automatic_supported_ids=sorted(retained),
            automatic_S_equals107_S=retained==anchor,
            original107_S_is_subset_of_native_S=anchor<=current,
            shared_false_S_N=len(retained_errors),shared_false_S_ids=sorted(retained_errors),
            original107_false_S_not_retained_ids=sorted(anchor_errors-retained_errors))
    return dict(anchor='label_only107',original107_supported_N=len(anchor),
                original107_false_S_N=len(anchor_errors),original107_supported_ids=sorted(anchor),
                original107_false_S_ids=sorted(anchor_errors),comparisons=comparisons,
                identity='Automatic S = native S intersect107 S; only native S outside107 S is sent for review.',
                limitation='A false Supported label shared by the main model and107 is not detected by this rule. Set containment is descriptive, not a risk guarantee.')


def prepare_result(helper, predictions_path, stats_path, predictions_sha, stats_sha):
    if digest(RESULT143) != EXPECTED_RESULT143_SHA:
        raise ValueError('Original143 results differ from the prepared snapshot')
    if digest(predictions_path) != predictions_sha or digest(stats_path) != stats_sha:
        raise ValueError('142 input fingerprint differs from the explicitly supplied completed result')
    keys, _, predictions143 = helper.load()
    previous = helper.c.read(RESULT143)
    stats = helper.c.read(stats_path)
    if (stats.get('task') != 142 or stats.get('arm') != 'relevance_order'
            or stats.get('scope') != 'full1817' or stats.get('expected_N') != 1817
            or stats.get('valid_N') != 1817 or stats.get('joint_valid_N') != 1817
            or stats.get('no_label_rewrite') is not True):
        raise ValueError('Require actual complete, valid, unmodified142 full1817 results')
    cov = stats.get('coverage', {})
    if (cov.get('candidate', {}).get('missing_ids') or cov.get('candidate', {}).get('invalid_ids')
            or cov.get('prompt_unverified_ids')):
        raise ValueError('142 has missing, invalid, or unverified inputs; no silent imputation')
    records = helper.c.rows(predictions_path)
    candidate = {row['id']: row for row in records}
    if len(records) != 1817 or len(candidate) != 1817 or set(candidate) != set(keys):
        raise ValueError('142 must contain exactly the same1817 unique IDs')
    labels = {}
    for i, row in candidate.items():
        if 'claim' in row or 'reference' in row:
            raise ValueError('Read sanitized142 outputs only')
        if row.get('primary_joint_valid') is not True or row.get('relevance_order') not in helper.LABELS:
            raise ValueError('Invalid142 prediction: ' + i)
        for field in ('sid', 'GT', 'claim_sha256', 'reference_sha256'):
            if field not in row or str(row[field]) != str(keys[i][field]):
                raise ValueError('142 identity or source mismatch: ' + i)
        if row.get('claim_repeat136') != predictions143['claim_repeat136'][i]:
            raise ValueError('142 and143 use different original136 labels: ' + i)
        labels[i] = row['relevance_order']
    # Same fixed rule as143; GT is not read here to construct the flag.
    flags = {i for i in keys if labels[i] == 'Supported'
             and predictions143['label_only107'][i] != 'Supported'}
    rows = [keys[i] for i in sorted(keys)]
    groups = dict(natural400=[r for r in rows if r['old_panel'] == 'natural'],
                  pressure100=[r for r in rows if r['old_panel'] == 'pressure'],
                  new1317=[r for r in rows if r['subset'] == 'new'],
                  history103_180=[r for r in rows if r['history103_panel'] in ('natural', 'pressure')])
    if [len(group) for group in groups.values()] != [400, 100, 1317, 180]:
        raise ValueError('Frozen panel sizes changed')
    summary = helper.summarize(rows, labels, flags)
    summary['panels'] = {name: helper.summarize(group, labels, flags) for name, group in groups.items()}
    summary['authors'] = {name: helper.summarize([r for r in rows if r['author'] == name], labels, flags)
                          for name in sorted({r['author'] for r in rows})}
    summary['patients'] = {str(sid): helper.summarize([r for r in rows if r['sid'] == sid], labels, flags)
                           for sid in sorted({r['sid'] for r in rows})}
    actual = summary['native']
    expected = stats['standalone_candidate']
    for field in ('correct', 'false_S', 'non_S', 'confusion_matrix'):
        if actual[field] != expected[field]:
            raise ValueError('143 helper does not reproduce actual142 native metric: ' + field)
    for field in ('mcc', 'percent_agreement'):
        if abs(actual[field] - expected[field]) > 1e-12:
            raise ValueError('142 native metric mismatch: ' + field)
    # Copy original120/136 metric objects without recomputation or alteration.
    result = dict(previous)
    result['native_scores'] = dict(previous['native_scores'], **{NAME: actual})
    result['rules'] = dict(previous['rules'], **{NAME: summary})
    result['reason'] = dict(previous['reason'])
    result['reason']['nonempty_in_sources'] = dict(previous['reason']['nonempty_in_sources'],
        **{NAME: sum(isinstance(r.get('reason'), str) and bool(r['reason'].strip()) for r in records)})
    result['supported_set_relations']=supported_set_relations(keys,dict(predictions143,**{NAME:labels}))
    for name,relation in result['supported_set_relations']['comparisons'].items():
        if (relation['automatic_supported_N']!=result['rules'][name]['automatic_predicted_S']
                or relation['shared_false_S_N']!=result['rules'][name]['remaining_automatic_false_S']):
            raise ValueError('Set relation disagrees with unchanged selective metrics: '+name)
    result['addendum'] = dict(source_task=142, status='executed_after_explicit_full1817_readiness',
        rule_unchanged=True, original143_results_sha256=EXPECTED_RESULT143_SHA,
        helper143_sha256=EXPECTED_CODE143_SHA,
        predictions142=dict(path=str(predictions_path),sha256=predictions_sha),
        stats142=dict(path=str(stats_path),sha256=stats_sha),
        original120_136_metric_objects_unchanged=True,
        full_population_labels_changed=0, no_new_inference=True,
        note='Fixed retrospective addendum; no CP guarantee and no imputed human decisions.')
    decisions = [dict(id=i, sid=keys[i]['sid'], GT=keys[i]['GT'], author=keys[i]['author'],
        old_panel=keys[i]['old_panel'], subset=keys[i]['subset'], history103_panel=keys[i]['history103_panel'],
        relevance_order142=labels[i], label_only107=predictions143['label_only107'][i],
        needs_review_relevance_order142=i in flags, original_reason_preserved_at_source=True)
        for i in sorted(keys)]
    return result, decisions


def render(helper, result):
    part = result['rules'][NAME]
    n = helper.number
    lines = ['# 143固定送审规则：142完整结果补充', '',
             '沿用同一1817条/20患者及main=S且107≠S送审规则。只补入142结果，不重新挑规则或阈值，'
             '不改变原120/136结果或任何原始标签。自动子集成绩不等于全量原生提升。', '',
             '## 原生全量结果', ''] + helper.metric_table(result['native_scores'].items())
    lines += ['', '## 同一固定规则下的自动集', ''] + helper.metric_table(
        (name+'/自动集', value['automatic']) for name,value in result['rules'].items())
    lines += ['', '|主模型|自动N/覆盖|送审N|拦截FS|送审正确S|残留FS/原非S|残留FS/自动非S|自动S假发现率|',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,value in result['rules'].items():
        lines.append(f"|{name}|{value['automatic_N']}/{n(value['automatic_coverage'],True)}|{value['review']['N']}|{value['review']['intercepted_false_S']}|{value['review']['deferred_correct_S']}|{value['remaining_automatic_false_S']}/{value['original_non_S']} ({n(value['automatic_false_S_over_original_non_S'],True)})|{value['remaining_automatic_false_S']}/{value['automatic_non_S']} ({n(value['automatic_false_S_over_automatic_non_S'],True)})|{n(value['automatic_predicted_S_FDR'],True)}|")
    relation=result['supported_set_relations']
    lines += ['', '## 共有Supported集合解释', '',
              f"107原判S共{relation['original107_supported_N']}条，其中错误S共{relation['original107_false_S_N']}条。"
              '固定规则下，自动判S集合恒等于主模型S与107 S的交集。', '',
              '|主模型|原生S数|107的S在主模型中丢失|主模型额外S（送审）|自动保留S|是否恰等于107 S|共有错误S（无法拦截）|',
              '|---|---:|---:|---:|---:|---|---:|']
    for name,check in relation['comparisons'].items():
        lines.append(f"|{name}|{check['native_supported_N']}|{check['original107_S_lost_N']}|{check['extra_S_beyond107_N']}|{check['automatic_supported_N']}|{'是' if check['automatic_S_equals107_S'] else '否'}|{check['shared_false_S_N']}|")
    lines += ['', '120、136是否完整包含107的S集合由上表实算；若包含，过滤后只是回到107的S集合，'
              '共有的错误S不会触发送审。这解释了相同残留错误数，不构成新的风险保证。142若破坏包含关系，'
              '按实际丢失ID及其GT列入JSON，不把不同残留数解释为自动发现所有共有错误。', '',
              '后续原生分数分析仍以136为重点；142点完整保留，不把这次固定分歧过滤包装为原生判定提升。']
    lost=relation['comparisons'][NAME]['original107_S_lost_by_GT']
    lines += ['', '142未保留的107原S按GT分为S/NS/NA：'
              +'/'.join(str(lost.get(g,0)) for g in helper.LABELS)
              +'；这部分已由142原生标签变化移出S集合，不是送审规则额外识别的错误。']
    lines += ['', '## 142随机送审参照与调用量', '']
    random = part['random_review'];lo,hi=random['central95_reference_interval'];calls=part['logical_inference_calls']
    lines += [f"同预测S池M={random['population_predicted_S']}、原FS K={random['population_false_S']}、送审n={random['same_review_count']}；"
              f"实际拦截{random['observed_intercepted_false_S']}，精确超几何期望{random['expected_intercepted_false_S']:.2f}，中央95%随机参考区间[{lo}, {hi}]。"
              '该区间不是临床安全CI或CP保证。', '',
              f"部署逻辑调用{calls['main']}+条件107调用{calls['conditional107']}={calls['total']}，平均{calls['mean_per_claim']:.3f}次/命题。"
              '本次缓存补充新增GPU/API为0；部署不免费，不将调用数冒充实测时间。', '',
              '142送审GT S/NS/NA：'+'/'.join(str(part['review']['GT'][g]) for g in helper.LABELS)+'。', '',
              '## 142分组', '', '原180与其余面板重叠，不相加；完整分母与三类指标保存在JSON。']
    for family,title in (('panels','面板'),('authors','作者'),('patients','患者')):
        lines += ['', title, '', '|分组|N|自动覆盖|送审|原FS→自动FS|拦截FS|送审正确S|自动MCC|自动PA|',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name,value in part[family].items():
            metric=value['automatic']
            lines.append(f"|{name}|{value['N']}|{n(value['automatic_coverage'],True)}|{value['review']['N']}|{value['native']['false_S']}→{value['remaining_automatic_false_S']}|{value['review']['intercepted_false_S']}|{value['review']['deferred_correct_S']}|{n(metric['mcc_display_value'] if metric else None)}|{n(metric['percent_agreement'] if metric else None,True)}|")
    lines += ['', '## 142三类与混淆矩阵']
    lines += helper.metric_details(NAME+'/原生',part['native'])
    lines += helper.metric_details(NAME+'/自动集',part['automatic'])
    lines += ['', '## 限制', '',
              '原reason仅按实际来源保留，缺失不生成、不借别的模型填补。送审并不表示人工已判对，未计算假设的人机最终成绩。'
              '指标未定义与MCC零分母沿143显示NA；Gwet AC1、Macro-F1等完整值在JSON。', '',
              '这是历史开发患者上的固定回顾baseline，不是独立验证或方法创新。'
              '不建立CP/选择性风险保证，不自动启用确认40人。所有原120/136指标对象逐项保留，原143文件不覆盖。', '',
              '[补充统计](results142.json) · [142原标签与送审标记](decisions142_sanitized.jsonl)']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Use only after root explicitly confirms142 full1817 readiness')
    parser.add_argument('--predictions',type=Path,default=R/'outputs/142_relevance_order/relevance_order_full1817_predictions_sanitized.jsonl')
    parser.add_argument('--stats142',type=Path,default=R/'outputs/142_relevance_order/relevance_order_full1817.json')
    parser.add_argument('--expected-predictions-sha256')
    parser.add_argument('--expected-stats142-sha256')
    parser.add_argument('--out',type=Path,default=HERE,help='Write a separate reproduction directory')
    args=parser.parse_args()
    if not args.execute:
        print('PREPARED_ONLY: no142 files read, no scoring, no outputs; wait for root full1817 readiness.')
        return
    if not args.expected_predictions_sha256 or not args.expected_stats142_sha256:
        parser.error('Execution requires fingerprints of both actual completed142 source files')
    helper=load_helper()
    before={CODE143:digest(CODE143),RESULT143:digest(RESULT143)}
    result,decisions=prepare_result(helper,args.predictions,args.stats142,args.expected_predictions_sha256,args.expected_stats142_sha256)
    if any((args.out/name).exists() for name in ('results142.json','report142.md','decisions142_sanitized.jsonl')):
        raise FileExistsError('Preserve existing addendum outputs; do not silently overwrite')
    helper.c.put(args.out/'results142.json',result)
    helper.c.putl(args.out/'decisions142_sanitized.jsonl',decisions)
    (args.out/'report142.md').write_bytes(render(helper,result).encode('utf-8'))
    if any(digest(path)!=value for path,value in before.items()):
        raise ValueError('Original143 file changed during addendum')
    value=result['rules'][NAME]
    print(helper.c.canonical(dict(status='ADDENDUM_COMPLETE',N=value['N'],automatic_N=value['automatic_N'],
        review_N=value['review']['N'],intercepted_false_S=value['review']['intercepted_false_S'],
        remaining_false_S=value['remaining_automatic_false_S'],original143_unchanged=True)))


if __name__=='__main__':
    main()
