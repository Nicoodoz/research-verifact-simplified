"""Render one concise Chinese main report from frozen metrics; no API."""
from pathlib import Path
import common016 as c
from completion_io016 import OUT

NAMES={'v4_first':'V4首次','qwen':'Qwen','cross_repeat':'分歧→普通重复','cross_review':'分歧→独立review','released':'原VeriFact发布系统'}
def signed(x,n=4):return f'{x:+.{n}f}'

def render(path):
    a=OUT/'analysis_001';s=c.read(a/'summary.json');g=c.read(a/'gate.json');m=c.read(a/'metrics.json');pair=c.read(a/'paired.json');rows=c.csvrows(a/'transitions.csv');changes=c.csvrows(a/'changes.csv')
    c.require(s['status']=='complete','No complete-cohort report for missing results')
    lines=['# 016：分歧触发独立复核的新患者验证','',
        '**结论：'+('达到本阶段预设门槛，值得继续第二阶段；本任务不自动执行。' if g['passed'] else '未达到本阶段预设门槛，结束016并停止本方向，不追加v2/v3。')+'**','',
        f"六名新开发患者、601条valid claims（LLM 189/human 412）。V4/Qwen/分歧普通重复/分歧独立review分别正确 **{s['correct']['v4_first']}/{s['correct']['qwen']}/{s['correct']['cross_repeat']}/{s['correct']['cross_review']}** 条。独立review相对最强单模型净 **{g['net_vs_best_single']:+d}** 条，相对同分歧普通重复净 **{g['net_vs_controls']['cross_repeat']:+d}** 条。",'',
        '## 1. 为什么做、实际做了什么','',
        '015无候选evidence_only在旧650条上比最强单模型净增15条，但只是对照的探索信号。016在其预留的新患者检验复现，并检验同样再问一次时，原版independent-review是否优于普通structured重复。claim、医生GT、C48、基础prompt均不改。','',
        f"本批为003原哈希开发顺序第25–30名：{'、'.join(s['patients'])}。保留全部历史有效回答后补齐V4/Qwen；仅 **{s['disagreements']}** 条分歧，各调用一次普通V4重复和015原版review。其余 **{s['agreement_passthrough']}** 条直接采用共同标签。无随机触发、全量review、trigger优化、剩余开发确认或reserved test。",'',
        f"**执行偏差：基础模型未能同期完成。** 硅基流动Qwen服务中断后，经用户授权，保留127条硅基流动Qwen回答，其余474条由阿里云完成（含原真实测试1条）。只更换Qwen端点和API模型标识，其他请求字段逐字相同。原V4也跨暂停前后运行。供应商别名不保证权重／推理实现等价，因此这是实际混合供应商流程的前瞻队列验证，不能称严格同期、单一供应商的纯模型因果比较。供应商分层仅作非随机描述，见provider_strata.csv。",'',
        '“独立”指不看两个模型答案，并不意味着统计上独立或使用第三个模型；review和repeat都是V4。Judge只见原claim和同一C48 reference，不见GT、作者/source/BHC或候选答案。本轮各角色内完整body均唯一；普通重复与首次V4为不同调用。','',
        '## 2. 同队列完整比较','',
        '002 valid-only三分类micro评价，1000次患者cluster bootstrap；LLM/human分别分析。总体“最强单模型”按V4/Qwen的总正确数定义，分作者门槛再分别对各指标的较高值。PA以百分数展示，AC1/MCC保留四位。原VeriFact是不同证据、不同历史模型的整个发布系统参照，不能解释成纯模型差异。','',
        '|作者|方法|正确/分母|PA|AC1|MCC|','|---|---|---:|---:|---:|---:|']
    for author in ('llm','human'):
        for name in NAMES:
            x=m[author][name];n=sum(x['confusion_matrix'][i][i] for i in range(3))
            lines.append(f"|{author}|{NAMES[name]}|{n}/{x['n']}|{100*x['percent_agreement']:.2f}%|{x['gwet_ac1']:.4f}|{x['mcc']:.4f}|")
    lines+=['','**独立review的配对变化及95%患者bootstrap区间：**','','|作者|相对方法|净正确|ΔPA（百分点）[95%CI]|ΔMCC [95%CI]|','|---|---|---:|---|---|']
    for author in ('llm','human'):
        for old in ('v4_first','qwen','cross_repeat','released'):
            d=pair[author]['cross_review_minus_'+old]['metrics'];p=d['percent_agreement'];mc=d['mcc'];r=next(x for x in changes if x['author']==author and x['candidate']=='cross_review' and x['baseline']==old)
            lines.append(f"|{author}|{NAMES[old]}|{int(r['net']):+d}|{p['delta']*100:+.2f} [{p['ci95'][0]*100:+.2f}, {p['ci95'][1]*100:+.2f}]|{mc['delta']:+.4f} [{mc['ci95'][0]:+.4f}, {mc['ci95'][1]:+.4f}]|")
    lines+=['','## 3. 类别代价、改对改错及患者方向','','S/NS/NA分别为Supported/Not Supported/Not Addressed；下表是各GT类别正确数/该类总数，不是新增医学标注。','','|作者|方法|S正确|NS正确|NA正确|错误接受为S|','|---|---|---:|---:|---:|---:|']
    for author in ('llm','human'):
        for name in NAMES:
            x=m[author][name]['per_class'];cells=[f"{x[label]['tp']}/{x[label]['support']}" for label in c.LABELS]
            lines.append('|'+ '|'.join([author,NAMES[name],*cells,str(x['Supported']['fp'])])+'|')
    lines+=['','混淆矩阵（行=GT、列=预测；顺序均为S/NS/NA，每个括号是一行）：','','|作者|方法|3×3混淆矩阵|','|---|---|---|']
    for author in ('llm','human'):
        for name in NAMES:
            lines.append(f"|{author}|{NAMES[name]}|{m[author][name]['confusion_matrix']}|")
    lines+=['','|作者|相对方法|改对|改错|都错但改标签|','|---|---|---:|---:|---:|']
    for r in changes:
        if r['candidate']=='cross_review' and r['baseline'] in ('v4_first','qwen','cross_repeat'):
            lines.append(f"|{r['author']}|{NAMES[r['baseline']]}|{r['fixed']}|{r['broken']}|{r['both_wrong_changed']}|")
    lines+=['','|患者|条数|V4正确|Qwen正确|普通重复流程正确|独立review流程正确|review−V4|','|---|---:|---:|---:|---:|---:|---:|']
    for sid in s['patients']:
        rr=[r for r in rows if r['subject_id']==sid];counts={name:sum(r[name]==r['human_gt'] for r in rr) for name in ('v4_first','qwen','cross_repeat','cross_review')}
        lines.append('|'+ '|'.join([sid,str(len(rr)),*[str(v) for v in counts.values()],f"{counts['cross_review']-counts['v4_first']:+d}"])+'|')
    lines+=['','六患者区间仅反映本队列的不确定性，不能据MCC单点覆盖PA、少数类损失或个别患者退步。完整混淆矩阵、类别PRF和逐患者/作者指标见机器结果。','',
        '## 4. 互补错误是否被利用','', '|作者|分歧类别|条数|普通重复判对|独立review判对|','|---|---|---:|---:|---:|']
    for r in c.csvrows(a/'bucket_outcomes.csv'):
        if r['bucket'] in ('v4_only_correct','qwen_only_correct','both_wrong_disagreement'):
            lines.append(f"|{r['author']}|{r['bucket']}|{r['n']}|{r['cross_repeat_correct']}|{r['cross_review_correct']}|")
    bucketrows=c.csvrows(a/'bucket_outcomes.csv')
    def total(bucket,key):return sum(int(r[key]) for r in bucketrows if r['bucket']==bucket)
    lines+=['',f"合计：V4独对的{total('v4_only_correct','n')}条中，review保住{total('v4_only_correct','cross_review_correct')}条；Qwen独对的{total('qwen_only_correct','n')}条中，review救回{total('qwen_only_correct','cross_review_correct')}条。普通repeat对应也是{total('v4_only_correct','cross_repeat_correct')}/{total('qwen_only_correct','cross_repeat_correct')}条。两者都错的{total('both_wrong_disagreement','n')}条中，review/repeat分别救回{total('both_wrong_disagreement','cross_review_correct')}/{total('both_wrong_disagreement','cross_repeat_correct')}条。互补空间确实存在，但review没有比普通重复更好地利用单方正确病例；总计只多救回1条双错病例。"]
    for author,o in s['oracle'].items():
        lines+=['',f"{author}：一致集合仍有{o['agreement_wrong']}条共同错误，本方法不会触及。分歧内若总能选中正确候选，完整队列理论正确数为{o['perfect_candidate_selection_correct']}；若允许第三标签且完美复核，为{o['perfect_free_review_correct']}。这些是GT计算的上限，不是可实现成绩。"]
        e=g['error_enrichment'][author]
        lines+=['',f"V4在分歧集合的错误率为{e['disagreement_V1_error_rate']*100:.1f}%，在一致集合为{e['agreement_V1_error_rate']*100:.1f}%；这描述错误富集，不构成分歧门控优于随机触发的因果证据。"]
    lines+=['','## 5. 预设门槛与研究判断','',
        '调用前冻结：比最强单模型至少净+13、比普通重复流程至少净+7；两作者至少净+2/+5且MCC各+0.025；review相对repeat两作者均净增且MCC各+0.01；AC1、类别、false-S和患者分布同时满足保护条件。所有条件均须通过。','',
        '未通过的条件：'+('、'.join(k for k,v in g['conditions'].items() if not v) or '无')+'。','',
        '**对本轮问题的直接回答：**','',
        '- **015的明显提升未复现。** review相对Qwen总净−5，相对V4净+6；不能仅以较弱V4为参照保留正向叙述。',
        '- **独立review未明显优于普通repeat。** 总净+1（LLM +2、human −1），未达到+7门槛。无法证明换成独立review具有额外价值，也没有随机门控对照可以证明触发策略的因果优势。',
        '- **两作者、类别与患者方向不一致。** 相比Qwen，LLM/human PA分别降低1.59/0.49个百分点，AC1均降低；LLM虽MCC更高，也不能抵消PA损失。human NA正确数由V4的27/60降至22/60，false-S由11增至13。review相对V4有5/6患者净增，但相对Qwen仅16076净增6条，其他4人退步、1人持平；97683相对V4损失3条，违反损失上限。',
        '- **最简单的同C48选择仍是直接用单模型。** 本批Qwen总正确数最高（457），高于review的452。原VeriFact发布系统达到489，但使用不同reference，且false-S更多；不是同条件Judge优越性证明。',
        '- **不进入下一阶段，也不形成已验证论文方法候选。** 没有开展剩余开发患者冻结确认。双模型＋review的Judge估算成本为单Qwen的1.84倍、单V4的2.54倍，当前增益不足以抵消成本；结束本方向，不追加优化。','',
        '本阶段能回答新患者上的复现，以及同分歧集合中review与普通重复的差别。没有随机/hash触发与全量review，不能把“分歧处错误较多”当作分歧门控的因果优越性，也无法判断全量review是否更好。未开展冻结后的剩余开发确认，因此不能称方法已经通过最终确认或成为已验证论文方法。','',
        '## 6. 费用、复查与边界','',
        f"全任务{ s['http_attempts'] }次HTTP尝试，状态分布{ s['http_status_counts'] }。全部服务usage估算加未知预留 **¥{s['task_used_or_reserved_cny']:.6f} / ¥40**；包括共同检索、两个基础模型、两种分歧复核及重试，非账单核验。按高峰无缓存价格比较，部署双模型+review的Judge费用约¥{s['economics']['ideal_judge_pipeline_peak_no_cache_cny']:.4f}，为单V4的{s['economics']['over_V4']:.2f}倍、单Qwen的{s['economics']['over_Qwen']:.2f}倍；逻辑Judge调用{s['economics']['deployed_logical_judge_calls']}次，对比单模型601次。普通重复对照不计入拟部署流程费用，共同检索另列。",'',
        f"其中收到usage的费用／已确定费用估算¥{s['received_usage_estimated_cny']:.6f}，未知或缺失usage预留¥{s['unknown_or_failed_usage_reservation_cny']:.6f}；历史失败及所有服务测试均计入。部署费用是本批实际token在高峰无缓存价格下的对照估算，不是未来纯阿里云配置的实测账单。",'',
        '费用来源：[硅基流动分时价格](https://docs.siliconflow.cn/docs/release-notes/overview)、[阿里云北京Qwen价格](https://help.aliyun.com/zh/model-studio/qwen3-8-27b)。发送前使用完整请求文本、历史服务器usage校准估计token，生成长度留余量；不把估计说成服务器精确token计数。冻结body和max_tokens用于每次保守费用预留，跨账号/阶段/供应商累计保护。','',
        '保留完整请求、原生回执、usage、费用、预测、分歧台账和预先门槛。断网重放与边界检查见verification_001；独立审计尚未进行，执行自查不等于审计PASS。模型仅有供应商别名，非不可变权重版本；理由不是内部机制证据，标签正确不保证解释医学正确。本研究不新增医生gold，也不证明临床部署安全性。','',
        '## 复查入口','',
        '- [原冻结协议](../protocol_002.md) · [供应商切换登记](protocol_amendment.json) · [原始指标与区间](analysis_001/metrics.json) · [配对比较](analysis_001/paired.json) · [完整分歧/改判台账](analysis_001/transitions.csv)',
        '- [门槛机器结果](analysis_001/gate.json) · [逐患者指标](analysis_001/patients.csv) · [费用与调用汇总](analysis_001/summary.json)',
        '- `verification_001/`保存离线重建与Windows检出检查；`handoff_001.json`登记被审HEAD、未提交改动与指纹。',
        '- 原protocol_001及preparation_001是被用户缩减前的无收费预案，现执行protocol_002/preparation_002，历史版本不回写。','']
    c.require(not path.exists(),'Main report already exists');path.write_text('\n'.join(lines),encoding='utf-8',newline='\n')

if __name__=='__main__':render(OUT/'report.md')
