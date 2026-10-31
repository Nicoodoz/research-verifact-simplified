"""Fixed cache-only review flags; native predictions and labels never change."""
from collections import Counter
from pathlib import Path
import json
import sys

from scipy.stats import hypergeom

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/120_full_pool_sft'))
from final_compare120 import metrics, LABELS
sys.path.insert(0, str(R / 'tasks/105_brief_supervision'))
import common105 as c

T = Path(__file__).resolve().parent
O = R / 'outputs/143_selective_verification'
FILES = {
    'keys': R / '.local_models/134_author_baselines/keys.jsonl',
    'full_pool120': R / 'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl',
    'claim_repeat136': R / 'outputs/136_claim_repeat_transfer/full1817_predictions_sanitized.jsonl',
    'label_only107': R / '.local_models/116_research_cycle/baseline107_selection1817.jsonl',
}
EXPECTED_SHA = {
    'keys': '8993f29bcaca11b57f1d06f200cce6cee462dbcc58371bb3cafeed844305b37a',
    'full_pool120': '04241eb8c7340476622dee94fd41692099f81fc423524be7dd3763573afd531e',
    'claim_repeat136': 'd548bd33cc0854413ada380f9401978e2dc42083592bcaa115afb9d489c8c124',
    'label_only107': '167c71694d5a5ee96fc222c58d978bc032351ade9935ec0476cd520092eb328b',
}


def ratio(a, b):
    return a / b if b else None


def load():
    data = {}
    for name, path in FILES.items():
        if c.sha(path) != EXPECTED_SHA[name]:
            raise ValueError('Frozen source SHA changed: ' + name)
        values = c.rows(path)
        data[name] = {row['id']: row for row in values}
        if len(values) != len(data[name]):
            raise ValueError('Duplicate IDs: ' + name)
    keys = data['keys']
    assert len(keys) == 1817 and len({row['sid'] for row in keys.values()}) == 20
    assert Counter(row['GT'] for row in keys.values()) == Counter(dict(zip(LABELS, (1455, 121, 241))))
    for name, records in data.items():
        if set(records) != set(keys):
            raise ValueError('Expected exactly the frozen1817 IDs: ' + name)
        for i, row in records.items():
            if 'claim' in row or 'reference' in row:
                raise ValueError('Only sanitized input files are allowed')
            for field in ('sid', 'GT', 'claim_sha256', 'reference_sha256'):
                if field in row and str(row[field]) != str(keys[i][field]):
                    raise ValueError('Identity/source mismatch: ' + name + '/' + i)
    predictions = {
        'full_pool120': {i: row['verdict'] for i, row in data['full_pool120'].items()},
        'claim_repeat136': {i: row['claim_repeat'] for i, row in data['claim_repeat136'].items()},
        'label_only107': {i: row['verdict'] for i, row in data['label_only107'].items()},
    }
    for name in predictions:
        for i, label in predictions[name].items():
            source = data[name][i]
            if label not in LABELS or source.get('valid', True) is not True or source.get('receipt_status') in ('invalid', 'missing'):
                raise ValueError('Invalid/missing source requires explicit handling, never imputation: ' + name + '/' + i)
    return keys, data, predictions


def score(rows, prediction):
    if not rows:
        return None
    result = metrics(rows, prediction)
    # Preserve the evaluator's zero convention and expose undefined denominator.
    result['mcc_display_value'] = None if result['mcc_denominator_zero'] else result['mcc']
    return result


def random_reference(population, false_supports, reviewed, observed):
    """Exact finite-population reference, not a confidence or safety interval."""
    if not population:
        expected, interval = 0., [0, 0]
    else:
        distribution = hypergeom(population, false_supports, reviewed)
        expected = reviewed * false_supports / population
        interval = [int(distribution.ppf(.025)), int(distribution.ppf(.975))]
    return dict(population_predicted_S=population, population_false_S=false_supports,
                same_review_count=reviewed, expected_intercepted_false_S=expected,
                central95_reference_interval=interval, observed_intercepted_false_S=observed,
                observed_minus_random_expectation=observed-expected,
                interpretation='Exact hypergeometric random-review reference distribution; not a safety CI or CP guarantee.')


