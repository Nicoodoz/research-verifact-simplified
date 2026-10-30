"""One fixed inverse-square-root-weight CPU MLP; no beta or threshold search."""
from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch.nn import functional as F
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from fit_mlp117 import CONFIG, MLPHead, predict, validation_key, load_head
from fit_probe117 import LABELS, metadata_rows, feature_matrices, metrics, write_json

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/117_verdict_probe'
WORK = PRIVATE/'sqrt_weight_mlp'
PUBLIC = ROOT/'outputs/117_verdict_probe'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section


def weighted_class_values(labels):
    counts = np.asarray([(np.asarray(labels) == label).sum() for label in LABELS], dtype=np.float64)
    if (counts <= 0).any():
        raise ValueError('All three original classes are required')
    values = counts**(-.5)
    values /= values.mean()
    return counts, values.astype(np.float32)


def continuation(panels, n):
    pooled = panels['pooled']
    recalls = pooled['scores']['candidate']['per_class']
    guard = all(v['recall'] is None or v['recall'] >= .10 for v in recalls.values())
    gain = panels['natural']['delta_MCC'] >= .01 or pooled['delta_MCC'] >= .01
    risk = pooled['delta_false_S'] <= (-2 if n == 160 else -3) and pooled['delta_correct'] >= (-5 if n == 160 else -15)
    return dict(no_obvious_class_collapse=guard, MCC_value=gain, risk_value=risk,
                continue_=guard and (gain or risk), false_S_increase_alone_is_not_veto=True)


def run():
    began = time.perf_counter()
    protocol = common.read(WORK/'protocol.json')
    if (WORK/'model.pt').exists() or (PUBLIC/'sqrt_weight_mlp.json').exists():
        raise FileExistsError('Preserve this one fixed attempt; do not refit')
    rows = metadata_rows(PRIVATE/'metadata.jsonl')
    matrix, feature_info = feature_matrices(PRIVATE/'evidence/features_initial', rows)
    x = matrix['verdict_prefix']
    roles = {role: [i for i, r in enumerate(rows) if r['role'] == role] for role in ('train', 'validation', 'screen')}
    if tuple(len(roles[role]) for role in roles) != (1024, 730, 160):
        raise ValueError('Reuse the fixed1171024/730/160 split')
    train = [rows[i] for i in roles['train']]
    val = [rows[i] for i in roles['validation']]
    train_labels = [r['GT'] for r in train]
    counts, weights = weighted_class_values(train_labels)
    if not np.isclose(weights.mean(), 1., atol=1e-7):
        raise AssertionError('Arithmetic class-weight mean must equal1')
    config = dict(CONFIG, class_weight='inverse_sqrt_training_frequency', beta=.5,
                  loss='inverse-sqrt class-weighted three-class CE, ordinary sample mean')
    write_json(WORK/'config.json', dict(config, class_counts=dict(zip(LABELS, counts.astype(int).tolist())),
                    class_weights=dict(zip(LABELS, weights.tolist())),
                    arithmetic_class_mean=float(weights.mean()),
                    empirical_training_mean=float(np.dot(counts, weights)/counts.sum())))
    random.seed(CONFIG['seed']); np.random.seed(CONFIG['seed']); torch.manual_seed(CONFIG['seed'])
    torch.set_num_threads(4)
    order_rng = torch.Generator(device='cpu').manual_seed(CONFIG['seed'])
    scaler = StandardScaler().fit(x[roles['train']])
    model = MLPHead(scaler.mean_, scaler.scale_)
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG['learning_rate'], weight_decay=CONFIG['weight_decay'])
    tensors = {role: torch.from_numpy(np.ascontiguousarray(x[ids])).float() for role, ids in roles.items()}
    y = torch.tensor([LABELS.index(g) for g in train_labels], dtype=torch.long)
    class_weights = torch.from_numpy(weights)
    best = best_state = None
    patience = 0
    curves = []
    with threadpool_limits(limits=4):
        for epoch in range(1, CONFIG['max_epochs']+1):
            if time.perf_counter()-began > 300:
                raise TimeoutError('Fixed CPU fit exceeded five minutes; preserve partial curve and stop')
            model.train(); total = 0.
            for batch in torch.randperm(len(y), generator=order_rng).split(CONFIG['batch_size']):
                optimizer.zero_grad(set_to_none=True)
                loss = F.cross_entropy(model(tensors['train'][batch]), y[batch],
                                       weight=class_weights, reduction='none').mean()
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError('Nonfinite fixed weighted loss')
                loss.backward(); optimizer.step()
                total += float(loss.detach())*len(batch)
            predictions, _ = predict(model, tensors['validation'])
            value = metrics(val, predictions)
            point = dict(epoch=epoch, training_loss=total/len(y), validation_metrics=value,
                         elapsed_seconds=time.perf_counter()-began)
            curves.append(point)
            with (WORK/'curve.jsonl').open('ab') as stream:
                stream.write((common.canonical(point)+'\n').encode())
            if best is None or validation_key(value) > validation_key(best['validation_metrics']):
                best = point; best_state = copy.deepcopy(model.state_dict()); patience = 0
            else:
                patience += 1
            if patience >= CONFIG['early_stopping_patience']:
                break
        if best_state is None:
            raise AssertionError('No validation-selected model')
        selection = dict(candidate='sqrt_weight_mlp', config=config, selected_epoch=best['epoch'],
            completed_epochs=len(curves), validation_metrics=best['validation_metrics'],
            class_counts=dict(zip(LABELS, counts.astype(int).tolist())),
            class_weights=dict(zip(LABELS, weights.tolist())), feature_info=feature_info,
            selection_uses_screen=False, new_GPU_CNY=0, new_API_CNY=0, protocol=protocol)
        write_json(WORK/'selection.json', selection)
        torch.save(dict(config=config, labels=list(LABELS), state_dict=best_state,
                        selected_epoch=best['epoch']), WORK/'model.pt')
        model, saved = load_head(WORK/'model.pt')
        assert saved['selected_epoch'] == best['epoch']
        keys = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
        base = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
        cache = {r['id']: x[i] for i, r in enumerate(rows)}
        predictions = {}
        stages = {}

        def evaluate_ids(ids, stage):
            absent = [i for i in ids if i not in predictions]
            needed = set(absent)-set(cache)
            if needed:
                for folder in ('features500_missing', 'features1817_missing'):
                    for path in (PRIVATE/'evidence'/folder/'batches').glob('*.npz'):
                        with np.load(path, allow_pickle=False) as z:
                            for index, identifier in enumerate(z['ids'].astype(str)):
                                if identifier in needed:
                                    if identifier in cache:
                                        raise ValueError('Duplicate new feature ID')
                                    cache[identifier] = z['verdict_prefix'][index].copy()
                if not needed <= set(cache):
                    raise ValueError('Missing cached original107 prefix states')
            if absent:
                labels, probabilities = predict(model, torch.from_numpy(np.stack([cache[i] for i in absent])).float())
                for i, label, probability in zip(absent, labels, probabilities):
                    predictions[i] = dict(id=i, verdict=str(label), valid=True,
                        probabilities=dict(zip(LABELS, probability.tolist())), probabilities_calibrated=False)
            groups = dict(natural=[keys[i] for i in ids if keys[i].get('old_panel') == 'natural'],
                          pressure=[keys[i] for i in ids if keys[i].get('old_panel') == 'pressure'],
                          pooled=[keys[i] for i in ids])
            if stage == '1817':
                groups['new1317'] = [keys[i] for i in ids if keys[i].get('subset') == 'new']
            panels = {name: section(group, base, predictions) for name, group in groups.items() if group}
            value = dict(N=len(ids), valid_N=len(ids), missing_N=0, invalid_N=0, panels=panels)
            if stage in ('160', '500'):
                value['continuation'] = continuation(panels, int(stage))
            stages[stage] = value
            records = [dict(predictions[i], GT=keys[i]['GT'], sid=str(keys[i]['sid']),
                       author=keys[i]['author'], old_panel=keys[i].get('old_panel'),
                       baseline107=base[i]['verdict']) for i in ids]
            common.putl(WORK/('predictions_'+stage+'.jsonl'), records)
            return value

        first = evaluate_ids([rows[i]['id'] for i in roles['screen']], '160')
        if first['continuation']['continue_']:
            second = evaluate_ids(sorted(i for i in keys if keys[i].get('old_panel') in ('natural', 'pressure')), '500')
            if second['continuation']['continue_']:
                evaluate_ids(sorted(keys), '1817')
        result = dict(selection=selection, stages=stages, elapsed_CPU_seconds=time.perf_counter()-began,
                      new_GPU_CNY=0, new_API_CNY=0, one_beta_only=True, confirmation40_used=False,
                      deployment_requires_original107_full_prefill=True)
        write_json(PUBLIC/'sqrt_weight_mlp.json', result)
        last = list(stages)[-1]
        common.putl(PUBLIC/'sqrt_weight_mlp_predictions.jsonl', common.rows(WORK/('predictions_'+last+'.jsonl')))
        report(result)
        print(common.canonical(dict(selected_epoch=best['epoch'], completed_epochs=len(curves),
            class_weights=selection['class_weights'], elapsed_CPU_seconds=result['elapsed_CPU_seconds'],
            stages={s: {p: {k: v[k] for k in ('N', 'delta_MCC', 'delta_correct', 'delta_false_S')}
                        for p, v in z['panels'].items()} for s, z in stages.items()})))


