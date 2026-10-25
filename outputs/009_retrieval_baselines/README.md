# 009 成果入口

状态阅读提示：report.md、paper_draft.md、audit_handoff.md和revision_001/README.md保留执行／交审时原文；其中“等待独立复核”、143项测试及旧HEAD不是当前状态。009审计开头和中段也保留初审历史，当前以其末尾2026-09-15修订PASS为准。研究数值与限制不变。

**唯一必读：[简明中文主报告](report.md)。** 009 已完成执行、真实实验、证据干预、独立审计及2026-09-15修订定向复核；原重放阻塞关闭，可正式冻结／结项。

建议C48作为暂定实用baseline，A48保留为对照；纯dense在人写组退化。C−A的LLM/human ΔMCC为+0.0002/+0.0158，未证明稳定优势。优先证据组织和Judge支持边界，暂缓扩大通用planner。6名新开发患者全部650条有效命题、三臂完整；总费用估算¥18.0822／40元，非账单。

|材料|入口与用途|
|---|---|
|可选论文写作|[设置、结果、讨论和相关工作草稿](paper_draft.md)；[全精度核心／类别／逐患者数表](synthesis_001/)|
|当前独立结论／修订被审版本|[审计末尾修订PASS](../../reviews/009_retrieval_baselines.md)；[revision_001清单（当时被审快照）](revision_001/handoff.json)|
|首次交审历史|[旧交审入口](audit_handoff.md)；[handoff_001历史清单](handoff_001.json)|
|执行前协议|[总协议](execution_protocol_001.md)、[开发重排刷新登记](execution_amendment_001.md)、[确认冻结](confirmation_protocol_001.json)|
|旧开发|[144条评分](development_001/analysis_001/)、[15例完整阅读](development_001/review_001/semantic_001/)|
|新确认|[650条评分](confirmation_001/analysis_001/)、[全量损失表](confirmation_001/loss_map_001/)、[35例完整阅读](confirmation_001/review_002/semantic_001/)、[定向原文追溯](confirmation_001/targeted_trace_001/records.json)|
|事后干预|[9例解释与限制](interventions_001/interpretation.md)、[53条件结果](interventions_001/analysis_001/case_results.json)、[冻结输入与控制](interventions_001/preparation/)|
|费用和回执|[任务合计账本](synthesis_001/costs.json)、[各阶段原生回执](live/)|
|当前修订验证|[146项断网测试／109文件重放](revision_001/verification_001/verification.json)；[测试日志](revision_001/verification_001/tests.log)|
|首次验证历史|[143项测试](verification_001/verification.json)|
|继续使用baseline|[配置](../../tasks/009_retrieval_baselines/baseline_config.json)、[纯本地接口](../../tasks/009_retrieval_baselines/retrieval_baseline.py)、[任务和使用说明](../../tasks/009_retrieval_baselines/README.md)|

所有历史run和原回答保留；上述“执行自查”不等于独立审计。开发最初评分遇输出路径错误后的完成记录见 `development_001/analysis_completion.json`，已生成内容与重放一致，不影响主指标；原检查日志保留。复核期间停止改动同批成果。

## 当前重放修订入口

009初审有条件通过及原阻塞记录保留；针对正常审计索引更新阻塞重放的问题，2026-09-15修订定向独立复核已通过，当前结论见[审计末尾](../../reviews/009_retrieval_baselines.md)。请审阅[revision_001修订说明](revision_001/README.md)及[最新被审版本](revision_001/handoff.json)；上表handoff_001为历史首次交审版本，revision_001清单也只表示当时被审字节，不要求以后正常入口／审计追加仍与它一致。原主报告、预测、指标和费用均未修改，本次没有API调用。