def summarize(rows, main, review_ids):
    automatic = [row for row in rows if row['id'] not in review_ids]
    reviewed = [row for row in rows if row['id'] in review_ids]
    n = len(rows)
    non_s = sum(row['GT'] != 'Supported' for row in rows)
    raw = score(rows, main)
    auto = score(automatic, main)
    fs = sum(row['GT'] != 'Supported' and main[row['id']] == 'Supported' for row in automatic)
    auto_non_s = sum(row['GT'] != 'Supported' for row in automatic)
    auto_s = sum(main[row['id']] == 'Supported' for row in automatic)
    intercepted = sum(row['GT'] != 'Supported' for row in reviewed)
    correct_s = sum(row['GT'] == 'Supported' for row in reviewed)
    main_s = sum(main[row['id']] == 'Supported' for row in rows)
    original_fs = sum(row['GT'] != 'Supported' and main[row['id']] == 'Supported' for row in rows)
    assert len(reviewed) == intercepted + correct_s
    assert fs + intercepted == original_fs
    return dict(N=n, native=raw, automatic_N=len(automatic), automatic_coverage=ratio(len(automatic), n),
                automatic=auto, automatic_non_S=auto_non_s, automatic_predicted_S=auto_s,
                original_non_S=non_s, remaining_automatic_false_S=fs,
                automatic_false_S_over_original_non_S=ratio(fs, non_s),
                automatic_false_S_over_automatic_non_S=ratio(fs, auto_non_s),
                automatic_predicted_S_FDR=ratio(fs, auto_s),
                automatic_coverage_by_GT={g: ratio(sum(row['GT']==g for row in automatic), sum(row['GT']==g for row in rows)) for g in LABELS},
                review=dict(N=len(reviewed), rate=ratio(len(reviewed), n),
                            patients=len({row['sid'] for row in reviewed}),
                            GT={g: sum(row['GT']==g for row in reviewed) for g in LABELS},
                            intercepted_false_S=intercepted, deferred_correct_S=correct_s,
                            false_S_interception_fraction=ratio(intercepted, original_fs)),
                random_review=random_reference(main_s, original_fs, len(reviewed), intercepted),
                logical_inference_calls=dict(main=n, conditional107=main_s, total=n+main_s,
                                             mean_per_claim=ratio(n+main_s, n)))


def analyze(keys, data, predictions):
    rows = [keys[i] for i in sorted(keys)]
    groups = {'natural400': [r for r in rows if r['old_panel']=='natural'],
              'pressure100': [r for r in rows if r['old_panel']=='pressure'],
              'new1317': [r for r in rows if r['subset']=='new'],
              'history103_180': [r for r in rows if r['history103_panel'] in ('natural', 'pressure')]}
    assert [len(groups[g]) for g in groups] == [400, 100, 1317, 180]
    result = dict(task=143, method='support_disagreement', analysis_kind='retrospective fixed cache baseline',
                  N=1817, patients=20, original_non_S=362, rule='main == Supported and107 != Supported',
                  native_scores={name: score(rows, labels) for name, labels in predictions.items()},
                  sources={name: dict(path=str(path.relative_to(R)).replace('\\', '/'),sha256=EXPECTED_SHA[name]) for name,path in FILES.items()},
                  protocol_sha256=c.sha(T/'PROTOCOL.md'), coverage=dict(missing=0,invalid=0,fallback=0),
                  reason=dict(policy='Original reason retained at source if present; no generation, borrowing, or replacement.',
                              nonempty_in_sources={name: sum(isinstance(r.get('reason'),str) and bool(r['reason'].strip()) for r in data[name].values()) for name in predictions}),
                  full_population_labels_changed=0, clinician_review_performed=False,
                  CP_or_formal_risk_guarantee=False, new_GPU_calls=0, new_API_calls=0,
                  rules={})
    decisions = [dict(id=i, sid=keys[i]['sid'], GT=keys[i]['GT'], author=keys[i]['author'],
                      old_panel=keys[i]['old_panel'], subset=keys[i]['subset'],
                      history103_panel=keys[i]['history103_panel'], label_only107=predictions['label_only107'][i]) for i in sorted(keys)]
    for name in ('full_pool120', 'claim_repeat136'):
        main = predictions[name]
        # This fixed flag uses predictions only. GT enters solely in evaluation.
        flags = {i for i in keys if main[i] == 'Supported' and predictions['label_only107'][i] != 'Supported'}
        result['rules'][name] = summarize(rows, main, flags)
        result['rules'][name]['panels'] = {g: summarize(group,main,flags) for g,group in groups.items()}
        result['rules'][name]['authors'] = {a: summarize([r for r in rows if r['author']==a],main,flags) for a in sorted({r['author'] for r in rows})}
        result['rules'][name]['patients'] = {str(sid): summarize([r for r in rows if r['sid']==sid],main,flags) for sid in sorted({r['sid'] for r in rows})}
        for row in decisions:
            row[name] = main[row['id']]
            row['needs_review_' + name] = row['id'] in flags
    return result, decisions


