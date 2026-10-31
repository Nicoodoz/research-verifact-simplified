"""Equal-workload selective-risk evaluation of fixed complete-path scores."""
from pathlib import Path
from collections import defaultdict
import json,sys,math,time
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,score,five_table,markdown_table

def main():
    P=R/'.local_models/150_label_path_risk/evidence';done=read(P/'results/complete.json');assert done['N']==352
    keys,pred,raw=assets();native=pred['claim_repeat136'];ids={i for i,k in keys.items() if k['old_panel'] in ('natural','pressure')}
    pool={i for i in ids if native[i]=='Supported'};assert len(ids)==500 and len(pool)==352
    new={r['id']:r for r in (read(p) for p in (P/'results/scores').glob('*.json'))};assert set(new)==pool
    margins={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        root=R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136'
        for path in root.glob('*.json'):
            r=read(path)
            if r['id'] in pool:margins[r['id']]=r['logit_S_minus_Not']
    assert set(margins)==pool
    groups=defaultdict(list)
    for i in pool:groups[str(keys[i]['sid'])].append(i)
    patient_rank={}
    for group in groups.values():
        values=[margins[i] for i in group]
        for i in group:patient_rank[i]=(sum(v<margins[i] for v in values)+.5*sum(v==margins[i] for v in values))/len(values)
    variants=dict(binary_margin=margins,patient_rank=patient_rank,legal_odds={i:r['legal_odds'] for i,r in new.items()},complete_S_logP={i:r['complete_S_logP'] for i,r in new.items()})
    workloads=sorted({50,80,*[math.floor(len(pool)*q/100) for q in (0,5,10,20,30)]});results={};flags={}
    for name,values in variants.items():
        order=sorted(pool,key=lambda i:(values[i],i));results[name]={};flags[name]={}
        for k in workloads:
            review=set(order[:k]);auto=ids-review;m=score(auto,native,keys)
            correctS=sum(keys[i]['GT']=='Supported' for i in review)
            results[name][str(k)]=dict(k=k,auto_N=len(auto),coverage=len(auto)/500,intercepted_FS=k-correctS,
                residual_FS=m['false_S'],original_non_S=179,review_correct_S=correctS,auto_metrics=m,
                natural_residual_FS=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' for i in auto if keys[i]['old_panel']=='natural'),
                pressure_residual_FS=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' for i in auto if keys[i]['old_panel']=='pressure'))
            flags[name][str(k)]=sorted(review)
    patients=sorted({str(keys[i]['sid']) for i in ids});audit={}
    for name in ('legal_odds','complete_S_logP','patient_rank'):
        audit[name]={}
        for k in (50,80):
            old=set(flags['binary_margin'][str(k)]);newflags=set(flags[name][str(k)]);counts=[]
            for sid in patients:
                group={i for i in ids if str(keys[i]['sid'])==sid}
                a=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' and i not in old for i in group)
                b=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' and i not in newflags for i in group)
                counts.append((b-a,sum(keys[i]['GT']!='Supported' for i in group)))
            draws=[]
            for seed in range(1000):
                selected=np.random.RandomState(seed).choice(len(patients),len(patients),replace=True);denom=sum(counts[j][1] for j in selected)
                if denom:draws.append(sum(counts[j][0] for j in selected)/denom)
            audit[name][str(k)]=dict(delta_FS=results[name][str(k)]['residual_FS']-results['binary_margin'][str(k)]['residual_FS'],
                fixed_flag_patient_bootstrap_CI=np.quantile(draws,[.025,.975]).tolist())
    costs=dict(N=352,actual_forward_calls=sum(r['forward_calls'] for r in new.values()),
        actual_forward_input_tokens=sum(r['actual_forward_input_tokens'] for r in new.values()),
        projected_answer_positions=sum(r['answer_positions_projected'] for r in new.values()),
        generated_tokens=0,score_seconds=sum(r['seconds'] for r in new.values()),worker_wall_seconds=done['worker_wall_seconds'],
        mean_score_seconds_per_scored_S=sum(r['seconds'] for r in new.values())/352,
        added_seconds_per_all500=sum(r['seconds'] for r in new.values())/500,
        worker_interval_CNY=done['worker_wall_seconds']*1.58/3600,new_API_calls=0,new_API_CNY=0)
    baselines=five_table(ids,keys,pred,raw);O=R/'outputs/150_label_path_risk'
    save(O/'analysis.json',dict(N=500,predicted_S=352,GT_used_for_score_construction=False,label_changes=0,results=results,fixed_flag_audit=audit,costs=costs,five_baselines=baselines))
    save(R/'.local_models/150_label_path_risk/review_flags.json',flags)
    with (O/'scores_sanitized.jsonl').open('w',encoding='utf-8') as file:
        for i in sorted(pool):file.write(json.dumps(dict(id=i,binary_margin=margins[i],patient_rank=patient_rank[i],legal_odds=new[i]['legal_odds'],complete_S_logP=new[i]['complete_S_logP'],seconds=new[i]['seconds'],forward_calls=3,actual_forward_input_tokens=new[i]['actual_forward_input_tokens']),ensure_ascii=False)+'\n')
    lines=['# 150 label_path_risk：完整合法标签路径的风险排序','',
        '原500的136支持池352条全部完成；1056次新forward，未生成或更改任何原标签。使用106/113已有评分算子，不包装成新算法。只比较等复核负担下的风险，不把自动子集指标当原生分类提升。','',
        '|评分|送审|自动覆盖|截获FS/48|残留FS/原non-S|送审正确S|自动S FDR|自动MCC|自动PA|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,points in results.items():
        for k in (50,80):
            v=points[str(k)];m=v['auto_metrics'];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}/179|{v['review_correct_S']}|{m['S_FDR']:.2%}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|")
    lines+=['','binary_margin直接复用144。patient_rank按当前500的各患者支持池计算，不使用GT；它与148全1817的归一/送审集合不同，不混分母。legal_odds是S完整路径logP减NS/NA路径logsumexp，complete_S_logP只用S完整路径似然；均不称已校准正确概率。', '',
        '## 五条固定基线：原500共同有效ID','',markdown_table(baselines),'',
        '五基线复用旧分类；作者两9B invalid单列形成共同子集，不能与500送审表直接相减。paper_r1为作者历史R1；作者9B用作者提示/768输出，120/136为104体系/384输出。','',
        '## 实测新增成本','',
        f"352条支持样本×3=1056次完整forward，实际forward输入tokens {costs['actual_forward_input_tokens']}，标签答案投影位置{costs['projected_answer_positions']}，生成tokens 0（不是API免费推理）。评分{costs['score_seconds']:.2f}秒，worker含加载/编译墙钟{costs['worker_wall_seconds']:.2f}秒，区间租金估算¥{costs['worker_interval_CNY']:.4f}；原500均摊新增{costs['added_seconds_per_all500']:.3f}秒/条。API新增0。准备、排队和回传继续计入全窗口，不与这些区间重复相加。",'',
        '当前完整路径实现需3次额外prefill/样本；即使complete_S_logP有效，S单路径优化的真实部署耗时也尚未单独测量，不能把原3路实测除以3冒充新实测。144的同次捕获只做过12对工程检查，不宣称零开销。','']
    for name in ('legal_odds','complete_S_logP','patient_rank'):
        changes=[audit[name][str(k)]['delta_FS'] for k in (50,80)]
        lines.append(f"{name}相对binary_margin的残留FS变化（50/80送审）：{changes[0]:+d}/{changes[1]:+d}。")
    lines+=['','所有预设曲线、自动子集三类precision/recall/F1、Macro-F1、混淆矩阵、自然/压力剩余FS与固定标记患者bootstrap均在analysis.json保留。20名历史开发患者、原500面板，不声称独立校准或CP保证；送审未算已纠错。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({n:{k:results[n][k]['residual_FS'] for k in ('50','80')} for n in results}))

if __name__=='__main__':main()
