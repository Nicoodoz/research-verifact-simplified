"""One second seed for two fixed positive CPU recipes; no repeated selection."""
from __future__ import annotations

import copy
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch.nn import functional as F
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/118_full_data_heads/seed_stability'
SOURCE = ROOT/'.local_models/117_verdict_probe'
PUBLIC = ROOT/'outputs/118_full_data_heads'
sys.path.insert(0, str(ROOT/'tasks/117_verdict_probe'))
from fit_mlp117 import MLPHead, load_head, predict
from fit_probe117 import LABELS, metadata_rows, write_json
from refit_full117 import read_metadata, load_features
from fit_sqrt_mlp117 import weighted_class_values
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section
sys.path.insert(0, str(ROOT/'tasks/110_update_interpolation'))
from analyze110 import changes


def run():
    start = time.perf_counter()
    protocol = common.read(PRIVATE/'protocol.json')
    if (PUBLIC/'seed_stability.json').exists():
        raise FileExistsError('Keep the single second-seed study; never select the better seed')
    rows, parts = read_metadata(SOURCE/'metadata_fulltrain.jsonl')
    values, feature_info = load_features([SOURCE/'evidence'/n for n in
        ('features_initial', 'features500_missing', 'features1817_missing', 'features_pool_missing')], rows)
    position = {r['id']: i for i, r in enumerate(rows)}
    original = metadata_rows(SOURCE/'metadata.jsonl')
    original_train = [r for r in original if r['role'] == 'train']
    if len(original_train) != 1024 or any(r['GT'] != rows[position[r['id']]]['GT'] for r in original_train):
        raise ValueError('Original1024 training IDs/GT differ from source features')
    keys = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    base = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    screen_ids = [r['id'] for r in parts['screen']]
    screen_x = torch.from_numpy(np.stack([values[position[i]] for i in screen_ids])).float()
    groups = dict(natural400=[keys[i] for i in screen_ids if keys[i].get('old_panel') == 'natural'],
                  pressure100=[keys[i] for i in screen_ids if keys[i].get('old_panel') == 'pressure'],
                  new1317=[keys[i] for i in screen_ids if keys[i].get('subset') == 'new'],
                  selection1817=[keys[i] for i in screen_ids])
    specs = [dict(name='original1024_unweighted', rows=original_train,
                  source=SOURCE/'mlp_initial/model.pt', epochs=6,
                  prior=ROOT/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl'),
             dict(name='full3675_sqrt', rows=parts['train'],
                  source=ROOT/'.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/model.pt',
                  epochs=10, prior=PUBLIC/'reconsidered_refit_sqrt_weight_full_predictions.jsonl')]
    result = dict(task=118, followup='seed_stability', protocol=protocol, feature_info=feature_info,
        models={}, new_GPU_CNY=0, new_API_CNY=0, no_new_epoch_or_beta_selection=True,
        no_best_seed_selection=True, confirmation40_used=False,
        interpretation='Fixed-epoch replication of selected recipes, not a new full early-stopping selection process')
    torch.set_num_threads(4)
    with threadpool_limits(limits=4):
        for spec in specs:
            folder = PRIVATE/spec['name']
            if folder.exists():
                raise FileExistsError('Preserve attempted second seed: '+spec['name'])
            folder.mkdir()
            source_model, saved = load_head(spec['source'])
            cfg = saved['config']; seed = cfg['seed']+1
            if seed != 118 or cfg['seed'] != 117 or saved['selected_epoch'] != spec['epochs']:
                raise ValueError('Unexpected source recipe seed/epoch')
            training = spec['rows']
            x = torch.from_numpy(np.stack([values[position[r['id']]] for r in training])).float()
            labels = [r['GT'] for r in training]
            y = torch.tensor([LABELS.index(g) for g in labels], dtype=torch.long)
            weight = torch.from_numpy(weighted_class_values(labels)[1]) if spec['name'] == 'full3675_sqrt' else None
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            order = torch.Generator(device='cpu').manual_seed(seed)
            model = MLPHead(source_model.mean.numpy(), source_model.scale.numpy())
            if not torch.equal(model.mean, source_model.mean) or not torch.equal(model.scale, source_model.scale):
                raise AssertionError('Second seed changed source scaler')
            optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
            for epoch in range(1, spec['epochs']+1):
                if time.perf_counter()-start > 300:
                    raise TimeoutError('Five-minute CPU limit reached; preserve partial second seed')
                model.train(); total = 0.
                for batch in torch.randperm(len(y), generator=order).split(cfg['batch_size']):
                    optimizer.zero_grad(set_to_none=True)
                    loss = F.cross_entropy(model(x[batch]), y[batch], weight=weight, reduction='none').mean()
                    if not bool(torch.isfinite(loss)):
                        raise FloatingPointError('Nonfinite second-seed loss')
                    loss.backward(); optimizer.step()
                    total += float(loss.detach())*len(batch)
                with (folder/'curve.jsonl').open('ab') as stream:
                    stream.write((common.canonical(dict(epoch=epoch, training_loss=total/len(y)))+'\n').encode())
            new_cfg = dict(cfg, seed=seed)
            torch.save(dict(config=new_cfg, labels=list(LABELS), state_dict=copy.deepcopy(model.state_dict()),
                            selected_epoch=spec['epochs'], fixed_refit=True), folder/'model.pt')
            restored, _ = load_head(folder/'model.pt')
            decisions, probabilities = predict(restored, screen_x)
            records = [dict(id=i, sid=str(keys[i]['sid']), GT=keys[i]['GT'], author=keys[i]['author'],
                        old_panel=keys[i].get('old_panel'), subset=keys[i].get('subset'), verdict=str(g), valid=True,
                        probabilities=dict(zip(LABELS, p.tolist())), probabilities_calibrated=False)
                       for i, g, p in zip(screen_ids, decisions, probabilities)]
            current = {r['id']: r for r in records}
            previous_rows = common.rows(spec['prior'])
            previous = {r['id']: r for r in previous_rows}
            if len(previous_rows) != 1817 or set(previous) != set(current):
                raise ValueError('First-seed complete1817 predictions are missing or differ')
            common.putl(PUBLIC/('seed_stability_'+spec['name']+'_seed118_predictions.jsonl'), records)
            entry = dict(source_seed=117, second_seed=118, fixed_epochs=spec['epochs'], N=1817,
                same_source_scaler=True, weights=None if weight is None else dict(zip(LABELS, weight.tolist())),
                source_model_sha256=common.sha(spec['source']), panels={})
            for panel, cohort in groups.items():
                first = section(cohort, base, previous)
                second = section(cohort, base, current)
                paired = [dict(r, pred={'seed117': previous[r['id']]['verdict'], 'seed118': current[r['id']]['verdict']}) for r in cohort]
                a, b = first['scores']['candidate'], second['scores']['candidate']
                entry['panels'][panel] = dict(seed117=first, seed118=second,
                    second_minus_first=dict(MCC=b['mcc']-a['mcc'], PA=b['percent_agreement']-a['percent_agreement'],
                        correct=b['correct']-a['correct'], false_S=b['false_S']-a['false_S'],
                        changes=changes(paired, 'seed117', 'seed118')))
            result['models'][spec['name']] = entry
            print(common.canonical(dict(model=spec['name'], seed=seed, N=1817)), flush=True)
    result['CPU_elapsed_seconds'] = time.perf_counter()-start
    write_json(PUBLIC/'seed_stability.json', result)
    report(result)
    print(common.canonical({name: {panel: {
        str(seed): {k: value['scores']['candidate'][k] for k in ('mcc', 'correct', 'false_S')}
        for seed, value in ((117, p['seed117']), (118, p['seed118']))}
        for panel, p in data['panels'].items()} for name, data in result['models'].items()}))


def report(result):
    lines = ['# 两个固定CPU头的第二seed稳定性检查', '',
        '每个配置仅增加seed118；原seed117全部保留，不按结果选最好seed。原1024无权重头固定6轮，全3675平方根权重头固定10轮；Scaler、训练ID顺序、网络、学习率和权重规则不变。该复验不等价于重新完整运行早停选型流程。', '',
        '|完整1817方案|seed|MCC|PA|正确数|false-S/真实非S|',
        '|---|---:|---:|---:|---:|---:|']
    reference = next(iter(result['models'].values()))['panels']['selection1817']['seed117']['scores']
    for label in ('label_only107', 'paper_r1'):
        v = reference[label]
        lines.append(f"|{label}|历史|{v['mcc']:.4f}|{100*v['percent_agreement']:.2f}%|{v['correct']}|{v['false_S']}/{v['non_S']}|")
    for name, data in result['models'].items():
        for seed in (117, 118):
            v = data['panels']['selection1817']['seed'+str(seed)]['scores']['candidate']
            lines.append(f"|{name}|{seed}|{v['mcc']:.4f}|{100*v['percent_agreement']:.2f}%|{v['correct']}|{v['false_S']}/{v['non_S']}|")
    lines += ['', '以下为seed118减seed117，不是选优指标：', '',
        '|配置|范围|ΔMCC|Δ正确|Δfalse-S|', '|---|---|---:|---:|---:|']
    for name, data in result['models'].items():
        for panel, value in data['panels'].items():
            d = value['second_minus_first']
            lines.append(f"|{name}|{panel}|{d['MCC']:+.4f}|{d['correct']:+d}|{d['false_S']:+d}|")
    lines += ['', '原1024无权重头的固定6轮收益对seed敏感：第二seed的MCC低于107，并显著损失NA。全3675平方根头的两seed都保留约0.026–0.028的MCC增益，但false-S代价从+6变成+24，风险稳定性弱于总体MCC稳定性。保留两次结果，不按结果挑选较好seed。', '',
        '自然400、压力100、新1317与完整1817的两seed完整指标、混淆矩阵及类别救回/误伤见同名JSON。只有两次固定seed，不能据此宣称普遍稳定性；不追加第三seed。全部评价来自历史暴露的开发选型20人，没有使用确认40人。', '',
              '新增GPU/API费用0；模型/曲线私有保存。完整部署仍需107原9B prefill。', '']
    (PUBLIC/'seed_stability.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    run()
