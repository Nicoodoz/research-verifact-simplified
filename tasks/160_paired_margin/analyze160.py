"""One frozen equal-rank two-prompt risk combination using cached scores."""
from pathlib import Path
import sys,json,time,math
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,score,five_table,markdown_table,cost

def midranks(values):
    allv=list(values.values());n=len(allv)
    return {i:(sum(x<v for x in allv)+.5*sum(x==v for x in allv))/n for i,v in values.items()}

def main():
    started=time.perf_counter();keys,pred,raw=assets();p=pred['claim_repeat136'];p120=pred['full_pool120'];pool={i for i,v in p.items() if v=='Supported'}
    margins={'claim_repeat136':{},'full_pool120':{}}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        root=R/'.local_models/144_native_confidence'/scope/'evidence/results'
        for arm in margins:
            for f in (root/('native120' if arm=='full_pool120' else arm)).glob('*.json'):
                r=read(f);i=r['id'];v=r['logit_S_minus_Not']
                if i in margins[arm]:assert margins[arm][i]==v
                margins[arm][i]=v
    assert pool<=set(margins['claim_repeat136'])
    both={i for i in pool if p120[i]=='Supported'};disagree=pool-both
    assert both<=set(margins['full_pool120'])
    ranks={name:midranks({i:v for i,v in values.items() if pred[name][i]=='Supported'}) for name,values in margins.items()}
    m=margins['claim_repeat136'];fusion={i:(ranks['claim_repeat136'][i]+ranks['full_pool120'][i])/2 for i in both}
    orders=dict(global_margin=sorted(pool,key=lambda i:(m[i],i)),disagree_margin=sorted(pool,key=lambda i:(0 if i in disagree else 1,m[i],i)),paired_rank=sorted(pool,key=lambda i:(0 if i in disagree else 1,m[i] if i in disagree else fusion[i],i)))
    cached=read(R/'.local_models/148_patient_score/review_flags.json');results={};flags={};workloads=sorted({0,178,290,*[math.floor(len(pool)*q/100) for q in (5,10,20,30)]})
    for name,order in orders.items():
        results[name]={};flags[name]={}
        for k in workloads:
            review=set(order[:k]);auto=set(keys)-review;a=score(auto,p,keys)
            results[name][str(k)]=dict(k=k,coverage=len(auto)/1817,intercepted_FS=88-a['false_S'],residual_FS=a['false_S'],original_non_S=362,review_correct_S=sum(keys[i]['GT']=='Supported' for i in review),auto_metrics=a)
            flags[name][str(k)]=sorted(review)
    for k in (178,290):assert flags['global_margin'][str(k)]==sorted(cached['global_margin'][str(k)])
    five=five_table(keys,keys,pred,raw);baseline148=read(R/'outputs/148_patient_score/analysis.json')['results']['patient_rank']
    out=dict(task=160,N=1817,predicted_S_N=len(pool),both_S_N=len(both),disagree_N=len(disagree),results=results,patient_rank_reference=baseline148,five_baselines=five,extra_120_view_cost=cost(pool,raw['full_pool120']),new_GPU_calls=0,new_API=0,GT_used_for_rule=False,label_changes=0,CPU_seconds=time.perf_counter()-started)
    O=R/'outputs/160_paired_margin';save(O/'analysis.json',out);save(R/'.local_models/160_paired_margin/review_flags.json',flags)
    lines=['# 160 paired_margin：既有两提示视角的固定风险组合','',
        f"136预测S {len(pool)}条，其中120判非S {len(disagree)}条。两视角同一120权重，分别使用各自原输入与原生分数。disagree_margin先120分歧再136 margin；paired_rank只把其余共同S改为两视角中位秩的固定等权平均。GT只用于以下计分，没有重训、调权或改原136标签。",'',
        '|方法|复核|自动覆盖|截获FS/88|残留FS/362|正确S送审|自动S FDR|自动MCC|自动PA|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,pts in dict(results,patient_rank148=baseline148).items():
        for k in ('178','290'):
            v=pts[k];a=v['auto_metrics'];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}|{v['review_correct_S']}|{a['S_FDR']:.2%}|{a['mcc']:.4f}|{a['percent_agreement']:.2%}|")
    lines+=['','全量标签、MCC和PA不变；送审不等于纠错，自动子集成绩不是全量提升。20名患者已有开发暴露，无独立校准或Conformal保证。patient_rank需要同患者一批命题，不能当单条模式。','',
        '## 固定五条分类参照','',markdown_table(five),'',
        '新增GPU/API调用0，CPU时间见analysis.json。部署需136原生判定外，在其预测S上新增最多1451个120视角prefill，逻辑判定总数3268/1817约1.80次/命题；同次只读捕获margin避免额外取分调用。历史120子集输入/输出tokens和时延的记录覆盖见analysis.json，缺项不补0，实际联合部署尚未计时。原模型硬件、batch和生成设置差异仍按120/136原报告。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({n:{k:pts[k]['residual_FS'] for k in ('178','290')} for n,pts in results.items()}))

if __name__=='__main__':main()