def report(result):
    chosen = result['selection']
    lines = ['# 117 sqrt_weight_mlp：固定中间类别权重', '',
        f"同117的1024训练/730内部验证，固定β=0.5，类别逆平方根权重按三类算术均值归一为1。128隐藏单元、dropout0.1、lr0.001、seed117及早停规则不变，内部验证选中epoch{chosen['selected_epoch']}。这是成熟权重方案的有限调参，不是新算法；没有搜索其他β。", '',
        '|范围|方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA净救回|',
        '|---|---|---:|---:|---:|---:|---:|']
    for stage, value in result['stages'].items():
        for panel, p in value['panels'].items():
            if panel == 'pooled' and stage != '1817':
                continue
            for name in ('label_only107', 'candidate'):
                m = p['scores'][name]
                net = '—' if name == 'label_only107' else '/'.join(str(p['changes']['by_class'][g]['rescued']-
                      p['changes']['by_class'][g]['harmed']) for g in LABELS)
                lines.append(f"|{stage}/{panel}|{name}|{m['mcc']:.4f}|{100*m['percent_agreement']:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{net}|")
    lines += ['', '全部训练曲线、权重、内部选点和各阶段结果已保留；没有按开发评价改epoch或阈值。原模型/预测未修改。该队列是已有历史暴露的开发选型患者，不称独立测试。', '',
              '新增GPU/API费用均为0；缓存CPU头部速度不是完整部署速度，仍需107原9B完整prefill。', '']
    (PUBLIC/'sqrt_weight_mlp.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    run()
