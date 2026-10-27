# 今晚结论：098与100〔名称阅读版〕

2026-10-27仅统一方案展示名称；[冻结原报告](night_summary.md)、预测、数值、判据及计算口径均保留。原报告的阶段状态仍按结项时记录解释。

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

**最终选择：失败停止。** 100实际分支为evidence，晋级方案为notes24k。

098已完整完成全部2120目标请求，另2次demo_lenmatch构造；demo_protect对verifact_ref/demo_lenmatch/compact48分别通过=False/False/False。压力/重复及三类代价详见098报告，未把未跑完当阴性，也未只赢verifact_ref就声称保护机制成立。

100采用事前预算降档：开发48自然+24压力（42人），确认预冻192自然+32压力（32人），固定重复16。开发/确认患者隔离，均有历史研究暴露；方法和规模未按新成绩调整。

实际最后执行阶段：confirmation。自然同ID表：

|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|
|---|---:|---:|---:|---:|---|
|compact48|0.4778|77.78%|147/189|6/37|53.8%/58.3%|
|notes24k|0.4584|78.31%|148/189|6/37|46.2%/41.7%|
|verifact_ref|0.4789|77.78%|147/189|4/37|53.8%/50.0%|
|paper_r1|0.4066|79.89%|151/189|14/37|30.8%/37.5%|
|chunks24k|0.4707|77.78%|147/189|6/37|53.8%/50.0%|

自然与额外NS/NA分开；完整压力、救回/伤害、患者95%区间、重复与human/LLM在[正式报告](report_display.md)和阶段analysis。默认Judge/原GT/原始数据未改变，没有PriorG或GPU部署。

新增费用：098续跑¥20.611429，100 ¥25.252259，合计¥45.863688/130；100未知预留¥0.000000，旧098未知仍保留原账。未为花完预算追加方法或样本。

明天最值得做的一个动作：拿这张同模型确认表与导师收敛论文主线，明确demo_protect和本版24K完整note路线停止；不再凭开发阳性追加投入。

<!-- Frozen source: night_summary.md; SHA256: 865121f7136d68253fc5619958d9cc0ce76d53faaef532378fed2956be3136b0; presentation-only naming update 2026-10-27. -->