def number(value, percent=False):
    return 'NA' if value is None else (f'{value:.2%}' if percent else f'{value:.4f}')


def metric_table(entries):
    lines = ['|配置/范围|N|MCC|PA|正确|false-S/非S|Macro-F1|', '|---|---:|---:|---:|---:|---:|---:|']
    for name, metric in entries:
        if metric is None:
            lines.append(f'|{name}|0|NA|NA|NA|0/0|NA|')
        else:
            lines.append(f"|{name}|{metric['n']}|{number(metric['mcc_display_value'])}|{number(metric['percent_agreement'],True)}|{metric['correct']}|{metric['false_S']}/{metric['non_S']}|{number(metric['macro_F1'])}|")
    return lines


def metric_details(name, metric):
    if metric is None:
        return ['', name + '无自动处理样本，指标未定义。']
    lines = ['', name, '', '|GT|Precision|Recall|F1|', '|---|---:|---:|---:|']
    for label in LABELS:
        row=metric['per_class'][label]
        lines.append('|'+label+'|'+'|'.join(number(row[k]) for k in ('precision','recall','f1'))+'|')
    lines += ['', '混淆矩阵（行GT、列预测，S/NS/NA）', '', '|GT\\预测|S|NS|NA|', '|---|---:|---:|---:|']
    lines += ['|'+label+'|'+'|'.join(map(str,row))+'|' for label,row in zip(('S','NS','NA'),metric['confusion_matrix'])]
    return lines


