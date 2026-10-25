# 045：Semantic Recovery Route Screen

## 目的

045不做大样本确认，只在16条development诊断病例上筛选真正不同的改进路线。允许新增API调用；限制的是研究支出而不是部署链复杂度。

核心问题：
- A：不改证据，只修正Judge的核验范围，能否减少“额外要求/NS-NA混淆”？
- B：LLM是否能从已有增量候选包中语义选择真正有用的证据？
- C：利用原Judge初判reason生成定向查询，再对同次住院EHR补检，是否优于静态候选？
- D：同一C48直接换Qwen Judge，是否已经足以改善结果？

本轮总收费API保护上限：人民币8元。第一批16条结束后即停止；不自动进入第二批。

## 队列

从044的8名development evaluation患者中选择16条，全部已被使用，不构成新验证集。

固定配额：
- base错误8条：GT Supported 4、Not Supported 2、Not Addressed 2；
- base正确保护对照8条：同样4/2/2；
- 每个类别尽量human/LLM各半；
- 同一患者最多3条；
- 候选在满足配额后按固定sha256哈希选择。

选择依据只使用044已冻结base结果、医生GT、author/patient信息；不使用045任何新结果。
## 路线

Baseline：复用044 round0 base回答，不收费重跑。另固定4条做同输入DeepSeek repeat，仅用于运行波动诊断。

A Prompt scope：
- C48完全不变；
- DeepSeek仍为0731；
- 增加一条明确规则：只核验claim实际陈述的必要成分；后续变化不自动否定早期时间点；计划不等于完成；可能/建议不自动等于确定事实；缺失与矛盾分开。
- 单次调用。

B Semantic bundle selection：
- Qwen只看claim、原C48和三个044冻结增量包的“新增原文”；
- 只输出 none / rank / complement / time，不判断最终标签，不看GT；
- 选none则直接复用baseline；否则把所选原文追加到C48，再由原DeepSeek终判。
- 最多两次LLM调用。

C Feedback targeted retrieval：
- 复用baseline verdict/reason/checks作为反馈；
- Qwen读取claim、base reference和baseline回答，输出1–2条检索查询与“需要确认的事实/关系”，不输出最终标签；
- 对同患者、目标住院日期范围内的031 corpus做本地BM25；
- 排除与C48正文精确重复，取最多2段、追加正文最多1500字符；
- 原DeepSeek对补检后的reference终判。
- Baseline已复用，因此每条新增两次LLM调用：gap/query + final Judge。

D Alternate Judge：
- Qwen3.8-27b在原C48上按同样三标签定义直接输出verdict/reason/checks/label_scores；
- 单次调用。
## 评价

第一轮只做方法筛选，不计算或宣称总体benchmark性能。

每条以医生GT判断：
- rescue：base错，路线对；
- harm：base对，路线错；
- unchanged wrong/correct；
- 分GT类别、author、patient报告。

同时报告：
- 路线实际改变标签的数量；
- 对发生标签变化的输出检查reason是否与自身verdict一致，引用是否来自实际reference；
- C路线检索到的新passage、query及其是否被终判reason使用；
- 每路线实际API调用数、prompt/completion token和usage估算费用。

晋级不是显著性检验。优先保留：
1. rescue > harm；
2. 没有明显把NS/NA普遍推向Supported；
3. 成功案例的reason确实利用新增/已有证据而非无依据改判；
4. 效果相近时优先简单、便宜路线。

本轮不以自动审计结果覆盖医生GT分类收益。自动审计如使用，仅作为解释质量辅助信号。

## 完整性

045所有输入、选择、请求body和回执写入独立任务目录，不修改044冻结artifact。HTTP200不因结果重跑；无receipt未知请求不自动重发。执行者核验与独立审计分开。
