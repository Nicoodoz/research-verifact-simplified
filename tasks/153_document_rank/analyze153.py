"""Check document-proxy normalization without training on evaluation labels."""
from pathlib import Path
from collections import defaultdict
import json,sys,math,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,score,five_table,markdown_table

def main():
    started=time.perf_counter();keys,pred,raw=assets();native=pred['claim_repeat136'];pool={i for i,g in native.items() if g=='Supported'};margin={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        for f in (R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136').glob('*.json'):
            r=read(f)
            if r['id'] in pool:margin[r['id']]=r['logit_S_minus_Not']
    assert set(margin)==pool and len(pool)==1451
    rankings={};sizes={}
    for name,groupkey in [('patient_rank',lambda i:(str(keys[i]['sid']),)),('document_rank',lambda i:(str(keys[i]['sid']),keys[i]['author']))]:
        groups=defaultdict(list)
        for i in pool:groups[groupkey(i)].append(i)
        values={}
        for group in groups.values():
            mm=[margin[i] for i in group]
            for i in group:values[i]=(sum(v<margin[i] for v in mm)+.5*sum(v==margin[i] for v in mm))/len(mm)
        rankings[name]=values;sizes[name]=sorted(len(g) for g in groups.values())
    variants=dict(global_margin=margin,**rankings);workloads=sorted({178,290,*[math.floor(len(pool)*q/100) for q in (0,5,10,20,30)]});results={}
    for name,values in variants.items():
        order=sorted(pool,key=lambda i:(values[i],i));results[name]={}
        for k in workloads:
            review=set(order[:k]);auto=set(keys)-review;m=score(auto,native,keys);correctS=sum(keys[i]['GT']=='Supported' for i in review)
            byauthor={a:dict(review=sum(keys[i]['author']==a for i in review),intercepted_FS=sum(keys[i]['author']==a and keys[i]['GT']!='Supported' for i in review)) for a in ('human','llm')}
            results[name][str(k)]=dict(k=k,coverage=len(auto)/1817,intercepted_FS=k-correctS,residual_FS=m['false_S'],original_non_S=362,review_correct_S=correctS,auto_metrics=m,by_author=byauthor)
    baseline=five_table(keys,keys,pred,raw);output=dict(N=1817,GT_used_for_ranking=False,document_group_proxy='sid x author; actualdocumentID not verified',group_sizes=sizes,results=results,five_baselines=baseline,CPU_seconds=time.perf_counter()-started,new_GPU_calls=0,new_API_CNY=0)
    O=R/'outputs/153_document_rank';save(O/'analysis.json',output)
    lines=['# 153 document_rank：单文档分组代理的风险排序','',
        '只用原136标签、144margin及分组元数据；GT只评价。文档分组代理为sid×author，未宣称已核对真实文档ID；部署须使用真实document_id。全量原标签和MCC不变，送审不等于纠错。','',
        '|分数|送审|自动覆盖|截获FS/88|残留FS/原non-S|送审正确S|自动S FDR|', '|---|---:|---:|---:|---:|---:|---:|']
    for name,points in results.items():
        for k in (178,290):
            v=points[str(k)];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}/362|{v['review_correct_S']}|{v['auto_metrics']['S_FDR']:.2%}|")
    lines+=['','## 五条固定基线：共同有效ID','',markdown_table(baseline),'',
        f"新增GPU/API调用0，API费用¥0；CPU{output['CPU_seconds']:.2f}秒，开机租金继续按全窗口记账。真实取分成本仍由144承担，缓存免费分析不是部署免费。历史基线费用未记录，不补0；作者invalid造成共同1793分母，不能与上方1817直接相减。",'',
        '完整三类表现、自动子集MCC/PA、分组大小、human/LLM送审构成与全部固定曲线见analysis.json。只有20名已暴露开发患者，不声称独立校准、CP或单命题流式保证。','']
    changes={str(k):results['document_rank'][str(k)]['residual_FS']-results['patient_rank'][str(k)]['residual_FS'] for k in (178,290)}
    lines.append('document_rank相对patient_rank的残留FS变化（178/290）：'+str(changes)+'。')
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8');print(json.dumps({n:{k:results[n][k]['residual_FS'] for k in ('178','290')} for n in results}))

if __name__=='__main__':main()
