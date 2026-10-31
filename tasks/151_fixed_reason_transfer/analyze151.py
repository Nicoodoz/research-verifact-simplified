"""Evaluate immutable-label short reasons and blinded stance assessment."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,statistics
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,rows,save,five_table,markdown_table,LABELS
from reason_io151 import package_reason

def main():
    P=R/'.local_models/151_fixed_reason_transfer';O=R/'outputs/151_fixed_reason_transfer'
    keys,pred,oldraw=assets();inputs={r['id']:r for r in rows(P/'inputs.jsonl')}
    raw={r['id']:r for r in (read(f) for f in (P/'evidence/results/reason_base9b').glob('*.json'))}
    assert len(inputs)==300 and set(inputs)==set(raw)
    judgments={};invalid_batches=[]
    for f in (P/'semantic_review').glob('*.json'):
        r=read(f)
        if 'expected_keys' not in r:continue
        if r.get('valid'):judgments.update(r['judgments'])
        else:invalid_batches.append(dict(batch=r['batch'],trials=r['trials']))
    counts=Counter();by={g:Counter() for g in LABELS};sanitized=[];words=[];private=[]
    for i,r in raw.items():
        fixed=inputs[i]['fixed_verdict'];assert fixed==pred['claim_repeat136'][i]==r['fixed_verdict'] and r['label_changed'] is False
        key=hashlib.sha256(('reason_base9b|'+i).encode()).hexdigest()[:20];j=judgments.get(key)
        parsed=r.get('parsed');ok=r['finish_reason']=='stop' and isinstance(parsed,dict)
        status=parsed['status'] if ok else 'invalid';counts[status]+=1;by[fixed][status]+=1
        consistent=None
        if status=='explained':
            words.append(len(parsed['reason'].split()));counts['over45words']+=words[-1]>45
            if j:
                consistent=j['stance']==fixed and not j['label_only'];counts['semantic_assessed']+=1
                counts['semantic_consistent']+=consistent;by[fixed]['semantic_assessed']+=1;by[fixed]['semantic_consistent']+=consistent
            else:counts['semantic_missing']+=1;by[fixed]['semantic_missing']+=1
        package=package_reason(fixed,r['content'],inputs[i]['reference'],finish_reason=r['finish_reason'],reviewed_stance=j['stance'] if j else None,label_only=j['label_only'] if j else False)
        assert package['verdict']==fixed
        counts['package_'+package['reason_status']]+=1;by[fixed]['package_'+package['reason_status']]+=1
        counts.update(package['flags'])
        private.append(dict(id=i,**package))
        sanitized.append(dict(id=i,fixed_verdict=fixed,label_changed=False,status=status,reviewed_stance=j['stance'] if j else None,AI_review_consistent=consistent,reason_status=package['reason_status'],flags=package['flags'],reason_sha256=hashlib.sha256(parsed['reason'].encode()).hexdigest() if status=='explained' else None,input_tokens=r['input_tokens'],output_tokens=r['output_tokens'],seconds=r['seconds']))
    api=[r for r in rows(R/'.local_models/night_20261031/api_ledger.jsonl') if r.get('task')=='151_fixed_reason_transfer']
    received=[r for r in api if r['event']=='received'];complete=read(P/'evidence/results/complete.json')
    budget=dict(GPU_worker_wall_seconds=complete['worker_wall_seconds'],GPU_worker_interval_CNY=complete['worker_wall_seconds']*1.58/3600,generation_seconds=sum(r['seconds'] for r in raw.values()),input_tokens=sum(r['input_tokens'] for r in raw.values()),output_tokens=sum(r['output_tokens'] for r in raw.values()),API_attempts=len(received),API_unknown_N=sum(r['outcome_unknown'] for r in received),API_HTTP200=sum(r['http_status']==200 for r in received),API_reserved_CNY=sum(r.get('reservation_CNY',0) for r in api),API_known_peak_CNY=sum(r.get('estimated_CNY_peak_no_discount') or 0 for r in received),API_input_tokens=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in received),API_output_tokens=sum((r.get('usage') or {}).get('completion_tokens',0) for r in received),API_seconds=sum(r['seconds'] for r in received))
    five=five_table(inputs,keys,pred,oldraw)
    out=dict(task=151,N=300,original_label_changes=0,GT_in_generation_or_review=False,counts=dict(counts),by_fixed_verdict={g:dict(v) for g,v in by.items()},median_reason_words=statistics.median(words),budget=budget,invalid_review_batches=invalid_batches,five_baselines=five)
    save(O/'analysis.json',out)
    for file,data in [(O/'reason_status_sanitized.jsonl',sanitized),(P/'packaged_reasons.jsonl',private)]:
        with file.open('w',encoding='utf-8') as f:
            for row in data:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    c=counts
    lines=['# 151 fixed_reason_transfer：固定136标签的新300条理由','',
        f"300条按ID哈希选取，排除147原60条；生成和盲审均不输入医生GT。原136预测标签全部保留，未为理由改标签。greedy192的未微调9B生成{c['explained']}/300条解释、{c['unable']}条unable、{c['invalid']}条格式/结束失败。解释中位{statistics.median(words)}词，超过45词{c['over45words']}条。",'',
        f"V4只看claim＋reason判读正文立场，已判读{c['semantic_assessed']}/{c['explained']}条，其中{c['semantic_consistent']}条与固定标签方向一致（{c['semantic_consistent']/c['semantic_assessed']:.2%}）；按全部300条计算的方向一致覆盖为{c['semantic_consistent']/300:.2%}。{c['semantic_missing']}条解释缺失有效盲审，单列且不按一致计。",'',
        f"接口保留原标签，并将unable、格式失败、方向冲突/模糊、明确ISO日期不在完整reference的解释分别标记。ready {c['package_ready']}、needs_review {c['package_needs_review']}、direction_unreviewed {c['package_direction_unreviewed']}、unable {c['package_unable']}、generation_failed {c['package_generation_failed']}。ISO日期标记{c['ISO_date_not_in_reference']}条；它只捕捉明确字符串问题，不证明其余理由医学真实。",'',
        '|固定标签|样本|解释|unable|已盲审|方向一致|ready|','|---|---:|---:|---:|---:|---:|---:|']
    for g,v in by.items():lines.append(f"|{g}|{sum(inputs[i]['fixed_verdict']==g for i in inputs)}|{v['explained']}|{v['unable']}|{v['semantic_assessed']}|{v['semantic_consistent']}|{v['package_ready']}|")
    lines+=['','ready表示通过当前格式、AI方向和有限日期检查，仍是AI辅助解释；不是医生认证。检查的是解释正文含义，不能靠标签词匹配。原理由、无法生成项和盲审原回执全部私有保留。',
        '4个HTTP200批次耗尽4096输出上限，没有按内容重发；HTTP0有限重试计入全部费用，未知预留保留。原生分类MCC/PA不因增加理由而提高。','',
        '## 实测成本','',f"理由生成输入{budget['input_tokens']}、输出{budget['output_tokens']} tokens；生成{budget['generation_seconds']:.2f}秒、每条{budget['generation_seconds']/300:.3f}秒，worker含加载/编译{budget['GPU_worker_wall_seconds']:.2f}秒、区间约¥{budget['GPU_worker_interval_CNY']:.4f}。RTX4080 SUPER/BF16/batch1/16384上下文，完整目标reference。",'',
        f"V4 thinking-high/max4096、并发2，尝试{budget['API_attempts']}次，HTTP200 {budget['API_HTTP200']}、HTTP0未知{budget['API_unknown_N']}；已知usage忙时未优惠估算¥{budget['API_known_peak_CNY']:.6f}，全部预留¥{budget['API_reserved_CNY']:.4f}保留。API输入{budget['API_input_tokens']}、输出{budget['API_output_tokens']} tokens，尝试秒数合计{budget['API_seconds']:.2f}（并发合计不是墙钟）。生成与worker不重复计费，准备/等待/回传计入全GPU窗口。",'',
        '## 固定五基线：同300条的共同有效ID','',markdown_table(five),'',
        '五条分类参照均复用缓存；作者两臂为作者接口/768输出，120/136为104体系/384输出，paper_r1为历史R1，费用缺项不补0。理由生成额外成本与已有分类成本相加，不能以reason方向检查替代分类评价。','',
        '结论：保留固定标签条件生成的理由功能，交付显式失败/需复核状态；不强编、不改标签。后续可围绕实际方向冲突和无法解释项作有限改进，不需把全量医学审查作为前置条件。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps(dict(counts=dict(counts),by=out['by_fixed_verdict'],budget=budget),ensure_ascii=False))

if __name__=='__main__':main()
