# 100：今晚预注册后续研究〔名称阅读版〕

2026-10-27仅统一方案展示名称；[冻结原报告](report.md)、预测、数值、判据及计算口径均保留。原报告的阶段状态仍按结项时记录解释。

## 方案名称映射

|展示名称|冻结代号|中文解释|
|---|---|---|
|`verifact_ref`|O|原作者发布的reference原样输入当前同Judge，无示例；属于原作者式适配，不代表完整复现论文系统。|
|`compact48`|C / C48|冻结C48检索证据，无示例；48指候选池上限，不是最终输入48段或48份note。|
|`demo_protect`|P / P90|verifact_ref加090已冻结的四个保护压缩示例；名称描述构造，不表示保护机制已成立。|
|`demo_lenmatch`|Q|verifact_ref加相同四例的普通相关性压缩；示例身份、标签、顺序不变，逐例配平保护压缩预算，保留完整源单元。|
|`chunks24k`|S24|BM25检索完整短块，逐例匹配notes24k实际渲染长度；24k是参考上限，不是固定输入长度或块大小。|
|`notes24k`|L24|以最高子块BM25分数排序，按24,000 reference tokens上限装入完整原note，不截断note。|
|`ehr_all`|EHR-all|输入冻结合法范围内全部原notes，不检索、不总结、不截断；不是患者终身EHR。|
|`demo_full`|F（098诊断臂）|verifact_ref加同四例的完整示例reference；不是当前患者的ehr_all。|
|`paper_r1`|Original / 作者历史R1发布预测|原作者发布的历史R1预测，只作历史参照；与当前同Judge的verifact_ref明确区分。|

100实际执行证据分支：demo_protect/demo_lenmatch/demo_full仅用于回顾098，未在100新增调用。ehr_all仅跑开发；确认晋级者是notes24k，chunks24k为必要长度对照。chunks24k/notes24k按JSON转义后reference内部的官方0731 tokenizer长度计预算，保留完整单元造成的离散差；ehr_all沿住院日历范围并排除discharge summary等资料。

