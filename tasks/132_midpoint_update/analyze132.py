"""Read first midpoint receipts and apply the pre-written continuation rule."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'.local_models/132_midpoint_update'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
from final_compare120 import paired,metrics,LABELS


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('screen160','old500','selection1817','internal687'),default='screen160');a=p.parse_args()
    keys={r['id']:r for r in c.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    target=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids'] if a.scope=='screen160' else sorted(i for i,r in keys.items() if r['old_panel'] in ('natural','pressure'))
    paths=[P/'evidence/midpoint_screen160']
    if a.scope=='old500':paths.append(P/'evidence/midpoint_old500')
    if a.scope=='selection1817':
        target=sorted(keys)
        paths+=[P/'evidence/midpoint_old500',P/'evidence/midpoint_selection1817']
    internal=[]
    if a.scope=='internal687':
        internal=c.rows(ROOT/'outputs/120_full_pool_sft/internal687_predictions_sanitized.jsonl')
        keys={r['id']:r for r in internal};target=sorted(keys);paths=[P/'evidence/midpoint_internal687']
    values=collect(paths);new={r['id']:r for r in values}
    if len(new)!=len(values) or set(new)!=set(target):raise ValueError('Require all distinct first receipts')
    sha=c.read(P/'adapter_final/composition.json')['adapter_sha256']
    if any(r['source_adapter_sha256']!=sha for r in values):raise ValueError('Wrong midpoint adapter')
    b107={r['id']:r for r in c.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    b120={r['id']:r for r in c.rows(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')}
    prompt_hashes={i:r['source_prompt_sha256_104'] for i,r in b120.items()}
    if a.scope=='internal687':
        b107={r['id']:dict(verdict=r['baseline107']) for r in internal}
        b120={r['id']:dict(verdict=r['candidate120']) for r in internal}
        prompt_hashes={r['id']:r['expected_prompt_sha256'] for r in c.rows(ROOT/'.local_models/120_full_pool_sft/internal687/bundle/data/internal687/internal120_inputs.jsonl')}
    for i,r in new.items():
        if r['source_prompt_sha256_104']!=prompt_hashes[i]:raise ValueError('Prompt changed')
    joint=[keys[i] for i in target if new[i]['valid']]
    groups={'all':joint}
    native103={};base105={}
    if a.scope in ('old500','selection1817'):
        groups.update({panel:[r for r in joint if r['old_panel']==panel] for panel in ('natural','pressure')})
        if a.scope=='selection1817':groups['new1317']=[r for r in joint if r.get('subset')=='new']
        native103={r['id']:r for r in c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')}
        base105={r['id']:r for r in c.rows(ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r['arm']=='base_judge'}
        for panel in ('natural','pressure'):
            groups['same103_'+panel]=[r for r in joint if r['id'] in native103 and native103[r['id']]['panel']==panel and native103[r['id']]['arms']['nine_native']['valid']]
            groups['same105base_'+panel]=[r for r in joint if r['old_panel']==panel and r['id'] in base105 and base105[r['id']]['parsed']['valid']]
    result=dict(scope=a.scope,expected_N=len(target),received_N=len(values),joint_valid_N=len(joint),invalid_N=len(values)-len(joint),
        fixed_alpha=.5,source107_sha256=c.read(P/'adapter_final/composition.json')['source107_sha256'],
        source120_sha256=c.read(P/'adapter_final/composition.json')['source120_sha256'],new_training=False,
        new_API=0,panels={})
    for name,rows in groups.items():
        scores={
            'paper_r1':metrics(rows,{r['id']:r['paper_r1'] for r in rows}),
            'label_only107':metrics(rows,{r['id']:b107[r['id']]['verdict'] for r in rows}),
            'full_pool120':metrics(rows,{r['id']:b120[r['id']]['verdict'] for r in rows}),
            'midpoint132':metrics(rows,{r['id']:new[r['id']]['verdict'] for r in rows})}
        if name.startswith('same103_'):
            scores['base9b_author_prompt_cached103']=metrics(rows,{r['id']:native103[r['id']]['predictions']['nine_native'] for r in rows})
        if name.startswith('same105base_'):
            if any(base105[r['id']]['prompt_token_sha256']!=b107[r['id']]['prompt_token_sha256'] for r in rows):raise ValueError('Cached unfine-tuned prompt differs')
            scores['base9b_same104_prompt_cached105']=metrics(rows,{r['id']:base105[r['id']]['parsed']['verdict'] for r in rows})
        bootstrap=a.scope=='selection1817' and name=='all' and len(rows)==1817
        result['panels'][name]=dict(scores=scores,vs107=paired(rows,b107,new,'label_only107',bootstrap=bootstrap),vs120=paired(rows,b120,new,'full_pool120',bootstrap=bootstrap))
    result['by_author']={author:dict(vs107=paired([r for r in joint if r['author']==author],b107,new,'label_only107'),
        vs120=paired([r for r in joint if r['author']==author],b120,new,'full_pool120')) for author in sorted({r['author'] for r in joint})}
    if a.scope=='selection1817':
        ordered=sorted(target,key=lambda i:(b107[i]['input_tokens'],i))
        result['by_input_length']={}
        for q in range(4):
            members=ordered[q*len(ordered)//4:(q+1)*len(ordered)//4]
            selected=[keys[i] for i in members if new[i]['valid']]
            result['by_input_length'][str(q+1)]=dict(expected_N=len(members),valid_N=len(selected),
                min_tokens=min(b107[i]['input_tokens'] for i in members),max_tokens=max(b107[i]['input_tokens'] for i in members),
                vs107=paired(selected,b107,new,'label_only107'),vs120=paired(selected,b120,new,'full_pool120'))
        from annotation_strata120 import doctor_metadata
        annotations=doctor_metadata()
        if any(annotations[r['id']]['GT']!=r['GT'] for r in joint):
            raise ValueError('Original physician labels differ')
        masks={
            'first_round_unanimous':lambda r:annotations[r['id']]['first_round_unanimous'],
            'first_round_disagreement':lambda r:not annotations[r['id']]['first_round_unanimous'],
            'true_nonS_with_zero_initial_S_votes':lambda r:r['GT']!='Supported' and annotations[r['id']]['initial_supported_votes']==0}
        result['physician_strata']={name:dict(N=len(selected),
            vs107=paired(selected,b107,new,'label_only107'),vs120=paired(selected,b120,new,'full_pool120'))
            for name,predicate in masks.items() for selected in [[r for r in joint if predicate(r)]]}
    if a.scope=='screen160':
        s=result['panels']['all']['scores'];old=s['label_only107'];full=s['full_pool120'];cand=s['midpoint132']
        sc=lambda v:v['per_class']['Supported']['recall']*sum(r['GT']=='Supported' for r in joint)
        gain107=(cand['mcc']>=old['mcc']+.01 or cand['correct']>=old['correct']+2 or cand['false_S']<=old['false_S']-1)
        risk=(cand['false_S']<=full['false_S']-2 and cand['mcc']>=old['mcc'] and cand['correct']>=old['correct']-1 and sc(cand)>=sc(old)-1 and gain107)
        quality=(cand['mcc']>=full['mcc']+.015 and cand['false_S']<=full['false_S'])
        result.update(continue_=bool(len(joint)>=152 and (risk or quality)),risk_branch=bool(risk),quality_branch=bool(quality))
    out=ROOT/'outputs/132_midpoint_update';out.mkdir(parents=True,exist_ok=True)
    c.put(out/(a.scope+'.json'),result)
    c.putl(out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],midpoint132=new[i]['verdict'],midpoint_valid=new[i]['valid'],baseline107=b107[i]['verdict'],baseline120=b120[i]['verdict']) for i in target])
    lines=['# 132：107与120有效更新的固定中点','',
        '只做一次alpha=0.5，无新增训练；原107、120与作者历史预测均复用。自然与压力分开，mixed筛查集合不冒充自然分布。','',
        '|范围／模型|有效N|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for panel,d in result['panels'].items():
        n=len(groups[panel])
        for label,m in d['scores'].items():
            recalls='/'.join(f"{m['per_class'][g]['recall']*100:.2f}%" if any(r['GT']==g for r in groups[panel]) else '—' for g in LABELS)
            lines.append(f"|{panel}/{label}|{n}|{m['mcc']:.4f}|{m['percent_agreement']*100:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    lines+=['','|范围／参照|ΔMCC|Δ正确|Δfalse-S|S救回/误伤|NS救回/误伤|NA救回/误伤|false-S新增/避免|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for panel,d in result['panels'].items():
        if panel.startswith('same'):continue
        for reference in ('vs107','vs120'):
            v=d[reference];change=v['changes']
            classes='|'.join(f"{change['by_class'][g]['rescued']}/{change['by_class'][g]['harmed']}" for g in LABELS)
            lines.append(f"|{panel}/{v['reference_model']}|{v['delta_MCC']:+.4f}|{v['delta_correct']:+d}|{v['delta_false_S']:+d}|{classes}|{change['false_S_new']}/{change['false_S_avoided']}|")
    if a.scope=='selection1817':
        lines+=['','完整1817的患者配对区间（1000次患者重抽样，开发队列描述）：','']
        for reference in ('vs107','vs120'):
            v=result['panels']['all'][reference]
            if 'patient_bootstrap' not in v:continue
            lo,hi=v['patient_bootstrap']['metrics']['mcc']['ci95']
            lines.append(f"- 相对{v['reference_model']}：ΔMCC {v['delta_MCC']:+.4f}，95%区间[{lo:+.4f}, {hi:+.4f}]。")
        lines+=['','|原始医生标注分层|N|相对107 Δ正确/Δfalse-S|相对120 Δ正确/Δfalse-S|',
                '|---|---:|---:|---:|']
        for name,v in result['physician_strata'].items():
            x,y=v['vs107'],v['vs120']
            lines.append(f"|{name}|{v['N']}|{x['delta_correct']:+d}/{x['delta_false_S']:+d}|{y['delta_correct']:+d}/{y['delta_false_S']:+d}|")
        lines+=['','患者、来源、输入长度四分位和完整混淆矩阵均保留在JSON。分层仅作事后描述，不筛除有分歧标签或反过来调整模型。']
    lines+=['',f"覆盖：{len(joint)}/{len(target)}，无效{result['invalid_N']}，未补旧答案。",
        '配对类别救回／误伤、患者方向与来源见JSON。参数插值不等于低学习率重训，也没有证明医学推理机制。',
        '107使用104的标签prompt；作者式未微调9B只在103已有覆盖上列出，其thinking与输出预算不同。105缓存的未微调9B与当前104标签prompt一致，但缺失／无效仍保留，未新运行105。paper_r1始终是不同模型的作者历史参照。','']
    lines+=['方法来源：借鉴[WiSE-FT／Robust fine-tuning of zero-shot models](https://arxiv.org/abs/2109.01903)的权重插值思想；本轮锚点107也已微调，并非原论文的零样本模型，不能直接继承其视觉鲁棒性结论。','']
    if a.scope=='screen160':lines.insert(-1,'冻结继续条件：'+('达到，允许补到500。' if result['continue_'] else '未达到，停止当前中点。'))
    (out/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
    print(c.canonical(dict(scope=a.scope,continue_=result.get('continue_'),scores={k:{x:v[x] for x in ('mcc','correct','false_S','non_S')} for k,v in result['panels']['all']['scores'].items()})))


if __name__=='__main__':main()
