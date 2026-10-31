"""Fixed-label rationale coverage, blinded stance checks, and actual costs."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib,statistics,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,rows,save,five_table,markdown_table,LABELS

def main():
    P=R/'.local_models/147_fixed_reason';keys,pred,oldraw=assets();inputs={r['id']:r for r in rows(P/'inputs.jsonl')}
    assert len(inputs)==60 and all(r['fixed_verdict']==pred['claim_repeat136'][i] for i,r in inputs.items())
    judgments={};review_files=[]
    for file in (P/'semantic_review').glob('*.json'):
        r=read(file)
        if 'expected_keys' not in r:continue
        review_files.append(r)
        if r.get('valid'):judgments.update(r['judgments'])
    arms={};sanitized=[]
    date_flags=read(P/'literal_date_flags.json') if (P/'literal_date_flags.json').exists() else []
    date_flag_keys={(r['arm'],r['id']) for r in date_flags}
    for arm in ('reason120','reason_base9b'):
        raw={r['id']:r for r in (read(f) for f in (P/'evidence/results'/arm).glob('*.json'))}
        assert set(raw)==set(inputs)
        counts=Counter();by={g:Counter() for g in LABELS};tokensin=[];tokensout=[];seconds=[];wordcounts=[]
        for i,r in raw.items():
            fixed=inputs[i]['fixed_verdict'];assert r['fixed_verdict']==fixed and r['label_changed'] is False
            counts['attempts']+=1;by[fixed]['attempts']+=1;tokensin.append(r['input_tokens']);tokensout.append(r['output_tokens']);seconds.append(r['seconds'])
            parsed=r.get('parsed');ok=r['finish_reason']=='stop' and isinstance(parsed,dict)
            status=parsed['status'] if ok else 'invalid'
            counts[status]+=1;by[fixed][status]+=1
            semantic=None;consistent=None;key=hashlib.sha256((arm+'|'+i).encode()).hexdigest()[:20]
            if status=='explained':
                counts['literal_ISO_date_flagged']+=(arm,i) in date_flag_keys
                words=len(parsed['reason'].split());wordcounts.append(words);counts['over45words']+=words>45
                semantic=judgments.get(key)
                if semantic:
                    consistent=semantic['stance']==fixed and not semantic['label_only']
                    counts['semantic_assessed']+=1;by[fixed]['semantic_assessed']+=1
                    counts['semantic_consistent']+=consistent;by[fixed]['semantic_consistent']+=consistent
                    counts['label_only']+=semantic['label_only'];counts['ambiguous']+=semantic['stance']=='Ambiguous'
                else:counts['semantic_missing']+=1;by[fixed]['semantic_missing']+=1
            if consistent and (arm,i) not in date_flag_keys:counts['passed_direction_and_date_checks']+=1
            sanitized.append(dict(id=i,arm=arm,fixed_verdict=fixed,label_changed=False,status=status,
                reason_sha256=hashlib.sha256(parsed['reason'].encode()).hexdigest() if status=='explained' else None,
                reviewed_stance=semantic['stance'] if semantic else None,reviewed_label_only=semantic['label_only'] if semantic else None,
                AI_review_consistent=consistent,literal_ISO_date_flagged=(arm,i) in date_flag_keys,input_tokens=r['input_tokens'],output_tokens=r['output_tokens'],seconds=r['seconds']))
        arms[arm]=dict(counts=dict(counts),by_fixed_verdict={g:dict(v) for g,v in by.items()},
            input_tokens=sum(tokensin),output_tokens=sum(tokensout),generation_seconds=sum(seconds),mean_seconds=statistics.mean(seconds),
            median_reason_words=statistics.median(wordcounts) if wordcounts else None,
            explained_coverage=counts['explained']/60,
            AI_direction_agreement_on_assessed=counts['semantic_consistent']/counts['semantic_assessed'] if counts['semantic_assessed'] else None,
            AI_direction_coverage_lower_bound=counts['semantic_consistent']/60)
    ledger=rows(R/'.local_models/night_20261031/api_ledger.jsonl');api=[r for r in ledger if r.get('task')=='147_fixed_reason']
    received=[r for r in api if r['event']=='received'];budget=dict(API_attempts=len(received),API_HTTP200=sum(r['http_status']==200 for r in received),
        API_unknown_N=sum(r['outcome_unknown'] for r in received),API_reserved_CNY=sum(r.get('reservation_CNY',0) for r in api),
        API_known_usage_estimate_peak_CNY=sum(r.get('estimated_CNY_peak_no_discount') or 0 for r in received),
        API_seconds=sum(r['seconds'] for r in received),API_cap_CNY=80)
    runtime=read(P/'evidence/results/runtime.json');complete=read(P/'evidence/results/complete.json')
    wall=complete['worker_wall_seconds'];budget['GPU_worker_wall_seconds']=wall;budget['GPU_worker_interval_CNY']=wall*1.58/3600
    five=five_table(inputs,keys,pred,oldraw)
    result=dict(task=147,N_per_arm=60,labels_frozen_from_136=True,GT_in_generation_or_review_input=False,original_label_changes=0,
        arms=arms,budget=budget,five_baselines=five,review_model='deepseek-v4-flash-0731 thinking-high',
        semantic_review_limitation='AI-assisted blinded stance assessment; not medical truth certification; NS/NA boundary and reviewer mistakes remain possible')
    O=R/'outputs/147_fixed_reason';save(O/'analysis.json',result)
    with (O/'reason_status_sanitized.jsonl').open('w',encoding='utf-8') as file:
        for row in sanitized:file.write(json.dumps(row,ensure_ascii=False)+'\n')
    lines=['# 147 fixed_reason：固定136标签后的简短理由','',
        '两种理由生成器各60条；S/NS/NA原预测各20条，按ID哈希固定，既不输入医生GT也不改变原136标签。输出仅追加reason或显式unable；这是功能评价，原生分类成绩保持。','',
        '|理由生成器|尝试|格式失败|产出reason|unable|已盲审|正文方向一致/已盲审|盲审方向一致/全部60|中位词数|',
        '|---|---:|---:|---:|---:|---:|---|---|---:|']
    for arm,v in arms.items():
        c=v['counts'];lines.append(f"|{arm}|60|{c.get('invalid',0)}|{c.get('explained',0)}|{c.get('unable',0)}|{c.get('semantic_assessed',0)}|{c.get('semantic_consistent',0)}/{c.get('semantic_assessed',0)}|{v['AI_direction_coverage_lower_bound']:.2%}|{v['median_reason_words']}|")
    lines+=['','独立V4判读输入为claim＋reason，不给固定标签或GT；结果为AI辅助正文立场检查。不能用标签词机械匹配，也不把盲审误差、NS/NA边界问题或医学真实性混作已解决。原始理由与全部请求/回执私有保存；缺失判读不按一致计算，unable不强编。','',
        '进一步的免费原文匹配发现：reason120有1条、reason_base9b有3条解释出现reference中不存在的完整ISO日期，全部保留并标记需复核，不强编或静默修正。该检查只捕获明确日期不匹配，不证明其余解释医学真实。base9b的12条未盲审来自3次HTTP200耗尽输出上限，未按内容重发；3个HTTP0尝试均保留未知费用预留。','',
        '## 实测生成与语义检查成本','',
        '|理由生成器|判定/生成次数|输入tokens|输出tokens|生成秒|每条秒|', '|---|---:|---:|---:|---:|---:|']
    for arm,v in arms.items():lines.append(f"|{arm}|60|{v['input_tokens']}|{v['output_tokens']}|{v['generation_seconds']:.2f}|{v['mean_seconds']:.3f}|")
    lines += ['',f"GPU两臂worker共{wall:.2f}秒（含加载/编译/生成），按¥1.58/h约¥{wall*1.58/3600:.4f}，不含此前排队、准备和回传。API盲审{budget['API_attempts']}次尝试，HTTP200 {budget['API_HTTP200']}次，未知{budget['API_unknown_N']}次；已知usage按忙时原价估算¥{budget['API_known_usage_estimate_peak_CNY']:.6f}，全部未对账预留¥{budget['API_reserved_CNY']:.4f}保留，不无据释放未知费用。共用80元窗口，不重置额度。",'',
        'reason120使用120适配器；reason_base9b在同一已加载底座上禁用适配器。两者均生成相同固定标签的理由，不重新分类；BF16、batch1、16384上下文、greedy192，完整目标reference保留。两臂共享加载墙钟，不能重复累加。','',
        '## 五条固定基线：同60条中的共同有效ID','',markdown_table(five),'',
        '五基线为已有分类参照，均未重跑；reason生成不替换其中任何标签。作者两臂使用作者接口/768输出；120和136用104体系/384输出。paper_r1为作者历史模型。历史费用缺项未补0，GPU窗口全程租金另含等待、准备、加载、编译、回传及发布。','']
    for arm,v in arms.items():lines.append(arm+'三类产出与方向检查：'+json.dumps(v['by_fixed_verdict'],ensure_ascii=False))
    lines += ['', '结论：保留固定标签条件生成理由的功能路线，优先继续reason_base9b：本批产出60/60、较reason120生成快约36%，已盲审方向一致45/48；不能与reason120的51/55或覆盖下界直接当作完整同分母优势。下一阶段固定新300条，继续保留无法生成、方向冲突和原文日期不匹配项，不为理由改标签。']
    (O/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(arms=arms,budget=budget),ensure_ascii=False))

if __name__=='__main__':main()
