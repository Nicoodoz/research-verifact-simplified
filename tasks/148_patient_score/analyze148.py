"""Two unsupervised patient normalizations of existing margins; no fitted labels."""
from pathlib import Path
from collections import defaultdict
import json,math,statistics,sys,time
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,score,five_table,markdown_table
import numpy as np

def main():
    started=time.perf_counter();keys,pred,raw=assets();p=pred['claim_repeat136'];pool={i for i,g in p.items() if g=='Supported'}
    scores={}
    roots=[R/'.local_models/144_native_confidence'/scope/'evidence/results' for scope in ['pilot','screen160','old500_fixpath','full1817']]
    for root in roots:
        for file in (root/'claim_repeat136').glob('*.json'):
            r=read(file)
            if r['id'] not in pool:continue
            if r['id'] in scores and scores[r['id']]!=r['logit_S_minus_Not']:raise ValueError('Conflicting margin')
            scores[r['id']]=r['logit_S_minus_Not']
    assert set(scores)==pool and len(pool)==1451 and all(math.isfinite(v) for v in scores.values())
    groups=defaultdict(list)
    for i in pool:groups[str(keys[i]['sid'])].append(i)
    rank={};center={}
    for sid,ids in groups.items():
        values=[scores[i] for i in ids];median=statistics.median(values);iqr=float(np.quantile(values,.75)-np.quantile(values,.25)) or 1.
        # Midranks preserve equal scores; ID breaks ties only at final referral.
        for i in ids:
            rank[i]=(sum(v<scores[i] for v in values)+.5*sum(v==scores[i] for v in values))/len(ids)
            center[i]=(scores[i]-median)/iqr
    variants={'global_margin':scores,'patient_rank':rank,'patient_center':center}
    workloads=sorted({178,290,*[math.floor(len(pool)*q/100) for q in (0,5,10,20,30)]})
    results={};flags={}
    for name,values in variants.items():
        order=sorted(pool,key=lambda i:(values[i],i));results[name]={};flags[name]={}
        for k in workloads:
            review=set(order[:k]);automatic=set(keys)-review;trueS=sum(keys[i]['GT']=='Supported' for i in review)
            m=score(automatic,p,keys)
            results[name][str(k)]=dict(k=k,auto_N=len(automatic),coverage=len(automatic)/len(keys),
                intercepted_FS=k-trueS,review_correct_S=trueS,residual_FS=m['false_S'],original_non_S=362,
                auto_metrics=m,patients_with_reviews=len({keys[i]['sid'] for i in review}),
                random_expected_intercepted_FS=88*k/len(pool))
            flags[name][str(k)]=sorted(review)
    baseline=five_table(keys,keys,pred,raw)
    output=dict(N=1817,predicted_S_N=1451,patients=20,GT_used_for_score_construction=False,
                label_changes=0,new_GPU_forwards=0,new_API_calls=0,results=results,five_baselines=baseline,
                CPU_seconds=time.perf_counter()-started)
    O=R/'outputs/148_patient_score';save(O/'analysis.json',output)
    save(R/'.local_models/148_patient_score/review_flags.json',flags)
    lines=['# 148 patient_score：患者内归一的等工作量回顾','',
           '两种归一均不使用GT拟合；GT只评价。原生136标签与全量MCC不变。20名患者均有历史开发暴露，无独立校准或CP保证。','',
           '|方法|送审|自动覆盖|截获FS/88|残留FS/原non-S|送审正确S|自动S FDR|自动MCC|自动PA|',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,points in results.items():
        for k in (178,290):
            v=points[str(k)];m=v['auto_metrics']
            lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}/362|{v['review_correct_S']}|{m['S_FDR']:.2%}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|")
    lines+=['','自动子集ID不同，MCC/PA只描述各自自动子集，不能冒充全量分类提升。所有固定曲线点及三类表现保留在analysis.json；送审项未按已纠错计。','',
            '## 固定五基线（共同有效ID）','',markdown_table(baseline),'',
            '五基线直接复用；作者两臂有invalid，因此共同分母1793，不能与1817直接相减。paper_r1为作者历史R1；两作者9B为768输出预算，120/136为104体系384输出预算。107不进入常规主表。','',
            f"新增推理0次、API费用¥0；CPU分析{output['CPU_seconds']:.2f}秒。排序部署仅需已有分数和患者分组，实际取分成本仍按144记录，不能把缓存分析免费当部署免费。GPU开机租金仍在本窗口账本累计。历史成本缺项未补0。",'']
    for name in ('patient_rank','patient_center'):
        changes={k:results[name][str(k)]['residual_FS']-results['global_margin'][str(k)]['residual_FS'] for k in (178,290)}
        lines.append(f"{name}相对global_margin残留FS变化（178/290送审）：{changes[178]:+d}/{changes[290]:+d}；同工作量下送审正确S随之同幅变化。")
    (O/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({n:{k:results[n][k]['residual_FS'] for k in ('178','290')} for n in results}))

if __name__=='__main__':main()
