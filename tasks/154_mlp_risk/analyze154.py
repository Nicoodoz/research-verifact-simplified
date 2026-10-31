"""Evaluate actual existing117 scores as136 referral signals; no new fitting."""
from pathlib import Path
from collections import defaultdict
import json,sys,math,time
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,rows,save,score,five_table,markdown_table

def main():
    started=time.perf_counter();keys,pred,raw=assets();native=pred['claim_repeat136'];pool={i for i,g in native.items() if g=='Supported'}
    source={r['id']:r for r in rows(R/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl')}
    assert set(source)==set(keys) and all(r.get('valid') is True for r in source.values())
    for i,r in source.items():assert r['GT']==keys[i]['GT'] and str(r['sid'])==str(keys[i]['sid'])
    margin={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        for f in (R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136').glob('*.json'):
            r=read(f)
            if r['id'] in pool:margin[r['id']]=r['logit_S_minus_Not']
    assert set(margin)==pool and len(pool)==1451
    # Sum the two nonS outputs directly: p(S) was sometimes rounded to1.0 in float32.
    head={i:-(source[i]['probabilities']['Not Supported']+source[i]['probabilities']['Not Addressed']) for i in pool}
    assert all(math.isfinite(v) and -1.000001<=v<=0 for v in head.values())
    rankmargin={i:n+1 for n,i in enumerate(sorted(pool,key=lambda i:(margin[i],i)))}
    rankhead={i:n+1 for n,i in enumerate(sorted(pool,key=lambda i:(head[i],i)))}
    fusion={i:-(1/(60+rankmargin[i])+1/(60+rankhead[i])) for i in pool}
    groups=defaultdict(list)
    for i in pool:groups[str(keys[i]['sid'])].append(i)
    patient={}
    for group in groups.values():
        mm=[margin[i] for i in group]
        for i in group:patient[i]=(sum(v<margin[i] for v in mm)+.5*sum(v==margin[i] for v in mm))/len(mm)
    variants=dict(global_margin=margin,patient_rank=patient,mlp_nonS=head,margin_mlp_fusion=fusion)
    workloads=sorted({178,290,*[math.floor(len(pool)*q/100) for q in (0,5,10,20,30)]});results={};flags={}
    for name,values in variants.items():
        order=sorted(pool,key=lambda i:(values[i],i));results[name]={};flags[name]={}
        for k in workloads:
            review=set(order[:k]);auto=set(keys)-review;m=score(auto,native,keys);correctS=sum(keys[i]['GT']=='Supported' for i in review)
            results[name][str(k)]=dict(k=k,coverage=len(auto)/1817,intercepted_FS=k-correctS,residual_FS=m['false_S'],original_non_S=362,review_correct_S=correctS,auto_metrics=m)
            flags[name][str(k)]=sorted(review)
    patients=sorted({str(k['sid']) for k in keys.values()});audit={}
    for name in ('mlp_nonS','margin_mlp_fusion'):
        audit[name]={}
        for k in (178,290):
            old=set(flags['global_margin'][str(k)]);new=set(flags[name][str(k)]);counts=[]
            for sid in patients:
                group={i for i,r in keys.items() if str(r['sid'])==sid}
                a=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' and i not in old for i in group)
                b=sum(native[i]=='Supported' and keys[i]['GT']!='Supported' and i not in new for i in group)
                counts.append((b-a,sum(keys[i]['GT']!='Supported' for i in group)))
            draws=[]
            for seed in range(1000):
                chosen=np.random.RandomState(seed).choice(len(patients),len(patients),replace=True);denom=sum(counts[j][1] for j in chosen)
                if denom:draws.append(sum(counts[j][0] for j in chosen)/denom)
            audit[name][str(k)]=dict(delta_FS=results[name][str(k)]['residual_FS']-results['global_margin'][str(k)]['residual_FS'],CI=np.quantile(draws,[.025,.975]).tolist())
    baselines=five_table(keys,keys,pred,raw);output=dict(N=1817,predicted_S=1451,GT_used_for_new_fitting=False,new_training=False,new_GPU_calls=0,new_API_CNY=0,
        results=results,fixed_flag_patient_bootstrap=audit,five_baselines=baselines,extra107_prefill_calls_deployment=1451,
        source117='original unweighted MLP selectedepoch6; 1024train32 /730internal8',CPU_seconds=time.perf_counter()-started)
    O=R/'outputs/154_mlp_risk';save(O/'analysis.json',output);save(R/'.local_models/154_mlp_risk/review_flags.json',flags)
    lines=['# 154 mlp_risk：117原MLP作为136的辅助风险分数','',
        '只复用原117完整真实分数，无新训练或seed选择。136原标签与全量MCC不变；旧MLP分类成绩不替代本次送审评价。MLP基于107前缀表示和原32人1024训练、8人730内部选epoch6，不能称当前120同权重原生概率或独立校准。','',
        '|送审分数|送审|自动覆盖|截获FS/88|残留FS/原non-S|送审正确S|自动S FDR|自动MCC|自动PA|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,points in results.items():
        for k in (178,290):
            v=points[str(k)];m=v['auto_metrics'];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}/362|{v['review_correct_S']}|{m['S_FDR']:.2%}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|")
    lines+=['','mlp_nonS使用真实p(NS)+p(NA)，不使用LLM自报分数；softmax未校准。融合按两种风险排名1/(60+rank)等权求和，常数和权重未按GT搜索。全部预设曲线和患者区间保留，不把最佳点当部署阈值。','',
        '## 五条固定基线：共同有效ID','',markdown_table(baselines),'',
        f"新增GPU/API调用0，API费用¥0；CPU{output['CPU_seconds']:.2f}秒。部署至少需要原136判断1817次＋对其原S池1451次额外107表示prefill，再运行小MLP；约1.80次逻辑前向/命题，不能把CPU头时间充当完整推理时间。当前新增端到端部署的耗时、token回执及费用未记录，不为补表重跑基线。原107/136输入token与已有历史耗时见[集中成本](../141_two_demos/inference_cost.md)。",'',
        '20名患者均有历史开发暴露，不声称独立校准或CP保证；固定标记bootstrap只反映当前选择下患者组成不确定性。送审项未按已纠正计。原117既有MCC .6109、正确1578、FS92/362的分类收益与风险原样保留，当前不把标签替换给136或借用旧reason。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({n:{k:results[n][k]['residual_FS'] for k in ('178','290')} for n in results}))

if __name__=='__main__':main()
