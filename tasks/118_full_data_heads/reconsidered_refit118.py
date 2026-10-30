"""Fixed6/10-epoch full40 refits of two already selected117 CPU MLP recipes."""
from __future__ import annotations

import copy
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch.nn import functional as F
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/118_full_data_heads/reconsidered_refit'
SOURCE = ROOT/'.local_models/117_verdict_probe'
PUBLIC = ROOT/'outputs/118_full_data_heads'
sys.path.insert(0, str(ROOT/'tasks/117_verdict_probe'))
from refit_full117 import read_metadata, load_features
from fit_probe117 import LABELS, predict_head, metrics, write_json
from fit_mlp117 import CONFIG, MLPHead, load_head, predict
from fit_sqrt_mlp117 import weighted_class_values
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section


def run():
    started = time.perf_counter()
    protocol = common.read(PRIVATE/'protocol.json')
    if (PUBLIC/'reconsidered_refit.json').exists():
        raise FileExistsError('Preserve the single fixed full-refit follow-up')
    rows, parts = read_metadata(SOURCE/'metadata_fulltrain.jsonl')
    feature_dirs = [SOURCE/'evidence'/name for name in ('features_initial', 'features500_missing',
                                                      'features1817_missing', 'features_pool_missing')]
    values, info = load_features(feature_dirs, rows)
    index = {r['id']: i for i, r in enumerate(rows)}
    train = parts['train']; screens = parts['screen']
    train_x = torch.from_numpy(np.stack([values[index[r['id']]] for r in train])).float()
    labels = [r['GT'] for r in train]
    train_y = torch.tensor([LABELS.index(g) for g in labels], dtype=torch.long)
    scaler = StandardScaler().fit(train_x.numpy())
    keys = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    base = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    if set(keys) != {r['id'] for r in screens} or any(r['GT'] != keys[r['id']]['GT'] for r in screens):
        raise ValueError('Full-refit screen ID/GT association differs')
    fixed160 = common.read(SOURCE/'data_selection.json')['screen_ids']
    rest = [r['id'] for r in screens if r['id'] not in set(fixed160)]
    if len(fixed160) != 160 or len(rest) != 1657:
        raise ValueError('Fixed160 membership differs')
    recipes = [('unweighted_full', SOURCE/'mlp_initial/model.pt', 6, None),
               ('sqrt_weight_full', SOURCE/'sqrt_weight_mlp/model.pt', 10, .5)]
    result = dict(task=118, followup='reconsidered_refit', protocol=protocol,
        train_N=3675, train_patients=40, validation_used=False,
        former_validation8_now_training=True, train_GT={g: labels.count(g) for g in LABELS},
        selection_patients=20, feature_info=info, models={},
        new_GPU_CNY=0, new_API_CNY=0, original118_unchanged=True,
        no_epoch_or_beta_selection=True, confirmation40_used=False)
    all_predictions = {}
    torch.set_num_threads(4)
    with threadpool_limits(limits=4):
        for name, original_path, epochs, beta in recipes:
            folder = PRIVATE/name
            if folder.exists():
                raise FileExistsError('Do not overwrite an attempted full-refit model: '+name)
            folder.mkdir()
            _, original = load_head(original_path)
            if original['selected_epoch'] != epochs:
                raise ValueError('Original117 selected epoch changed')
            config = dict(original['config'])
            if any(config[k] != CONFIG[k] for k in ('feature', 'hidden', 'dropout', 'learning_rate',
                                                   'weight_decay', 'batch_size', 'seed')):
                raise ValueError('Original architecture/optimizer recipe changed')
            if beta is None:
                weight = None
                weight_map = None
            else:
                counts, weight_array = weighted_class_values(labels)
                weight = torch.from_numpy(weight_array)
                weight_map = dict(zip(LABELS, weight_array.tolist()))
            selection = dict(candidate=name, fixed_epochs=epochs, beta=beta,
                weights=weight_map, config=config, new_epoch_selection=False, validation_used=False,
                train_N=3675, train_patients=40, scaler_fitted_on_full_training_only=True,
                source_recipe_model_sha256=common.sha(original_path), source_weights_used=False)
            write_json(folder/'selection.json', selection)
            random.seed(CONFIG['seed']); np.random.seed(CONFIG['seed']); torch.manual_seed(CONFIG['seed'])
            order = torch.Generator(device='cpu').manual_seed(CONFIG['seed'])
            model = MLPHead(scaler.mean_, scaler.scale_)
            optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG['learning_rate'], weight_decay=CONFIG['weight_decay'])
            for epoch in range(1, epochs+1):
                if time.perf_counter()-started > 300:
                    raise TimeoutError('CPU refits exceeded five minutes; preserve partial attempts')
                model.train(); total = 0.
                for batch in torch.randperm(len(train_y), generator=order).split(CONFIG['batch_size']):
                    optimizer.zero_grad(set_to_none=True)
                    loss = F.cross_entropy(model(train_x[batch]), train_y[batch], weight=weight, reduction='none').mean()
                    if not bool(torch.isfinite(loss)):
                        raise FloatingPointError('Nonfinite fixed-refit loss')
                    loss.backward(); optimizer.step()
                    total += float(loss.detach())*len(batch)
                with (folder/'curve.jsonl').open('ab') as stream:
                    stream.write((common.canonical(dict(epoch=epoch, training_loss=total/len(train_y)))+'\n').encode())
            torch.save(dict(config=config, labels=list(LABELS), state_dict=copy.deepcopy(model.state_dict()),
                            selected_epoch=epochs, fixed_refit=True), folder/'model.pt')
            model, _ = load_head(folder/'model.pt')
            predicted = {}
            def score(ids):
                raw = torch.from_numpy(np.stack([values[index[i]] for i in ids])).float()
                decisions, probabilities = predict(model, raw)
                for i, decision, probability in zip(ids, decisions, probabilities):
                    predicted[i] = dict(id=i, verdict=str(decision), valid=True,
                        probabilities=dict(zip(LABELS, probability.tolist())), probabilities_calibrated=False)
            score(fixed160)
            small = metrics([keys[i] for i in fixed160], [predicted[i]['verdict'] for i in fixed160])
            can_expand = all(v['recall'] is None or v['recall'] > 0 for v in small['per_class'].values())
            if can_expand:
                score(rest)
            ids = sorted(predicted)
            records = [dict(predicted[i], GT=keys[i]['GT'], sid=str(keys[i]['sid']),
                       author=keys[i]['author'], old_panel=keys[i].get('old_panel'),
                       subset=keys[i].get('subset'), baseline107=base[i]['verdict']) for i in ids]
            common.putl(folder/'predictions.jsonl', records)
            common.putl(PUBLIC/('reconsidered_refit_'+name+'_predictions.jsonl'), records)
            result['models'][name] = dict(recipe=selection, expanded_to1817=can_expand,
                                         N=len(predicted), screen160_metrics=small)
            all_predictions[name] = predicted
            print(common.canonical(dict(model=name, fixed_epochs=epochs, N=len(predicted))), flush=True)
        # Reuse original118 linear model and all160 first predictions.
        linear_folder = ROOT/'.local_models/118_full_data_heads/refit_models/balanced_linear_full'
        old = common.rows(ROOT/'outputs/118_full_data_heads/full_linear_160_full_linear_predictions.jsonl')
        if len(old) != 160 or {r['id'] for r in old} != set(fixed160):
            raise ValueError('Original118 linear160 first receipts differ')
        linear_pred = {r['id']: r for r in old}
        with np.load(linear_folder/'verdict_prefix_head.npz', allow_pickle=False) as head:
            lab, probability = predict_head(head, np.stack([values[index[i]] for i in rest]))
        for i, label, p in zip(rest, lab, probability):
            linear_pred[i] = dict(id=i, verdict=str(label), valid=True, probabilities=dict(zip(LABELS, p.tolist())),
                                  probabilities_calibrated=False)
        all_predictions['full_linear'] = linear_pred
        result['models']['full_linear'] = dict(N=1817, original160_reused=True, new_predictions=1657,
            fixed_C=.0001, class_weight='balanced', refit=False)
        common.putl(PUBLIC/'reconsidered_refit_full_linear_predictions.jsonl',
            [dict(linear_pred[i], GT=keys[i]['GT'], sid=str(keys[i]['sid']), author=keys[i]['author'],
                  old_panel=keys[i].get('old_panel'), baseline107=base[i]['verdict']) for i in sorted(keys)])
    for name, filename in [('original1024_unweighted', 'reconsidered_extension_verdict_mlp_predictions.jsonl'),
                           ('original1024_sqrt', 'sqrt_weight_mlp_predictions.jsonl')]:
        prior = common.rows(ROOT/'outputs/117_verdict_probe'/filename)
        if len(prior) != 1817 or {r['id'] for r in prior} != set(keys):
            raise ValueError('Existing1024-model full predictions differ')
        all_predictions[name] = {r['id']: r for r in prior}
        result['models'][name] = dict(N=1817, all_existing_predictions_reused=True)
    for name, pred in all_predictions.items():
        ids = sorted(pred)
        groups = dict(natural400=[keys[i] for i in ids if keys[i].get('old_panel') == 'natural'],
                      pressure100=[keys[i] for i in ids if keys[i].get('old_panel') == 'pressure'])
        if len(pred) == 1817:
            groups.update(selection1817=[keys[i] for i in ids],
                          new1317=[keys[i] for i in ids if keys[i].get('subset') == 'new'])
        result['models'][name]['panels'] = {p: section(k, base, pred) for p, k in groups.items() if k}
    result['CPU_elapsed_seconds'] = time.perf_counter()-started
    write_json(PUBLIC/'reconsidered_refit.json', result)
    report(result)
    print(common.canonical({name: {p: {k: v[k] for k in ('N', 'delta_MCC', 'delta_correct', 'delta_false_S')}
                                   for p, v in z['panels'].items()} for name, z in result['models'].items()}))


