"""Fixed six-way cosine-kNN screening on cached107 verdict-prefix states.

No LLM/GPU/API, token decoding, clinical-content output, probability calibration,
or patient feature. Internal730 alone select one configuration before screen160.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/121_nearest_memory'
PUBLIC = ROOT/'outputs/121_nearest_memory'
SOURCE = ROOT/'.local_models/117_verdict_probe'
sys.path.insert(0, str(ROOT/'tasks/117_verdict_probe'))
from fit_probe117 import LABELS, metrics, write_json
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common

SOURCE_SHA = '096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'
PREFIX = [4754, 415, 8217, 3147]
CONFIGS = [(k, mode) for k in (5, 15, 31) for mode in ('uniform', 'inverse_training_class_frequency')]


def normalized(matrix):
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError('Invalid frozen feature matrix')
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms <= 0) or not np.isfinite(norms).all():
        raise ValueError('Zero or invalid feature vector')
    return matrix/norms


def features(ids):
    wanted = set(ids)
    if len(ids) != len(wanted):
        raise ValueError('Repeated requested feature ID')
    found = {}
    width = None
    for name in ('features_initial', 'features_pool_missing', 'features500_missing', 'features1817_missing'):
        folder = SOURCE/'evidence'/name
        complete = common.read(folder/'complete.json')
        if complete.get('adapter_sha256') != SOURCE_SHA or complete.get('prefix_token_ids') != PREFIX:
            raise ValueError('Feature cache is not frozen107 original verdict-prefix: '+name)
        for path in sorted((folder/'batches').glob('*.npz')):
            with np.load(path, allow_pickle=False) as data:
                names = data['ids'].astype(str).tolist()
                selected = [(n, i) for n, i in enumerate(names) if i in wanted]
                if not selected:
                    continue
                receipt = common.read(path.with_suffix('.json'))
                if (receipt.get('ids') != names or receipt.get('adapter_sha256') != SOURCE_SHA
                        or receipt.get('prefix_token_ids') != PREFIX):
                    raise ValueError('Feature/receipt association mismatch: '+str(path))
                value = np.asarray(data['verdict_prefix'], dtype=np.float32)
                if value.ndim != 2 or value.shape[0] != len(names) or not np.isfinite(value).all():
                    raise ValueError('Invalid cached prefix states')
                width = value.shape[1] if width is None else width
                if value.shape[1] != width:
                    raise ValueError('Feature width changed')
                for n, i in selected:
                    if i in found:
                        raise ValueError('Duplicate cached feature ID: '+i)
                    found[i] = value[n].copy()
    if wanted != set(found):
        raise ValueError('Missing cached states: '+str(len(wanted-set(found))))
    return normalized(np.stack([found[i] for i in ids]))


def neighbors(query, train):
    similarity = query@train.T
    # Stable ordering uses only the already-frozen119 training order for ties.
    order = np.argsort(-similarity, axis=1, kind='stable')[:, :31]
    return order, np.take_along_axis(similarity, order, axis=1)


def votes(indices, train_y, counts, k, mode):
    neighbor_y = train_y[indices[:, :k]]
    weights = np.ones(3, dtype=np.float64) if mode == 'uniform' else 1/counts.astype(np.float64)
    if mode not in ('uniform', 'inverse_training_class_frequency'):
        raise ValueError('Unknown fixed voting mode')
    scores = np.stack([(neighbor_y == n).sum(axis=1)*weights[n] for n in range(3)], axis=1)
    # Fixed class-index tie break; scores are votes, not calibrated probabilities.
    return scores.argmax(axis=1), scores


def choice_key(config):
    value = config['validation_metrics']
    return value['mcc'], -value['false_S'], -config['k'], config['voting'] == 'uniform'


def gate(panels, size):
    n, p = panels['natural'], panels['pressure']
    net = lambda value, label: value['changes']['by_class'][label]['rescued']-value['changes']['by_class'][label]['harmed']
    correct = n['delta_correct']+p['delta_correct']
    fs = n['delta_false_S']+p['delta_false_S']
    if size == 160:
        guards = dict(natural_correct=n['delta_correct'] >= -2, pressure_correct=p['delta_correct'] >= -2,
                      natural_S=net(n, LABELS[0]) >= -3,
                      natural_NS=net(n, LABELS[1]) >= -2, natural_NA=net(n, LABELS[2]) >= -2,
                      pressure_NS=net(p, LABELS[1]) >= -4, pressure_NA=net(p, LABELS[2]) >= -4)
        quality = n['delta_MCC'] >= .015 and correct >= 4 and fs <= 1
        risk = fs <= -2 and correct >= -2 and n['delta_MCC'] >= -.01
    elif size == 500:
        guards = dict(natural_S=net(n, LABELS[0]) >= -5, natural_NA=net(n, LABELS[2]) >= -5,
                      pressure_NA=net(p, LABELS[2]) >= -5)
        quality = n['delta_MCC'] >= .01 and correct >= 5 and fs <= 1
        risk = fs <= -3 and correct >= -3 and n['delta_MCC'] >= -.01
    else:
        raise ValueError('Only prespecified160/500 gates exist')
    for panel, value in panels.items():
        for label, value in value['scores']['candidate']['per_class'].items():
            if value['recall'] is not None:
                guards[panel+' '+label+' recall_positive'] = value['recall'] > 0
    return dict(guards=guards, quality_signal=quality, risk_signal=risk,
                continue_=all(guards.values()) and (quality or risk))


def cohort():
    fixed = SOURCE/'lpft_full32_bundle/data/lpft_full32'
    train = [{key: row[key] for key in ('id', 'sid', 'GT')} for row in common.rows(fixed/'train.jsonl')]
    validation = [{key: row[key] for key in ('id', 'sid', 'GT')} for row in common.rows(fixed/'validation.jsonl')]
    keys = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    screen = common.read(SOURCE/'data_selection.json')['screen_ids']
    sets = [set(str(r['sid']) for r in rows) for rows in (train, validation, keys)]
    ids = [set(r['id'] for r in rows) for rows in (train, validation, keys)]
    if (len(train), len(validation), len(keys), len(screen)) != (2945, 730, 1817, 160):
        raise ValueError('Fixed32/8/20 cohort dimensions changed')
    if tuple(map(len, sets)) != (32, 8, 20) or any(sets[i] & sets[j] or ids[i] & ids[j]
                                               for i in range(3) for j in range(i+1, 3)):
        raise ValueError('Patient or ID isolation failed')
    if any(len(rows) != len(group) for rows, group in zip((train, validation, keys), ids)):
        raise ValueError('Duplicate original IDs')
    if any(row['GT'] not in LABELS for rows in (train, validation, keys) for row in rows):
        raise ValueError('Original label schema changed')
    if not set(screen) <= {r['id'] for r in keys if r.get('old_panel') in ('natural', 'pressure')}:
        raise ValueError('160 is not nested in the fixed500')
    return train, validation, {r['id']: r for r in keys}, screen


def run():
    started = time.perf_counter()
    protocol = common.read(PRIVATE/'protocol.json')
    if protocol['k'] != [5, 15, 31] or protocol['status'] != 'frozen_before_new_predictions':
        raise ValueError('Prespecified protocol is absent or changed')
    if (PRIVATE/'selection.json').exists():
        raise FileExistsError('Preserve completed121 selection; do not refit or rescreen')
    train, validation, keys, screen = cohort()
    train_ids = [r['id'] for r in train]
    combined = features(train_ids+[r['id'] for r in validation])
    train_x, validation_x = combined[:len(train)], combined[len(train):]
    train_y = np.asarray([LABELS.index(r['GT']) for r in train], dtype=np.int64)
    counts = np.bincount(train_y, minlength=3)
    assert counts.min() > 0 and tuple(LABELS) == ('Supported', 'Not Supported', 'Not Addressed')
    nearest, distance = neighbors(validation_x, train_x)
    configurations = []
    for k, mode in CONFIGS:
        predictions, _ = votes(nearest, train_y, counts, k, mode)
        value = metrics(validation, [LABELS[int(i)] for i in predictions])
        configurations.append(dict(k=k, voting=mode, validation_metrics=value))
    chosen = max(configurations, key=choice_key)
    selection = dict(task=121, name='nearest_memory', feature='frozen107_verdict_prefix',
        feature_width=train_x.shape[1], training_N=len(train), validation_N=len(validation),
        training_patients=32, validation_patients=8, training_GT=dict(Counter(r['GT'] for r in train)),
        source_adapter_sha256=SOURCE_SHA, configurations=configurations, chosen=chosen,
        selection_uses_screen=False, confirmation40_used=False, protocol=protocol,
        ancestry_note='107 ancestor saw196 from original40, including some internal-validation patients',
        new_GPU_CNY=0, new_API_CNY=0)
    write_json(PRIVATE/'selection.json', selection)  # Before any screen prediction.
    np.savez(PRIVATE/'memory.npz', train_x=train_x, train_y=train_y, ids=np.asarray(train_ids),
             labels=np.asarray(LABELS), class_counts=counts)
    baseline_rows = common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    baseline = {r['id']: r for r in baseline_rows}
    if set(baseline) != set(keys) or any(r.get('valid') is not True for r in baseline_rows):
        raise ValueError('Complete valid original107 baseline required')
    stages = {}
    all_predictions = {}
    def evaluate_ids(ids, stage):
        absent = [i for i in ids if i not in all_predictions]
        if absent:
            q = features(absent)
            near, similarity = neighbors(q, train_x)
            predictions, scores = votes(near, train_y, counts, chosen['k'], chosen['voting'])
            private_neighbors = []
            for j, identifier in enumerate(absent):
                all_predictions[identifier] = dict(id=identifier, verdict=LABELS[int(predictions[j])], valid=True)
                private_neighbors.append(dict(id=identifier,
                    neighbor_ids=[train_ids[int(n)] for n in near[j, :chosen['k']]],
                    cosine=similarity[j, :chosen['k']].tolist(), vote_scores=scores[j].tolist()))
            common.putl(PRIVATE/('neighbors_'+stage+'.jsonl'), private_neighbors)
        groups = {panel: [keys[i] for i in ids if keys[i].get('old_panel') == panel]
                  for panel in ('natural', 'pressure')}
        if stage == '1817':
            groups['selection1817'] = [keys[i] for i in ids]
            groups['new1317'] = [keys[i] for i in ids if keys[i].get('subset') == 'new']
        panels = {name: section(rows, baseline, all_predictions) for name, rows in groups.items() if rows}
        result = dict(N=len(ids), valid_N=len(ids), missing_N=0, invalid_N=0, panels=panels)
        if stage in ('160', '500'):
            result['continuation'] = gate(panels, int(stage))
        stages[stage] = result
        clean = [dict(all_predictions[i], sid=str(keys[i]['sid']), GT=keys[i]['GT'],
                      author=keys[i]['author'], old_panel=keys[i].get('old_panel'),
                      baseline107=baseline[i]['verdict']) for i in ids]
        common.putl(PRIVATE/('predictions_'+stage+'.jsonl'), clean)
        return result
    first = evaluate_ids(screen, '160')
    if first['continuation']['continue_']:
        old = sorted(i for i in keys if keys[i].get('old_panel') in ('natural', 'pressure'))
        second = evaluate_ids(old, '500')
        if second['continuation']['continue_']:
            evaluate_ids(sorted(keys), '1817')
    final = dict(selection=selection, stages=stages, elapsed_CPU_wall_seconds=time.perf_counter()-started,
                 new_GPU_CNY=0, new_API_CNY=0, patients_used_for_model_input=False,
                 deployment_note='Full107 prefill plus cached training-vector nearest-neighbor readout; CPU head time is not end-to-end throughput',
                 status='stopped_after_'+list(stages)[-1], no_more_configuration_search=True)
    write_json(PUBLIC/'results.json', final)
    write_json(PRIVATE/'complete.json', dict(status=final['status'], seconds=final['elapsed_CPU_wall_seconds'],
               new_GPU_CNY=0, new_API_CNY=0))
    report(final)
    print(json.dumps(dict(chosen={k: chosen[k] for k in ('k', 'voting')}, stages={stage: {
        name: {k: value[k] for k in ('N', 'delta_MCC', 'delta_correct', 'delta_false_S')}
        for name, value in result['panels'].items()} for stage, result in stages.items()},
        seconds=final['elapsed_CPU_wall_seconds'], new_GPU_CNY=0, new_API_CNY=0), ensure_ascii=False))


def report(result):
    selected = result['selection']['chosen']
    last = list(result['stages'])[-1]
    lines = ['# 121 nearest_memory', '',
        f"固定107的 verdict_prefix 表示做余弦kNN，32人2945训练、8人730验证。内部验证选择 k={selected['k']}、{selected['voting']}；6个配置完整指标见 results.json。无新神经网络训练/GPU/API。", '',
        '|范围|方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA净救回|',
        '|---|---|---:|---:|---:|---:|---:|']
    for stage, result_stage in result['stages'].items():
        for panel, value in result_stage['panels'].items():
            for model in ('label_only107', 'candidate'):
                score = value['scores'][model]
                net = '—' if model == 'label_only107' else '/'.join(str(
                    value['changes']['by_class'][g]['rescued']-value['changes']['by_class'][g]['harmed']) for g in LABELS)
                lines.append(f"|{stage} {panel} ({value['N']})|{model}|{score['mcc']:.4f}|{100*score['percent_agreement']:.2f}%|{score['correct']}|{score['false_S']}/{score['non_S']}|{net}|")
    positive = last == '1817'
    first_panels = result['stages']['160']['panels']
    screen_changes = {name: first_panels[name]['changes'] for name in ('natural', 'pressure')}
    extra_false = sum(value['false_S_new'] for value in screen_changes.values())
    avoided_false = sum(value['false_S_avoided'] for value in screen_changes.values())
    lines += ['', ('完成1817扩展，按实际总体及分面取舍判断；未自动升级。' if positive else
        f'在{last}范围未通过事先冻结的综合/风险继续规则，停止当前kNN配方；未继续扩大或搜索。'), '',
        f'最初160条新增false-S {extra_false}次、避免{avoided_false}次。自然集准确率提高不能抵消这些新增错误放行；全部类别得失照实保留。', '',
        '107祖先已见原40人的196条，内部验证不是完全无祖先暴露；选型20人亦有历史研究暴露。训练记忆只使用原GT，患者ID不作为特征。各类救回/误伤、混淆矩阵和全部验证配置保留在JSON。', '',
        'CPU近邻时间不等于完整部署速度：新输入仍需107的完整prefill。新增GPU/API费用均为0。', '',
        '方法参照：[kNN Prompting (ICLR 2023)](https://arxiv.org/abs/2303.13824)；本试验使用隐藏表示余弦，不声称复现其完整方法。反证：[Great Memory, Shallow Reasoning (NAACL 2025)](https://aclanthology.org/2025.naacl-short.40/)说明近邻记忆并不保证多事实推理。', '']
    (PUBLIC/'report.md').write_bytes('\n'.join(lines).encode('utf-8'))


def self_test():
    x = normalized([[1, 0], [0, 1], [-1, 0]])
    n, similarity = neighbors(x[:1], x)
    assert n.tolist() == [[0, 1, 2]] and np.allclose(similarity, [[1, 0, -1]])
    y = np.asarray([0, 0, 1, 2, 2])
    # Majority is0; frequency correction chooses1 when class1 is rarer.
    indices = np.asarray([[0, 1, 2]])
    assert votes(indices, y, np.asarray([10, 1, 2]), 3, 'uniform')[0].tolist() == [0]
    assert votes(indices, y, np.asarray([10, 1, 2]), 3, 'inverse_training_class_frequency')[0].tolist() == [1]
    assert tuple(LABELS) == ('Supported', 'Not Supported', 'Not Addressed')
    print(json.dumps(dict(PASS=True, cosine_order=True, inverse_class_frequency=True,
                         original_label_index=True, no_model=True)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--threads', type=int, default=4)
    a = p.parse_args()
    with threadpool_limits(limits=a.threads):
        self_test() if a.self_test else run()
