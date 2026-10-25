"""Render final report and full metrics from completed frozen results; no calls."""
import common093 as c
def pct(v):return '—' if v is None else f'{v:.2%}'
def table(metrics):
    if not metrics:return '本集合无共同有效输出，不能计算配对分类指标。'
    out=['|配置|MCC|PA|正确/N|错误支持/non-S|AC1|Macro-F1|预测S假发现率|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm,z in metrics.items():out.append(f"|{arm}|{z['MCC']:.4f}|{pct(z['PA'])}|{z['correct']}/{z['N']}|{z['false_S']}/{z['true_non_S']}|{z['AC1']:.4f}|{z['Macro_F1']:.4f}|{pct(z['false_discovery_S'])}|")
    return '\n'.join(out)
def main():
    data=c.read(c.OUT/'analysis.json');cost=c.read(c.OUT/'cost_ledger.json');decision=c.read(c.OUT/'decision.json');freeze=c.read(c.OUT/'main_freeze.json')
    detail=['# 093 完整指标、有效性与成本','','原作者=Original；B=原C48；F=仅折叠；A=折叠后补证。矩阵行GT、列预测，顺序S/NS/NA。无效输出没有用旧答案补齐。','']
    sections=[]
    for panel,d in data['panels'].items():
        title='自然组成主面板' if panel=='natural' else 'NS/NA压力面板'
        sections+=['## '+title,'',f"完整N={d['N']}，患者{d['patients']}；GT={d['GT']}。共同core有效{d['common_core_N']}，共同raw有效{d['common_raw_N']}。",'','Frozen PriorG：','',table(d['common_core_metrics']['PriorG']),'','原生raw（自己的共同有效分母）：','',table(d['native_raw_metrics']),'']
        detail+=['## '+title,'',f"完整有效性：{d['full_status']}",'']
        for method,tt in d['common_core_metrics'].items():
            detail+=['### 共同core / '+method,'',table(tt),'','|配置|类别|Precision|Recall|F1|','|---|---|---:|---:|---:|']
            if tt:
                for arm,z in tt.items():
                    for i,lab in enumerate(['S','NS','NA']):detail.append(f"|{arm}|{lab}|{pct(z['precision'][i])}|{pct(z['recall'][i])}|{z['F1'][i]:.4f}|")
                detail+=['','混淆矩阵：','']+[arm+': '+str(z['confusion_matrix']) for arm,z in tt.items()]+['']
        detail+=['### 真正补证子集（描述性，不替代主面板）','',f"N={d['operated_core_N']}，GT={d['operated_GT']}",'',table(d['operated_metrics']),'']
        sections+=['|层次/比较|救回|伤害|净正确|患者胜/负/平|PA差95%区间（百分点）|MCC差95%区间|','|---|---:|---:|---:|---|---|---|']
        for method in ['raw','PriorG']:
            for name,p in d['comparisons'][method].items():
                if not p:continue
                ci=p['independent_supplement_CI95'];pa=ci['PA'];mcc=ci['MCC']
                sections.append(f"|{method} {name}|{p['rescue']}|{p['harm']}|{p['net']:+d}|{p['patient_win_loss_tie']}|[{pa[0]*100:+.2f}, {pa[1]*100:+.2f}]|[{mcc[0]:+.4f}, {mcc[1]:+.4f}]|")
        sections+=['',f"完整N的无效/保守PA：{d['full_status']}。完整N保守PA把无结果视为未判对，只是下界；三分类MCC在共同core集合计算，不混用。",'']
    costlines=['|面板/臂|输入tokens|输出tokens|逻辑单臂原价费用|平均响应秒|','|---|---:|---:|---:|---:|']
    for panel,arms in cost['logical_panels'].items():
        for arm,z in arms.items():costlines.append(f"|{panel}/{arm}|{z['prompt_tokens']}|{z['completion_tokens']}|¥{z['undiscounted_cny']:.6f}|{z['mean_elapsed_seconds']:.2f}|")
    body=f"""# 093 重复原文折叠与固定预算补证：首轮研究报告

## 结论

**{decision['conclusion']}**

{decision['reason']}

本轮完成历史差异核查、GT盲材料盘点、唯一候选实现、功能检查及真实同期B/F/A比较。没有微调核心Judge、训练辅助模型、增加F4、重训PriorG或更换大模型；默认B保持不变。执行者自检见selfcheck.json，独立审计未执行。初始HEAD e3999daa6，使用下一个空闲编号093。

## 为什么不是换名重复

[历史差异表](history_difference.md)逐项核对028、042、046、048及011/047/049/069/081等。动态要求、关系、引用放行、coverage packing、缺口扩检都已有真实试验；本轮不重做。候选的新增实际操作是：把原包完全重复正文折叠为带完整来源映射的共享原文，只用真实省下的预算补入旧D48原文，原B没有被挤出。042的重选可丢原段，046/048的追加放宽了原输入量，因此并非同一干预。

普通字典编码、贪心排序和原文来源核对不是算法首创。程序可逆不等于模型理解无损，文本重复也不证明临床事件相同、笔记复制或证据不独立。该区别必须由F−B及A−F实测，而不是命名来证明。

## 方法与冻结

详见[操作说明](method.md)及[协议](../../tasks/093_lossless_evidence_budget/protocol.md)。B为原实际C48；F保留所有来源头，在完全相同的至少160字符正文之间共享原文，最多4组；A按旧rerank次序加入能放入的不同正文候选。每note最多2条、总来源最多16条、最终字符数不超过该病例原B实际长度。反证与支持不由本地规则分类或过滤，原claim/医生GT不改。

原文及每个来源跨度均可回查，F可展开回原B字节；A保留全部B来源。新增内容只来自同患者旧D48，不含生成医学解释。Judge继续deepseek-v4-flash-0731、thinking-high、temperature0、8192输出上限、同一评分接口。新三分数沿原Frozen PriorG；raw/U0/U2同步诊断，不按结果改工作点。无效不填旧答案、不自动设NA，原始回执保留。

## 样本与可测性

在不看GT或旧模型对错下，9065条C48中1267条可节省字符；1401条有完整D48/分数的原生材料中，228条可折叠、198条能真正补证，跨8患者、共329新增段。达到运行前登记的最低工程可测条件；不是分类成功门槛。

首轮按实际完整请求字节上界冻结自然90（75S/6NS/9NA、18患者）与压力30（15NS/15NA、17患者）。自然选择与独立前90个ID哈希前缀完全一致；压力按标签、患者轮转与ID哈希，不按历史对错。两面板互斥但患者有交集，分别报告，不合并成总体PA。当前数据均有历史研究暴露；本轮允许使用全体材料，但真实分类母体仅是1401条可回放子集。

自然仅12条/5患者、压力4条/3患者实际补证，其他病例按部署逻辑保持原包并共享B回执。自然触发子集为11S/1NA，NS机会主要在压力的2NS/2NA，故少数类方法效应的分母很小。不能把完整面板共同正确数当新机制修复数。

三臂120条共360逻辑位置，同ID同body共享后152正式请求；1次虚构预检另计。不集成或择优多次回答，每个部署方案一次Judge；F是组件对照，不是额外核查答案。全部规模、输入、别名和预算在新回答前冻结。

{chr(10).join(sections)}

## 原生判断与决策边界

{decision['raw_final_interpretation']}

每例raw→final与三对比较保存在[transitions.jsonl](transitions.jsonl)。有效性先于机制归因，缺失/无效不写成score边界变化。患者bootstrap1000次，条件于本次固定样本与输出；没有多种子或独立外部验证，区间跨0不等价于无差别或等效。

## 代表病例与来源

[病例分析](case_analysis.md)只公开ID、标签变化、来源指纹和抽象关系，不上传原文。病例解释是执行者对可见材料的核查，不是新医生GT或模型内部推理因果证据。没有根据病例修改操作、阈值或再发成功回答。

## 成本与工程完整性

全任务{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200，重试{cost['retries']}次；按0731北京忙时未优惠原价及未知预留累计 **¥{cost['original_or_reserved_cny']:.6f}/20**，预检¥{cost['preflight_cny']:.6f}。原价依据为[阿里云0731快照价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)，使用输入3/输出9元每百万token，不使用通用未版本化模型的1/2价格或优惠扩大额度。

主运行最大输入字节/8192输出保守上界¥{freeze['main_worst_case_cny']:.6f}，加虚构预检上界¥{freeze['preflight_worst_case_cny']:.6f}及2元恢复预留仍小于20。普通通信故障有限恢复，未知保留上界，已成功回答没有因内容重发。没有新增embedding/rerank/辅助LLM调用，没有云GPU租赁。

{chr(10).join(costlines)}

上述是逻辑单臂部署费用描述，不能相加当本任务真实费用；真实费用只求物理回执。额外检索收费为0是因为复用了现有候选与分数，不表示完整部署检索免费；字符预算相同也不表示token完全相同。前处理为本地精确匹配/格式化，不声称单独测得端到端部署加速。

## 下一步决定与交付

{decision['next_step']}

本轮不自动跑全量、不增加版本，不启动094。完整三分类precision/recall/F1、混淆矩阵和各决策层见[detailed_tables.md](detailed_tables.md)；机器结果analysis.json、cost_ledger.json、predictions_public.jsonl、source_manifest.json、main_freeze.json和execution_freeze.json可核查。只做执行者自检，不写独立审计PASS。私有原文、请求/回执保存在.local_models/093，不修改.gitignore或历史结果。
"""
    c.put(c.OUT/'report_generation.json',dict(utc=c.now(),decision_sha256=c.sha(c.OUT/'decision.json'),analysis_sha256=c.sha(c.OUT/'analysis.json')))
    with (c.OUT/'report.md').open('x',encoding='utf-8',newline='\n') as f:f.write(body)
    with (c.OUT/'detailed_tables.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(detail)+'\n')
    print('Chinese report and detailed tables written.')
if __name__=='__main__':main()