规则见[AGENTS命名规范](../../AGENTS.md#实验方案命名与展示)；实现依据：[证据构造及长度定义](../../tasks/100_preregistered_followup/evidence100.py#L88) · [098示例与Judge构造](../../tasks/098_p90_native_confirmation/prepare098.py#L103).

## 结论与结果（统一展示名称）

**最终类别：失败停止。** 实际分支：evidence；候选：notes24k。默认系统未改变；独立审计未执行。

## 098先行结论

098已完整完成2120目标请求，demo_lenmatch构造2次另计；主面板、压力、demo_full（80条）、四臂重复60均完成。demo_protect对verifact_ref/demo_lenmatch/compact48原门槛通过为False/False/False，压力检查={'false_S_limit': True, 'minority_recall': False}，重复反向={'verifact_ref': False, 'demo_lenmatch': True}。按本次用户要求，只有recommend_replace_C=true才走跨模型；本轮为False。[098正式报告](../098_p90_native_confirmation/report_display.md)。

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.6278|82.87%|329/397|7/98|58.1%/71.6%|
|verifact_ref|0.6462|83.63%|332/397|6/98|61.3%/74.6%|
|paper_r1|0.5468|81.36%|323/397|23/98|51.6%/49.3%|
|demo_protect|0.6301|83.12%|330/397|5/98|48.4%/73.1%|
|demo_lenmatch|0.6328|83.63%|332/397|6/98|51.6%/67.2%|

## 样本、冻结和公平条件

32名确认患者是100人排除098评价40与示例开发28后的余集；本轮开发实际42人，确认实际32人，开发与确认患者互不重叠。全部患者历史已暴露，只称本轮患者隔离确认。开发48自然+NS/NA各12，确认预冻192自然+NS/NA各16，确认自然16条独立重复。原始GT只抽样/评价，不进构造。原定规模的最贵完整路径141.81元，事前按用户规定整体降档后121.30元；包含为098原50元上限余量完整预留、每次8192输出、无缓存/别名节约。实际便宜不扩样。[协议](../../tasks/100_preregistered_followup/protocol.md) · [输入冻结](execution_freeze.json) · [预算](budget_plan.json)。

证据分支固定与098同DeepSeek0731、同简洁Judge、thinking-high、temperature0、max8192；无示例/后处理。verifact_ref使用发布reference，compact48使用冻结检索证据。chunks24k/notes24k遍历同一完整eligible语料，008词法、640字符块和BM25原函数，031实际6125段的索引字段/文本/ID已逐一核对。notes24k以最高子块分数排完整note；chunks24k完整短块逐例配平notes24k实际JSON渲染token预算；ehr_all给全部合规原note。仅同note相接/空白间隔可合并；原文完整覆盖恢复原TEXT。合法范围沿既有住院日历日期、排除discharge summary，不临改截止时间或HADM规则。原note的实际HADM保留供回查。

原始未转义语料最长299672 tokenizer tokens；本轮冻结最大全请求输入预计310204，低于0731平台1M上下文，全部ehr_all均完整，无长患者剔除或截断。长度预算计Input JSON转义后reference内部，API实际prompt usage另列，公开tokenizer不冒充已证明内部模板逐token一致。compact48只作参考，不参与候选筛选。相同body跨臂只共享本轮首答，既定重复独立发送。[容量与别名](capacity_and_alias_preflight.json) · [来源/范围](source_inventory.json)。paper_r1仅作者历史R1同ID预测，不能替代同期verifact_ref；098的demo_full是完整历史示例，100的ehr_all是本患者全部合规notes、无示例，二者不同。

## 开发排雷与唯一候选

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.4772|72.92%|35/48|1/11|25.0%/85.7%|
|ehr_all|0.6473|83.33%|40/48|0/11|50.0%/85.7%|
|notes24k|0.7101|87.50%|42/48|0/11|50.0%/85.7%|
|verifact_ref|0.5892|79.17%|38/48|0/11|50.0%/85.7%|
|paper_r1|0.6269|83.33%|40/48|0/11|75.0%/42.9%|
|chunks24k|0.6771|85.42%|41/48|0/11|50.0%/85.7%|

额外NS/NA压力：

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.1869|50.00%|12/24|5/24|41.7%/58.3%|
|ehr_all|0.1147|50.00%|12/24|3/24|41.7%/58.3%|
|notes24k|0.1935|54.17%|13/24|3/24|41.7%/66.7%|
|verifact_ref|0.2587|54.17%|13/24|5/24|50.0%/58.3%|
|paper_r1|0.2188|45.83%|11/24|8/24|58.3%/33.3%|
|chunks24k|0.0387|45.83%|11/24|3/24|33.3%/58.3%|

开发筛选逐项结果（未按显著与否或小阳性决定扩量）：

- ehr_all：eligible=True，否决=无，路径A/B=True/True。
- notes24k：eligible=True，否决=无，路径A/B=True/True。
- chunks24k：eligible=True，否决=无，路径A/B=True/True。

唯一晋级：notes24k。完整共同有效口径/覆盖见development_analysis。

## 完整确认结果

自然分布：

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.4778|77.78%|147/189|6/37|53.8%/58.3%|
|notes24k|0.4584|78.31%|148/189|6/37|46.2%/41.7%|
|verifact_ref|0.4789|77.78%|147/189|4/37|53.8%/50.0%|
|paper_r1|0.4066|79.89%|151/189|14/37|30.8%/37.5%|
|chunks24k|0.4707|77.78%|147/189|6/37|53.8%/50.0%|

额外NS/NA压力：

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.3010|62.50%|20/32|2/32|50.0%/75.0%|
|notes24k|0.3290|65.62%|21/32|0/32|50.0%/81.2%|
|verifact_ref|0.4268|68.75%|22/32|2/32|56.2%/81.2%|
|paper_r1|0.0824|43.75%|14/32|7/32|37.5%/50.0%|
|chunks24k|0.4045|68.75%|22/32|0/32|50.0%/87.5%|

|候选−参考|救回/伤害|ΔMCC [95%患者区间]|ΔPA|Δfalse-S率 [95%区间]|
|---|---:|---|---:|---|
|compact48−verifact_ref|8/8|-0.0011 [-0.0870,+0.0807]|+0.00%|+5.41% [+0.00%,+15.00%]|
|compact48−chunks24k|9/9|+0.0071 [-0.0537,+0.0756]|+0.00%|+0.00% [-6.98%,+9.09%]|
|notes24k−compact48|9/8|-0.0194 [-0.0991,+0.0461]|+0.53%|+0.00% [-8.00%,+8.83%]|
|notes24k−verifact_ref|8/7|-0.0205 [-0.1060,+0.0474]|+0.53%|+5.41% [+0.00%,+15.00%]|
|notes24k−chunks24k|6/5|-0.0123 [-0.0742,+0.0322]|+0.53%|+0.00% [-6.98%,+9.09%]|
|chunks24k−compact48|9/9|-0.0071 [-0.0756,+0.0537]|+0.00%|+0.00% [-9.09%,+6.98%]|
|chunks24k−verifact_ref|9/9|-0.0082 [-0.0899,+0.0628]|+0.00%|+5.41% [+0.00%,+12.77%]|

压力配对：

|候选−参考|救回/伤害|ΔMCC [95%患者区间]|ΔPA|Δfalse-S率 [95%区间]|
|---|---:|---|---:|---|
|compact48−verifact_ref|1/3|-0.1258 [-0.3439,+0.0901]|-6.25%|+0.00% [-8.83%,+9.09%]|
|compact48−chunks24k|1/3|-0.1036 [-0.3034,+0.1196]|-6.25%|+6.25% [+0.00%,+15.62%]|
|notes24k−compact48|2/1|+0.0280 [-0.2035,+0.1834]|+3.12%|-6.25% [-15.62%,+0.00%]|
|notes24k−verifact_ref|2/3|-0.0978 [-0.3716,+0.0881]|-3.12%|-6.25% [-15.15%,+0.00%]|
|notes24k−chunks24k|1/2|-0.0755 [-0.3273,+0.1385]|-3.12%|+0.00% [+0.00%,+0.00%]|
|chunks24k−compact48|3/1|+0.1036 [-0.1196,+0.3034]|+6.25%|-6.25% [-15.62%,+0.00%]|
|chunks24k−verifact_ref|2/2|-0.0223 [-0.1287,+0.0649]|+0.00%|-6.25% [-15.15%,+0.00%]|

固定同body重复：冻结16条、共同有效15条，标签翻转{'notes24k': 0, 'verifact_ref': 0, 'chunks24k': 1}；第二答不替换首答。首次/第二次三类指标、配对与核心方向完整保留在confirmation_analysis.json。

实用门槛与区间的正式判定见[confirmation_decision.json](confirmation_decision.json)。本轮notes24k−verifact_ref ΔMCC=−0.0205、ΔPA=+0.53个百分点、false-S率+5.41个百分点，MCC与风险两路线点值均未通过，并非仅差显著性。相对compact48和chunks24k同样未过实用门槛，完整note机制未成立。

正确数变化来自Supported净+4、NS净−1、NA净−2；PA略升掩盖少数类损失。重复verifact_ref/notes24k标签未变且notes24k−verifact_ref MCC仍为负，没有可声称稳定的核心优势；机器stability_pass字段不能在主路线未通过时单独读成“稳定性通过”，详见[错误转移与字段解释](error_transfer_analysis.md)。原预测和判定未改写。只有实用点值和主要改善量患者95%区间均支持且压力/重复合格才叫确认通过；区间跨0不等于等效。

## 长度、实际操作、覆盖和费用

下表为当前实际最后执行阶段的各臂首次调用，cache/别名实际均分费和独立部署无缓存费分开。

|臂|例数|平均输入token|平均输出含思考|实际均分元/例|无缓存元/例|
|---|---:|---:|---:|---:|---:|
|compact48|224|2950.5|461.0|0.006500|0.006500|
|notes24k|224|21004.9|536.8|0.028315|0.033923|
|verifact_ref|224|7454.1|499.8|0.013430|0.013430|
|chunks24k|224|21001.4|572.6|0.028773|0.034079|

实际同body/长度不是名义上的不同臂：开发72条中chunks24k=notes24k为43条、notes24k=ehr_all为45条；确认224条中chunks24k=notes24k为90条、notes24k=ehr_all为92条。chunks24k/notes24k最大离散token缺口分别199/115；没有截断notes24k以凑长度。确认实际API输入notes24k−chunks24k平均3.53 tokens、P95为15、最大115，长度对照有效。自然192条首次API平均输入verifact_ref/compact48/chunks24k/notes24k为7452/2950/21053/21057 tokens；无缓存每例约0.01331/0.00646/0.03419/0.03404元，notes24k约compact48的5.27倍而没有实用优势。[实际输入与操作](input_operation_summary.json)。

完整覆盖[coverage.csv](coverage.csv)、三类P/R/F1/混淆/预测S假发现率与作者分层[detailed_tables.md](detailed_tables.md)单列；自然冻结192，verifact_ref/compact48/chunks24k/notes24k有效190/192/191/191，主共同189。压力32共同32，重复16共同15。无效不补旧答案或NA、不重发。

098此前已发生及未知¥5.027330不占新额度，原未知预留仍留原账；098原任务累计¥25.638760/50。本指令新增098 ¥20.611429＋100 ¥25.252259＝**¥45.863688/130**；100未知¥0.000000。逐次发送均先预留，未优惠目录价结算，重试/在途/未知不清零；099历史额度未叠加。[总账](cost_ledger.json)。不是账户实扣账单，无GPU租金。

## 自检与解释边界

使用统一evaluate/paired_compare和1000次患者配对bootstrap，独立混淆矩阵/sklearn/Decimal复核；不是独立调查者或医生审计。GT面对完整参考EHR，本轮all是冻结合法日历范围内全部notes，不能冒充患者终身记录。32名患者隔离只消除本轮开发患者重叠，不覆盖历史开发选择或新医院泛化。raw改判不是内部推理或新医生GT。[执行者自检](selfcheck.json)。

确认失败或仅点值改善，不通过追加同面板/更改24K/换样本救成绩；完成本轮后不自动启动新实验。

<!-- Frozen source: report.md; SHA256: b9f7d716a4f85697d6712056715224bdd3de0b1e11e7406ef62701f7c0d029ef; presentation-only naming update 2026-10-27. -->
