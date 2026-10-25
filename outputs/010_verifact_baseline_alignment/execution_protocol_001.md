# 010执行前固定协议

## 科研目标与两层比较

本任务是baseline校准，不开发packaging方法。沿用009确认650条valid atomic claims，原开发哈希顺序第19–24名：59250、93640、15057、27036、59840、66218；LLM243（S/NS/NA=228/10/5）、human407（313/27/67）。这些患者已有逐例分析，010不是独立新患者验证。保留其余16名开发和40名reserved test，不重抽。

第一层：按原proposition_id、rater配置和reference_id从本地release提取原R1-70B发布预测；配置固定rater-121，sentence facts N100、rerank、absolute_time、current admission、deduplicate=True。逐条与002导出预测交叉核对，reference payload SHA256与ID一致。与009 A48/C48在同650条上按002默认口径并列。这是same-cohort system reference，不把不同系统／模型的差值称检索效果。

第二层主要比较方向为 **verifact_reference − c48_reference**，两个作者分别报告。两臂原claim、GT不变；完整reference直接取各自实际保存文本，不裁长、不重新排序、不改metadata、不添加来源BHC。保留实际差异（发布约100 sentence facts、C48约12个完整片段及其note信息），因此不是等输入token或单一packaging变量对照。对差异原因只作分层诊断，不能以本实验宣布某一种格式导致全部收益。

## Judge与输入复用

沿用009冻结common＋structured提示与同一JSON schema、deepseek-ai/DeepSeek-V4-Flash、temperature=0、enable_thinking=false、max_tokens=2048、n=1、stream=false；只发送proposition和reference。模型别名相同不保证不可变权重，也不假定temperature=0确定性。

为了同期比较，650×2主条件都在010重新生成，不拿旧009 C48答案作为同期对照。无需重新计算索引、embedding、候选或rerank。C48每条完整body与009核对一致；旧C48预测留作同输入跨运行波动诊断，不替换010答案。

所有主完整body在调用前去重、同body共享canonical。另在每患者/作者按SHA256(010/repeat/v1: + proposition_id)取1条、两套reference各重复1次，共24次，仅诊断波动。合计1324个请求（当前1300 canonical无相互重复）。按独立固定哈希混合请求顺序，同时使用4并发，不先跑完整一臂再跑另一臂。重复永不覆盖canonical。

## 评价与完整性

调用002 evaluate/paired_compare，valid-only、三分类micro PA/AC1/MCC、1000次患者cluster bootstrap、作者分开；类别precision/recall/F1、正确/错误转移、逐患者结果和实际分母全保存。第一层不孤立归因。第二层配对只要求同一完整作者队列，缺失则受影响的主比较明确受阻；可以另报预登记的两臂共同完整项敏感性，保存排除ID/覆盖/指纹，不能替代完整主结果。HTTP200即终止，即使截断或解析失败也不补标签、不重生成。

证据诊断先做650条全文长度、编号数、日期与显式note信息的描述；发布reference缺少note ID时不把无法确定note覆盖当成0，也不靠关键词率充当医学gold。深入阅读预先纳入009同队列典型病例N071/N293/N302/N394/N430/N527/N561/N563/N585/N644；再按作者/改善/退化/仍错固定哈希选最多2例，加入各作者稳定正确/稳定错误且reference改变的对照。若某类无例实报，不为了故事删除例子。重复问题N119可作补充。完整输入与不同完整生成输出一起查，观察、解释、不确定性分开；相同EHR事实可合并显示，但保留各reference的编号和完整映射。

不做补回／移除、格式重写或新的打包臂。报告要回答原009证据损失在发布reference中是否仍有、优势是否更多来自内容/数量/时间/身份可用性、Judge支持范围仍有什么问题。单例锚点不是新医生gold，原标签与恢复语境的正确性分开。

## 费用、恢复和授权

按用户交办010及AGENTS长期授权，预计¥33.049（峰时、按完整消息字符×0.4近似输入tokens＋每答400输出tokens，无缓存优惠）；不是精确token计数、费用承诺或账单。全任务只有一个judge阶段，固定上限¥40，全部账号、主比较、24次重复和必要重试合计，不新增子阶段重置。没有付费预检、其他服务或新planner。预算不足或服务配置错误时停止新增付费工作并完成能做的离线分析。

采用009已审计调度逻辑的010独立副本，仅切换路径/任务身份；不修改009。发前按UTF8字节与最大2048输出保守预占，回执usage按有日期价格结算；未知结果保留预占。所有回执与阶段输入指纹不可覆盖，恢复先读取已写成功回执；不删除回执来生成更好答案。

明确无答案402/code30001可换下一账号重试原请求；408/429/5xx最多3次相同发送，未知结果最多2次、旧预留仍计入；单请求总尝试最多12。每批遇暂时错误等待20秒，最终缺失保留且继续尚未发送任务。非暂时配置错误暂停。4并发、任务锁及阶段锁防止重复运行；HTTP200无论好坏不重发。

官方价格于2026-09-15核对：[日期公告](https://docs.siliconflow.cn/docs/release-notes/overview)、[价格页](https://siliconflow.cn/pricing)。V4-Flash峰时缓存命中/非命中输入/输出为0.3/3/9元每百万token，北京02–08点为0.15/1.5/4.5；代码沿用此日期规则。9月15日起repetition_penalty被忽略，但本任务未设置该字段。账号只读本地.env.siliconflow_pool，不记录key或其指纹，不调用余额接口。

运行前绑定输入、计算代码、预算与协议指纹。根README、AGENTS、审计和状态文档是可变快照，不阻断已有回执离线评分；冻结实验材料和回执仍严格校验。结束后主报告、版本/未提交修改及文件清单交独立Codex审计，执行者不写PASS、不改旧审计、不扩展实验。
