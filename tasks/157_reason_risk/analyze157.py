"""Fixed functional-status priority, evaluated without new inference."""
from pathlib import Path
import json,sys,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,rows,save,score,five_table,markdown_table

def main():
    started=time.perf_counter();keys,pred,raw=assets();p=pred['claim_repeat136']
    statuses={r['id']:r for r in rows(R/'outputs/151_fixed_reason_transfer/reason_status_sanitized.jsonl')};ids=set(statuses);assert len(ids)==300
    pool={i for i in ids if p[i]=='Supported'};margin={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        for f in (R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136').glob('*.json'):
            r=read(f)
            if r['id'] in pool:margin[r['id']]=r['logit_S_minus_Not']
    assert set(margin)==pool
    def priority(i):
        r=statuses[i]
        if r['status'] in ('unable','invalid'):return 0
        if r['reviewed_stance'] is not None and not r['AI_review_consistent']:return 1
        return 2
    orders=dict(global_margin=sorted(pool,key=lambda i:(margin[i],i)),reason_status=sorted(pool,key=lambda i:(priority(i),margin[i],i)))
    native=score(ids,p,keys);results={};flags={}
    for name,order in orders.items():
        results[name]={};flags[name]={}
        for k in (30,48):
            review=set(order[:k]);auto=ids-review;m=score(auto,p,keys)
            results[name][str(k)]=dict(k=k,coverage=len(auto)/300,residual_FS=m['false_S'],intercepted_FS=native['false_S']-m['false_S'],review_correct_S=sum(keys[i]['GT']=='Supported' for i in review),original_non_S=sum(keys[i]['GT']!='Supported' for i in ids),auto_metrics=m)
            flags[name][str(k)]=sorted(review)
    baseline=five_table(ids,keys,pred,raw);prior=read(R/'outputs/151_fixed_reason_transfer/analysis.json')['budget']
    out=dict(task=157,N=300,native_S_N=len(pool),native_metrics=native,results=results,prior_reason_cost=prior,new_model_calls=0,new_API=0,CPU_seconds=time.perf_counter()-started,five_baselines=baseline,GT_used_for_rule=False,label_changes=0)
    O=R/'outputs/157_reason_risk';save(O/'analysis.json',out);save(R/'.local_models/157_reason_risk/review_flags.json',flags)
    lines=['# 157 reason_risk：理由状态与原生margin的固定组合','',
        f"固定151原300条，其中136预测S {len(pool)}条、原false-S {native['false_S']}。unable/生成失败→盲审非S或label-only→其余，组内按原margin；缺失盲审不当作冲突，日期问题不直接当原分类风险。GT仅用于以下计分。",'',
        '|方法|复核|自动覆盖|截获FS|残留FS|送审正确S|自动S FDR|自动MCC|自动PA|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,pts in results.items():
        for k in ('30','48'):
            v=pts[k];m=v['auto_metrics'];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}|{v['review_correct_S']}|{m['S_FDR']:.2%}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|")
    lines+=['','送审不计作已纠错，原生标签与全量MCC/PA不变。自动子集成绩不是全量提升；患者已有开发暴露，无独立校准或Conformal保证。','',
        '## 五条分类参照','',markdown_table(baseline),'',
        f"新增推理/API为0。部署完整理由成本不能省略：151生成{prior['generation_seconds']:.2f}秒、输入{prior['input_tokens']}、输出{prior['output_tokens']} tokens，worker区间¥{prior['GPU_worker_interval_CNY']:.4f}；盲审已知原价估算¥{prior['API_known_peak_CNY']:.6f}、预留¥{prior['API_reserved_CNY']:.4f}。完整窗口包含等待/准备/回传；历史费用缺失不补0。",'',
        '详细三类表现、false-S分母与功能成本见analysis.json。AI方向判断可能误判，不能把理由冲突直接当医生错误标签。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({n:{k:v['residual_FS'] for k,v in pts.items()} for n,pts in results.items()}))

if __name__=='__main__':main()
