"""Render Chinese report with every frozen comparison and complete class metrics."""
from collections import Counter
import common094 as c
def pct(x):return '—' if x is None else f'{x:.2%}'
def table(t):
    if not t:return '无可计算共同有效集合。'
    out=['|配置|MCC|PA|正确/N|false-S/non-S|AC1|Macro-F1|预测S假发现率|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for a,z in t.items():out.append(f"|{a}|{z['MCC']:.4f}|{pct(z['PA'])}|{z['correct']}/{z['N']}|{z['false_S']}/{z['true_non_S']}|{z['AC1']:.4f}|{z['Macro_F1']:.4f}|{pct(z['false_discovery_S'])}|")
    return '\n'.join(out)
def main():
    data=c.read(c.OUT/'analysis.json');cost=c.read(c.OUT/'cost_ledger.json');decision=c.read(c.OUT/'decision.json');diff=c.lines(c.OUT/'extraction_differences.jsonl');parts=[];detail=['# 094 完整分层指标','','Original为原作者同ID发布标签，不施加本研究G。B为同期原默认，V为claim可见问答，Q为待证答案隔离问答。矩阵行GT、列预测，顺序S/NS/NA。','']
    for panel,d in data['panels'].items():
        name='自然组成面板' if panel=='natural' else '机制富集面板（不可当全量组成）'
        parts+=['## '+name,'',f"冻结{d['N']}条/{d['patients']}患者，GT={d['GT']}；实际问答{d['operated_N']}条，core共同有效{d['core_N']}，raw共同有效{d['raw_N']}。",'','最终Frozen PriorG：','',table(d['metrics']['PriorG']),'','原生raw：','',table(d['native_raw_metrics']),'','|比较|救回/伤害/净正确|患者胜/负/平|PA差95%区间（百分点）|MCC差95%区间|','|---|---|---|---|---|']
        for method in ['raw','PriorG']:
            for pair,z in d['comparisons'][method].items():
                ci=z['independent_supplement_CI95'];pa=ci['PA'];mc=ci['MCC'];parts.append(f"|{method} {pair}|{z['rescue']}/{z['harm']}/{z['net']:+d}|{z['patient_win_loss_tie']}|[{pa[0]*100:+.2f},{pa[1]*100:+.2f}]|[{mc[0]:+.4f},{mc[1]:+.4f}]|")
        parts+=['',f"完整N有效性及保守正确率：{d['full_status']}。无效不填旧答案；保守PA仅把无结果视作未判对，不把其变成NA。",'']
        detail+=['## '+name,'']
        for method,t in d['metrics'].items():
            detail+=['### 共同core / '+method,'',table(t),'','|配置|类别|Precision|Recall|F1|','|---|---|---:|---:|---:|']
            for a,z in t.items():
                for i,label in enumerate(['S','NS','NA']):detail.append(f"|{a}|{label}|{pct(z['precision'][i])}|{pct(z['recall'][i])}|{z['F1'][i]:.4f}|")
            detail+=['','混淆矩阵（S/NS/NA）：','']+[a+': '+str(z['confusion_matrix']) for a,z in t.items()]+['']
        for method,t in d['operated_metrics'].items():detail+=['### 实际操作子集 / '+method,'',table(t),'']
        for author,tt in d['author_strata'].items():
            for method,t in tt.items():detail+=['### '+author+' / '+method,'',table(t),'']
    coverage=[]
    for panel in ['natural','mechanism']:
        rr=[r for r in diff if r['panel']==panel]
        coverage.append(dict(panel=panel,operated=len(rr),both_valid=sum(r['V_valid'] and r['Q_valid'] for r in rr),V_nonempty=sum(r['V_candidates']>0 for r in rr),Q_nonempty=sum(r['Q_candidates']>0 for r in rr),record_identical=sum(r['record_identical'] for r in rr),answer_text_identical=sum(r['answer_text_identical'] for r in rr),citation_set_identical=sum(r['citation_set_identical'] for r in rr)))
    costs=['|面板/方案|部署调用数|输入token|输出token|原价费用|平均串行调用耗时秒|','|---|---:|---:|---:|---:|---:|']
    for panel,arms in cost['logical_panels'].items():
        for arm,z in arms.items():costs.append(f"|{panel}/{arm}|{z['calls']}|{z['input_tokens']}|{z['output_tokens']}|¥{z['undiscounted_cny']:.6f}|{z['mean_sequential_call_seconds']:.2f}|")
    for panel,d in c.read(c.OUT/'both_aux_valid_diagnostic.json').items():
        for method,t in d['metrics'].items():detail+=['## '+panel+' 双方辅助记录有效诊断 / '+method,'','按输出有效性作事后诊断，不替代主分析或选择新规则。','',table(t),'']
    report=f'''# 094 固定C48下的答案隔离式问答核验

## 结论

**{decision['conclusion']}**

{decision['reason']}

已完成用户指定唯一候选的历史核查、实现、操作验证和同期B/V/Q实测。默认C48→T-S B thinking-high→Frozen PriorG不变；不延伸092、不继续093 packing、不加F4或拟合新后处理。初始HEAD为03a58bb3b，使用空闲编号094。

## 研究问题与历史区别

本轮检验取证端暂时不见claim待证取值，是否减少照抄假设、改善事件/状态/时间对应，以及收益是否能兑现为最终分类。028、048、049、065都已有要求、引用或独立审核，但其取证输入包含原claim；094增加的是可检查的输入隔离与匹配V对照，详见[历史差异表](history_difference.md)。不把既有阴性解释为整个方向不可能。

QAGS使用源文档与生成文本问答一致性；CoVe的two-step/factored验证明确排除初始回答上下文。094承接已有思想，非算法首创；临床固定证据三分类和当前分数边界是否受益需要本轮实测，不能继承原论文不同数据的数字。[QAGS原论文](https://aclanthology.org/2020.acl-main.450.pdf) · [CoVe原论文](https://aclanthology.org/2024.findings-acl.212.pdf)。

## 唯一候选与对照

生成器仅看原claim，产生一个开放问题、原claim对应取值及其原文字串。登记取值留在最终比较端。Q取证请求只有question/reference；V额外包含unverified_claim，其余模型、问题、完整C48、提示、2048输出预算一致。原生请求SHA、隔离白名单和同体别名可核查。

取证同用deepseek-v4-flash-0731非thinking辅助接口，最多两候选、每个最多两处来源引用，允许歧义或当前证据不足。引用校验成功仅说明文本可定位，不证明回答真值。最终B仍原T-S thinking-high/8192输出；V/Q使用相同的辅助字段说明和原输出schema，完整claim/C48均保留，辅助记录与病历原文明确分开，缺答案不硬判NS/NA，不设全支持放行。

Q−V检验答案可见性差异；V−B检验整理与额外计算；Q−B检验系统收益。三者最终同一Frozen PriorG，raw/U0/U2仅作诊断，事后不选新工作点。label_scores是LLM自报分数，不是真实token probability或校准概率。每病例每方案一个最终回答，不投票/择优；完全相同最终请求体共享首次成功回执。

## 先确认操作，再运行Judge

32条在任何新回答前冻结：自然20条为全9065材料ID哈希前缀，实际18S/0NS/2NA；机制12条按预定事件/时间/状态词、标签各4、患者轮转与ID规则，不按旧模型对错选。原本正确病例没有被排除。两面板不混成总体PA；自然缺NS，少数类证据只能参考小规模富集面板。全体患者均有历史暴露，不是独立holdout。

32次生成后执行者只看claim与问题做语义核查。统一增加“先确认有无记录，不预设事件发生”的限定，拒绝6个丢失事件定位或改变问题范围的输出，不重发生成、不逐例改写。自然16/20、机制10/12实际操作；这是经人工审核的原型，不是已验证的全自动系统。[问题工程记录](engineering_note.md)。

初版来源匹配将空白差异当失败，随后仅作空白定位修复并回填真实原文，保留初版结果，无新增API、不修复文字或编号错误。V/Q合法取证23/26、22/26，各13份非空回答；另外10/9份合法证据不足，3/4份无效只传不可用标记。没有把工程无效解释成方法阴性。[来源定位更正](source_locator_correction.md)。所有修复发生在最终Judge结果前，方法/最终输入再次冻结。

实际内容变化（仅描述性字符串/来源指标，不是医学正确性gold）：{coverage}。空记录也可能相同；回答文字不同不自动表示事实发生变化，须结合病例分析。

{chr(10).join(parts)}

## 原生改善、后处理与取证内容

{decision['raw_final_interpretation']}

{decision['content_interpretation']}

[代表病例](case_analysis.md)使用ID、标签、分数及来源指纹，不发布原临床文本；没有新增QA医生gold，不凭reason推断模型内部机制。完整类别、矩阵、操作子集和作者分层见[detailed_tables.md](detailed_tables.md)。transitions.jsonl保留每例三对比较，extraction_differences.jsonl保留取证状态/引用变化。

患者bootstrap1000次，条件于本次冻结输出，不覆盖历史选择或调用随机性。小样本区间含0不等于等效；没有重复成功调用，不能把单轮差异认定为稳定机制效应。问题仍保留识别上下文，原C48检索也曾受原claim影响，因此隔离范围是“本次取证请求隐藏登记目标答案”，不是整个管线与原命题完全统计独立。

## 成本与收益

总尝试{cost['attempts']}，HTTP200 {cost['HTTP200']}，重试{cost['retries']}；未优惠原价及未知预留 **¥{cost['original_price_or_reserved_cny']:.6f}/20**。分阶段费用：{cost['stage_cost_cny']}。事前全部六调用链最大输出上界¥16.829463，预检上界¥0.057876，另预留¥2。无新增检索、GPU租赁或模型下载。

[官方0731北京忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)按每百万input/output 3/9元，未用折扣扩大预算。真实任务费用按物理回执求和；以下逻辑方案费用包含生成、取证及最终判断，不能跨臂相加当物理账单。

{chr(10).join(costs)}

另有32条执行者问题审核及来源/工程检查，人工时间未单独计时、未折算货币；上表不声称端到端部署人力成本。耗时为实测调用耗时之和，不是并发批处理墙钟加速。复用检索缓存不代表上线检索免费。

## 决策、限制与交付

{decision['next_step']}

执行者自检见selfcheck.json；独立审计未执行。历史工件、默认系统和.gitignore不变，私有原文/回执保留在.local_models/094。任务结项提交推送后停止，不自动095、全量或新版本。复查入口见[任务README](../../tasks/094_answer_isolated_verification/README.md)和[audit_handoff.md](audit_handoff.md)。
'''
    (c.OUT/'report.md').write_text(report,encoding='utf-8');(c.OUT/'detailed_tables.md').write_text('\n'.join(detail).rstrip()+'\n',encoding='utf-8')
    c.put(c.OUT/'report_metadata.json',dict(utc=c.now(),analysis_sha256=c.sha(c.OUT/'analysis.json'),decision_sha256=c.sha(c.OUT/'decision.json'),operation_content_summary=coverage))
    print('Report written')
if __name__=='__main__':main()