def render(result):
    lines = ['# 143：固定分歧送审的缓存回顾', '',
             '固定1817条/20名历史评价患者；两条预先固定规则均报告。原S/NS/NA完全不改，因此全量原生MCC没有提升。送审后的人工结论尚不存在，不计算假设的人机最终成绩。', '',
             '## 全量原生结果', ''] + metric_table(result['native_scores'].items())
    lines += ['', '## 自动处理与送审', ''] + metric_table((name+'/自动集',v['automatic']) for name,v in result['rules'].items())
    lines += ['', '|主模型|自动N/覆盖|送审N|拦截原FS|送审的原正确S|残留自动FS/全部非S|残留FS/自动非S|自动S假发现率|',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,v in result['rules'].items():
        lines.append(f"|{name}|{v['automatic_N']}/{number(v['automatic_coverage'],True)}|{v['review']['N']}|{v['review']['intercepted_false_S']}|{v['review']['deferred_correct_S']}|{v['remaining_automatic_false_S']}/{v['original_non_S']} ({number(v['automatic_false_S_over_original_non_S'],True)})|{v['remaining_automatic_false_S']}/{v['automatic_non_S']} ({number(v['automatic_false_S_over_automatic_non_S'],True)})|{number(v['automatic_predicted_S_FDR'],True)}|")
    lines += ['', '原non-S固定362；自动集non-S随送审而变化，两个分母不能混用。自动集MCC仅针对被保留的子集，不能与全1817的MCC差值称作原生提升。', '',
              '|主模型|送审GT S/NS/NA|送审涉及患者|主调用+条件107调用|平均逻辑调用/命题|', '|---|---|---:|---:|---:|']
    for name,v in result['rules'].items():
        calls=v['logical_inference_calls'];gt=v['review']['GT']
        lines.append(f"|{name}|{'/'.join(str(gt[g]) for g in LABELS)}|{v['review']['patients']}|{calls['main']}+{calls['conditional107']}={calls['total']}|{calls['mean_per_claim']:.3f}|")
    lines += ['', '本次复用缓存，新增GPU/API调用0。部署时先跑主模型，只有主判S才追加107；上述为逻辑调用量，不是实测时延，部署绝非免费。缓存中原reason若有仍留在原来源；本次不生成、不借用其他模型reason。实际非空reason数量：'+str(result['reason']['nonempty_in_sources'])+'。', '',
              '## 同数量随机送审参照', '', '|主模型|预测S池M|其中FS K|送审n|实际拦截FS|随机精确期望|中央95%随机参考区间|', '|---|---:|---:|---:|---:|---:|---|']
    for name,v in result['rules'].items():
        x=v['random_review'];lo,hi=x['central95_reference_interval']
        lines.append(f"|{name}|{x['population_predicted_S']}|{x['population_false_S']}|{x['same_review_count']}|{x['observed_intercepted_false_S']}|{x['expected_intercepted_false_S']:.2f}|[{lo}, {hi}]|")
    lines += ['', '`X~Hypergeom(M,K,n)`，只在同一个主模型原预测S池中不放回抽同样n条。此区间是固定队列随机规则下拦截数的分布，不是安全置信区间、泛化区间或CP保证；并未额外随机试验或按结果挑种子。', '',
              '## 面板、作者与患者', '', '原180与其余面板有重叠，不相加。分组完整三类指标与随机参照保留在results.json。']
    for family in ('panels','authors','patients'):
        lines += ['', {'panels':'面板','authors':'作者','patients':'患者'}[family], '',
                  '|主模型/分组|N|自动覆盖|送审|原FS→自动FS|拦截FS|送审正确S|自动MCC|自动PA|', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name,rule in result['rules'].items():
            for group,v in rule[family].items():
                metric=v['automatic'];mcc=metric['mcc_display_value'] if metric else None;pa=metric['percent_agreement'] if metric else None
                lines.append(f"|{name}/{group}|{v['N']}|{number(v['automatic_coverage'],True)}|{v['review']['N']}|{v['native']['false_S']}→{v['remaining_automatic_false_S']}|{v['review']['intercepted_false_S']}|{v['review']['deferred_correct_S']}|{number(mcc)}|{number(pa,True)}|")
    lines += ['', '## 三类表现与混淆矩阵']
    for name,m in result['native_scores'].items():lines += metric_details(name+'/全量',m)
    for name,v in result['rules'].items():lines += metric_details(name+'/自动集',v['automatic'])
    lines += ['', '## 边界与核验', '',
              '原生结果、自动集结果、送审负担均完整保留，不选较好的一条隐藏另一条。不将送审假设判对，不改医生GT，不把任何reason转接到别的标签。缺失0、invalid0、fallback0；四份来源SHA和逐ID送审标记可复核。', '',
              'MCC若分母为0，JSON保留项目评价器的0约定和标志，表中显示NA；其他零分母也显示NA。Macro-F1沿用项目三类固定均值；Gwet AC1和所有逐类分母见JSON。', '',
              '本规则根据旧开发认识提出，是回顾baseline，不是独立验证或方法创新。32人为120新增训练范围，8内部患者曾参与选择且起点有43条监督；20评价患者已反复使用，100人全有历史暴露，不自动使用确认40人。未使用校准标签选择阈值，本方法也没有概率校准、CP覆盖或选择性安全保证。', '',
              '没有患者泛化保证或人工复核效果实验。若希望未来声称风险控制，需要另行冻结目标风险分母并建立有效校准/评价分离；不能由本次过滤出的好看子集倒推保证。', '',
              '[结果与来源指纹](results.json) · [逐ID原标签及送审标记](decisions_sanitized.jsonl) · [固定回顾协议](../../tasks/143_selective_verification/PROTOCOL.md)']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    keys,data,predictions=load()
    result,decisions=analyze(keys,data,predictions)
    c.put(O/'results.json',result)
    c.putl(O/'decisions_sanitized.jsonl',decisions)
    (O/'report.md').write_bytes(render(result).encode('utf-8'))
    if any(c.sha(path)!=EXPECTED_SHA[name] for name,path in FILES.items()):
        raise ValueError('Source changed during analysis')
    print(c.canonical({name: dict(automatic_N=v['automatic_N'],coverage=v['automatic_coverage'],review_N=v['review']['N'],intercepted_FS=v['review']['intercepted_false_S'],remaining_FS=v['remaining_automatic_false_S'],correct_S_reviewed=v['review']['deferred_correct_S']) for name,v in result['rules'].items()}))


if __name__ == '__main__':
    main()