def report(result):
    lines = ['# 118固定正向配方的全40人重拟合', '',
        '仅检验扩大训练资料：原40人3675条，固定无权重6轮和逆平方根权重10轮。原8名内部验证患者已进入训练，未再选epoch或β。原118的balanced16轮结果不改；其线性头仅补1657条，旧160首回执复用。', '',
        '|完整1817方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA净救回|',
        '|---|---:|---:|---:|---:|---:|']
    reference = next(z['panels']['selection1817'] for z in result['models'].values() if 'selection1817' in z['panels'])
    for name in ('label_only107', 'paper_r1'):
        m = reference['scores'][name]
        lines.append(f"|{name}|{m['mcc']:.4f}|{100*m['percent_agreement']:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|—|")
    for name, model in result['models'].items():
        if 'selection1817' not in model['panels']:
            lines.append(f'|{name}（160类塌缩，未扩）|—|—|—|—|—|'); continue
        p = model['panels']['selection1817']; m = p['scores']['candidate']
        net = '/'.join(str(p['changes']['by_class'][g]['rescued']-p['changes']['by_class'][g]['harmed']) for g in LABELS)
        lines.append(f"|{name}|{m['mcc']:.4f}|{100*m['percent_agreement']:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{net}|")
    lines += ['', '扩大资料没有普遍改善：无权重全量头的MCC优势几乎消失，false-S大幅增加，不建议替换原1024版本。全量平方根权重头仍保留MCC/PA收益，且NA净救回8条、false-S仅增加6次；它比原1024平方根头少18条正确、少6次false-S，属于可保留讨论的另一种取舍。全量线性参考的总体MCC和正确数下降。', '',
        '全部自然400、压力100、新1317及完整1817指标和类别得失见同名JSON；保留失败/退化结果，不重新选参。这里只证明固定配方在当前开发队列上的表现，不能把增加数据、患者覆盖和训练更新次数的共同变化唯一归因于其中一个因素。', '',
        '全部使用冻结107缓存，新增GPU/API费用0；模型与Scalers私有保存。完整部署仍需9B原prompt prefill，CPU头速度不等于端到端吞吐。', '']
    (PUBLIC/'reconsidered_refit.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    run()
