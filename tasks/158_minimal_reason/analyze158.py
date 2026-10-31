"""Paired development comparison against151, with failures and cost retained."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,statistics
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'));sys.path.insert(0,str(R/'tasks/151_fixed_reason_transfer'))
from common146 import assets,read,rows,save,five_table,markdown_table
from reason_io151 import package_reason

def summarize(private,ids):
    inputs={r['id']:r for r in rows(private/'inputs.jsonl')};judgments={};raw={};counts=Counter();records={};length=[]
    for f in (private/'semantic_review').glob('*.json'):
        r=read(f)
        if r.get('valid') and 'judgments' in r:judgments.update(r['judgments'])
    for i in ids:
        r=read(private/'evidence/results/reason_base9b'/(i+'.json'));raw[i]=r;fixed=inputs[i]['fixed_verdict'];assert r['fixed_verdict']==fixed and r['label_changed'] is False
        key=hashlib.sha256(('reason_base9b|'+i).encode()).hexdigest()[:20];j=judgments.get(key);parsed=r.get('parsed')
        status=parsed['status'] if r['finish_reason']=='stop' and isinstance(parsed,dict) else 'invalid';counts[status]+=1
        consistent=None
        if status=='explained':
            length.append(len(parsed['reason'].split()));counts['over35words']+=length[-1]>35
            if j:
                consistent=j['stance']==fixed and not j['label_only'];counts['assessed']+=1;counts['consistent']+=consistent
            else:counts['unassessed']+=1
        package=package_reason(fixed,r['content'],inputs[i]['reference'],finish_reason=r['finish_reason'],reviewed_stance=j['stance'] if j else None,label_only=j['label_only'] if j else False)
        assert package['verdict']==fixed;counts[package['reason_status']]+=1;counts.update(package['flags'])
        records[i]=dict(id=i,fixed_verdict=fixed,status=status,AI_consistent=consistent,reviewed_stance=j['stance'] if j else None,reason_status=package['reason_status'],flags=package['flags'],reason_sha256=hashlib.sha256(parsed['reason'].encode()).hexdigest() if status=='explained' else None,word_count=len(parsed['reason'].split()) if status=='explained' else None,input_tokens=r['input_tokens'],output_tokens=r['output_tokens'],seconds=r['seconds'])
    return dict(N=len(ids),counts=dict(counts),median_words=statistics.median(length) if length else None,generation_seconds=sum(r['seconds'] for r in raw.values()),input_tokens=sum(r['input_tokens'] for r in raw.values()),output_tokens=sum(r['output_tokens'] for r in raw.values())),records

def main():
    P=R/'.local_models/158_minimal_reason';inputs={r['id']:r for r in rows(P/'inputs.jsonl')};ids=set(inputs);assert len(ids)==100
    keys,pred,rawbase=assets();assert all(inputs[i]['fixed_verdict']==pred['claim_repeat136'][i] for i in ids)
    old,rold=summarize(R/'.local_models/151_fixed_reason_transfer',ids);new,rnew=summarize(P,ids)
    paired=[i for i in ids if rold[i]['AI_consistent'] is not None and rnew[i]['AI_consistent'] is not None]
    agreement=dict(both_assessed_N=len(paired),old_consistent=sum(rold[i]['AI_consistent'] for i in paired),new_consistent=sum(rnew[i]['AI_consistent'] for i in paired),new_only_consistent=sum(rnew[i]['AI_consistent'] and not rold[i]['AI_consistent'] for i in paired),old_only_consistent=sum(rold[i]['AI_consistent'] and not rnew[i]['AI_consistent'] for i in paired))
    ledger=[r for r in rows(R/'.local_models/night_20261031/api_ledger.jsonl') if r.get('task')=='158_minimal_reason'];received=[r for r in ledger if r['event']=='received'];complete=read(P/'evidence/results/complete.json')
    budget=dict(GPU_worker_wall_seconds=complete['worker_wall_seconds'],GPU_worker_interval_CNY=complete['worker_wall_seconds']*1.58/3600,API_attempts=len(received),API_HTTP200=sum(r['http_status']==200 for r in received),API_unknown_N=sum(r['outcome_unknown'] for r in received),API_reserved_CNY=sum(r.get('reservation_CNY',0) for r in ledger),API_known_peak_CNY=sum(r.get('estimated_CNY_peak_no_discount') or 0 for r in received),API_input_tokens=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in received),API_output_tokens=sum((r.get('usage') or {}).get('completion_tokens',0) for r in received))
    five=five_table(ids,keys,pred,rawbase);O=R/'outputs/158_minimal_reason';save(O/'analysis.json',dict(task=158,N=100,old151=old,minimal_reason=new,paired_AI_direction=agreement,budget=budget,five_baselines=five,label_changes=0,GT_in_generation_or_review=False))
    with (O/'reason_status_sanitized.jsonl').open('w',encoding='utf-8') as f:
        for i in sorted(ids):f.write(json.dumps(dict(id=i,old151=rold[i],minimal_reason=rnew[i]),ensure_ascii=False)+'\n')
    lines=['# 158 minimal_reason：关键依据一句话与原文日期约束','',
        '配对151同批100条，按原136预测S/NS/NA分层60/14/26和ID哈希固定，不按GT或原理由失败取样。固定标签、完整目标reference、底座模型和greedy192均不变；只改理由指令为最小决定依据/最多35词，不添加非必要日期，必要日期逐字保留原文脱敏表示。不是新holdout。','',
        '|方案|解释|unable|格式失败|已盲审|正文方向一致|全100方向一致覆盖|日期标记|ready|中位词数|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,v in [('151原理由',old),('minimal_reason',new)]:
        c=v['counts'];lines.append(f"|{name}|{c.get('explained',0)}|{c.get('unable',0)}|{c.get('invalid',0)}|{c.get('assessed',0)}|{c.get('consistent',0)}|{c.get('consistent',0)/100:.2%}|{c.get('ISO_date_not_in_reference',0)}|{c.get('ready',0)}|{v['median_words']}|")
    lines+=['',f"双方均有有效AI盲审{agreement['both_assessed_N']}条，原方向一致{agreement['old_consistent']}、新{agreement['new_consistent']}；新独有一致{agreement['new_only_consistent']}、旧独有一致{agreement['old_only_consistent']}。缺失盲审单列，不当作一致或冲突。V4只看claim/reason，不给固定标签或GT；AI判读可能错，尤其NS/NA边界。",'',
        '日期检查是有限字符串检查，少写错误日期不等于其余医学事实全部认证；原文、每次理由与请求保留。原分类标签全部不变，原生MCC/PA未提高。','',
        '|方案|生成次数|输入tokens|输出tokens|生成秒|单条秒|','|---|---:|---:|---:|---:|---:|']
    for name,v in [('151同100条',old),('minimal_reason',new)]:lines.append(f"|{name}|100|{v['input_tokens']}|{v['output_tokens']}|{v['generation_seconds']:.2f}|{v['generation_seconds']/100:.3f}|")
    lines+=['',f"新增100条RTX4080 SUPER/BF16/batch1/16384上下文，worker含加载编译{budget['GPU_worker_wall_seconds']:.2f}秒、区间¥{budget['GPU_worker_interval_CNY']:.4f}；151旧100生成成本从原300缓存逐条复用，共享加载/盲审完整成本见151，不能伪造精确分摊。",'',
        f"新V4 thinking-high/max4096、并发2，尝试{budget['API_attempts']}次，HTTP200 {budget['API_HTTP200']}，未知{budget['API_unknown_N']}；已知usage未优惠原价估算¥{budget['API_known_peak_CNY']:.6f}、全部预留¥{budget['API_reserved_CNY']:.4f}保留。输入/输出{budget['API_input_tokens']}/{budget['API_output_tokens']} tokens。所有失败计费，不按HTTP200无效内容重发。",'',
        '## 固定五条分类参照','',markdown_table(five),'',
        '五基线直接复用缓存；历史费用缺项不补0，作者接口/输出预算与120/136差异保持披露。理由成本额外增加，不能用方向一致率替代三分类表现。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps(dict(old=old,new=new,paired=agreement,budget=budget),ensure_ascii=False))

if __name__=='__main__':main()
