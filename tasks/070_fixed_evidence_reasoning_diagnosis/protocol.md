# 070：固定证据下的 LLM 判断差异诊断（零 API）

## 问题与边界

保持 053/066 的 C48→final reference、原有模型回答和 Frozen PriorG 不变。只做 development 内部诊断，不新增检索、模型调用、prompt、路由器、后处理参数或 reserved 开发。066 的 Observed Reasoning Oracle 是事后用医生 GT 在已有判断中选对的上限，不能作为可部署成绩或可学习路由监督。

## 固定分析口径

1. 以 053 的 240 条为完整自然队列。主同输入比较限于 T-S 核心有效且有 Qwen 原生 label_scores 的 237 条；另报告 3 条 T-S 无效的固定回退，不把缺失 Qwen 预测填标签。验证每条 N-S、T-S、Qwen 实际请求的 proposition 与完整 reference 一致，并记录模型、thinking、scoring 设置与回答来源。若有不一致，退出“同证据”归因并逐 ID 披露。
2. 固定四个判断：DeepSeek non-thinking scoring U0（NS_U0）、DeepSeek thinking-high scoring 原生 verdict（TS_raw）、Qwen non-thinking scoring 的 score argmax（Qwen_U0）、T-S scores＋冻结 PriorG（TS_PriorG）。分别报告完整同 ID 的 PA/AC1/MCC、false-S、类别召回、相对 TS_PriorG 的 rescue/harm/net 与患者聚类配对区间；再列作者、GT 类别与患者分布。不得从中事后选“最佳方法”。
3. 对基准 39 错中 14 条有其他判断答对的病例，逐条记录成功者、是否唯一成功、原生 verdict/score argmax 是否分歧、T-S 分数与 PriorG 边界、完整 reference 指纹和实际输出/引用。并对原先正确的病例统计同一候选会造成的 harm，防止只读成功病例。
4. 检索已有同请求体的独立回执和事先固定的 repeat。精确区分独立重复调用与同一答案的缓存/复用；只有原包/候选在相同输入和设置下重复支持的个案才可称观察到重复，不把单次正确称稳定。跨任务不同证据、模型快照或配置不合并为同输入重复。
5. 定性归因只作候选解释：按 claim 的完整支持、事件状态、时间/范围、确定性、NS/NA 边界、其他/无法判断编码；同时分辨“同一个 T-S raw 被 PriorG 改坏”的确定性决策边界、跨模型/模式的判断差异，以及引用/解释能否支持该标签。引用、reason、reasoning_content 不能证明内部机制；医生标签不是新增 passage-level gold。每条保留足够原文和实际输出的可回查路径，不在简报中大量抄录临床文本。

## 决策

只有当同一具体语义机制在多个病例和患者中重复出现、较少依赖单次边界翻转、且固定候选的总体 harm 不吞没 rescue，才推荐一个后续受控推理实验。否则建议停止或收缩到病例定义/标签契约诊断。后续实验建议须说明要区分的两种解释、继续/停止结果；本任务不实现、不自动启动 071。

## 交付

保存来源/口径校验、全队列配对评价、14 条逐例台账、重复证据核查、中文报告和执行者自检。无收费 API、无 commit/push。
