"""One CPU-only dual-state MLP; original117 split/selection, fixed160 screen."""
from __future__ import annotations

from collections import Counter
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
PRIVATE = ROOT / '.local_models/125_dual_state_readout'
PUBLIC = ROOT / 'outputs/125_dual_state_readout'
sys.path.insert(0, str(ROOT/'tasks/117_verdict_probe'))
from fit_probe117 import LABELS, metadata_rows, feature_matrices, metrics, write_json
from fit_mlp117 import CONFIG, MLPHead, predict, validation_key
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section
sys.path.insert(0, str(ROOT/'tasks/110_update_interpolation'))
from analyze110 import changes


def write_report(result):
    """Render only saved160 metrics; never infer missing native9B scores."""
    lines=['# 125 dual_state_readout：停止当前固定拼接配方','',
        '拼接冻结107的prompt_end与verdict_prefix（4096+4096维），仍只使用一个MLP128，其他超参与原117无权重流程相同。原32名患者1024条训练，8名730条内部验证，seed117、最大40轮、耐心8；内部验证选择第6轮，实际第14轮早停。仅评价预定160条，未计算其余1657条。','',
        '|范围|方案|MCC|PA|正确数|false-S/真实非S|',
        '|---|---|---:|---:|---:|---:|']
    for name,title in [('natural','自然128'),('pressure','压力32'),('pooled160','合计160')]:
        part=result['panels'][name]
        choices=[('paper_r1 作者历史系统',part['scores']['paper_r1']),
                 ('原作者式prompt＋未微调9B / 103 nine_native',None),
                 ('107',part['scores']['label_only107']),
                 ('117原MLP',part['vs_original_MLP']['scores']),
                 ('125拼接',part['scores']['candidate'])]
        for label,score in choices:
            if score is None:
                lines.append(f'|{title}|{label}|—|—|本160未完整覆盖|—|')
            else:
                lines.append(f"|{title}|{label}|{score['mcc']:.5f}|{100*score['percent_agreement']:.2f}%|{score['correct']}|{score['false_S']}/{score['non_S']}|")
    lines+=['',
        'paper_r1是同ID作者历史发布预测，不是同Judge同期强对照。原作者式未微调9B只保存原自然120／压力60，未完整覆盖本160，不填假数字；其原180同ID结果见[统一横表](../120_full_pool_sft/horizontal_comparison.md)。107使用104改写prompt，不是作者原版；同新版prompt未微调9B的共同391／94对照也在该横表。','',
        '相对原117 MLP，125合计少4条正确、MCC低0.06450、false-S多4次：正确S净+3，NS净−3，NA净−4；没有救回新的正确NS。压力面板尤其下降。相对107多6条正确主要来自S，但false-S多12，不能把自然PA上升当作本候选成功。','',
        '**停止当前固定配方，不扩500/1817，不调整拼接比例、tap、宽度或训练设置。** 这是否定本次配方的160条信号，不等于证明所有双状态方法无效。源特征和旧117代码未改。','',
        f"CPU执行约{result['elapsed_seconds']:.2f}秒；新增GPU/API均0。头、配置与曲线在私有125目录，完整类别矩阵和救回/误伤见[result160.json](result160.json)。"]
    (PUBLIC/'report.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))


def main():
    if (PRIVATE/'model.pt').exists() or (PUBLIC/'result160.json').exists():
        raise FileExistsError('Preserve the one fixed125 attempt; no refit or overwrite')
    started = time.perf_counter()
    rows = metadata_rows(ROOT/'.local_models/117_verdict_probe/metadata.jsonl')
    parts = {role:[i for i,r in enumerate(rows) if r['role']==role]
             for role in ('train','validation','screen')}
    if tuple(len(parts[r]) for r in parts)!=(1024,730,160):
        raise ValueError('Only the frozen1024/730/160 split is allowed')
    patient_n={role:len({str(rows[i]['sid']) for i in ix}) for role,ix in parts.items()}
    if patient_n!={'train':32,'validation':8,'screen':20}:
        raise ValueError('Original32/8/20 patient isolation changed')
    frozen160=common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    if {rows[i]['id'] for i in parts['screen']}!=set(frozen160):
        raise ValueError('Screen160 membership changed')
    matrices,info=feature_matrices(ROOT/'.local_models/117_verdict_probe/evidence/features_initial',rows)
    if any(matrices[k].shape!=(1914,4096) for k in ('prompt_end','verdict_prefix')):
        raise ValueError('Expected two aligned4096-dimensional frozen107 states')
    values=np.concatenate([matrices['prompt_end'],matrices['verdict_prefix']],axis=1)
    config=dict(CONFIG,feature='concat_prompt_end_verdict_prefix',feature_order=['prompt_end','verdict_prefix'],
                input_width=8192,loss='ordinary three-class CE; no class weighting')
    source=common.read(ROOT/'.local_models/117_verdict_probe/mlp_initial/selection.json')
    if any(source['config'].get(k)!=CONFIG[k] for k in CONFIG):
        raise ValueError('Original unweighted117 recipe changed')
    PRIVATE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    protocol=dict(task=125,candidate='dual_state_readout',config=config,parts={r:len(v) for r,v in parts.items()},
        patients=patient_n,feature_info=info,screen_selection=False,new_GPU_calls=0,new_API_calls=0,
        no_new_backbone_forward=True,other1657_scored=False,one_fixed_candidate=True)
    write_json(PRIVATE/'protocol.json',protocol)
    random.seed(117);np.random.seed(117);torch.manual_seed(117);torch.set_num_threads(4)
    rng=torch.Generator(device='cpu').manual_seed(117)
    scaler=StandardScaler().fit(values[parts['train']])
    model=MLPHead(scaler.mean_,scaler.scale_)
    optimizer=torch.optim.AdamW(model.parameters(),lr=CONFIG['learning_rate'],weight_decay=CONFIG['weight_decay'])
    x={r:torch.from_numpy(np.ascontiguousarray(values[ix])).float() for r,ix in parts.items()}
    y=torch.tensor([LABELS.index(rows[i]['GT']) for i in parts['train']],dtype=torch.long)
    validation=[rows[i] for i in parts['validation']]
    best=state=None;patience=0;curve=[]
    with threadpool_limits(limits=4):
        for epoch in range(1,CONFIG['max_epochs']+1):
            if time.perf_counter()-started>300:
                raise TimeoutError('Preserve partial curve; fixed CPU attempt exceeded five minutes')
            model.train();total=0.
            for ix in torch.randperm(len(y),generator=rng).split(CONFIG['batch_size']):
                optimizer.zero_grad(set_to_none=True)
                loss=F.cross_entropy(model(x['train'][ix]),y[ix])
                if not bool(torch.isfinite(loss)):raise FloatingPointError('Nonfinite125 CE')
                loss.backward();optimizer.step();total+=float(loss.detach())*len(ix)
            labels,_=predict(model,x['validation']);value=metrics(validation,labels)
            point=dict(epoch=epoch,training_loss=total/len(y),validation_metrics=value)
            curve.append(point)
            with (PRIVATE/'curve.jsonl').open('ab') as stream:
                stream.write((common.canonical(point)+'\n').encode('utf-8'))
            if best is None or validation_key(value)>validation_key(best['validation_metrics']):
                best=point;state=copy.deepcopy(model.state_dict());patience=0
            else:patience+=1
            if patience>=CONFIG['early_stopping_patience']:break
        if state is None:raise AssertionError('No validation-selected model')
        model.load_state_dict(state,strict=True);model.eval()
        torch.save(dict(config=config,labels=list(LABELS),state_dict=state,
                        selected_epoch=best['epoch']),PRIVATE/'model.pt')
        labels,probs=predict(model,x['screen'])
    screen=[rows[i] for i in parts['screen']]
    keymap={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    baseline={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    original={r['id']:r for r in common.rows(ROOT/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl')}
    predictions={r['id']:dict(id=r['id'],verdict=str(label),valid=True,
        probabilities=dict(zip(LABELS,p.tolist())),probabilities_calibrated=False)
        for r,label,p in zip(screen,labels,probs)}
    common.putl(PRIVATE/'screen_predictions.jsonl',[dict(predictions[r['id']],GT=r['GT'],sid=str(r['sid']),author=r['author']) for r in screen])
    panels={}
    for name,group in [('natural',[keymap[r['id']] for r in screen if keymap[r['id']]['old_panel']=='natural']),
                       ('pressure',[keymap[r['id']] for r in screen if keymap[r['id']]['old_panel']=='pressure']),
                       ('pooled160',[keymap[r['id']] for r in screen])]:
        current=section(group,baseline,predictions)
        old=metrics(group,[original[r['id']]['verdict'] for r in group]);new=current['scores']['candidate']
        paired=[dict(r,pred={'original_mlp':original[r['id']]['verdict'],'dual_state':predictions[r['id']]['verdict']}) for r in group]
        current['vs_original_MLP']=dict(scores=old,delta_MCC=new['mcc']-old['mcc'],
            delta_correct=new['correct']-old['correct'],delta_false_S=new['false_S']-old['false_S'],
            changes=changes(paired,'original_mlp','dual_state'))
        panels[name]=current
    result=dict(protocol,selected_epoch=best['epoch'],completed_epochs=len(curve),
        validation_metrics=best['validation_metrics'],stop_reason='patience8' if patience>=8 else 'max40',
        elapsed_seconds=time.perf_counter()-started,panels=panels,
        interpretation='Fixed160 screening only; no other1657 predictions or claims of full-cohort benefit')
    write_json(PUBLIC/'result160.json',result)
    write_report(result)
    common.putl(PUBLIC/'predictions160_sanitized.jsonl',[dict(predictions[r['id']],GT=r['GT'],sid=str(r['sid']),author=r['author']) for r in screen])
    print(common.canonical(dict(selected_epoch=best['epoch'],completed_epochs=len(curve),
        elapsed_seconds=result['elapsed_seconds'],panels={name:dict(N=z['N'],scores=z['scores']['candidate'],
            delta_MCC=z['delta_MCC'],delta_correct=z['delta_correct'],delta_false_S=z['delta_false_S'],
            vs_original_MLP=z['vs_original_MLP']) for name,z in panels.items()})))


if __name__=='__main__':main()
