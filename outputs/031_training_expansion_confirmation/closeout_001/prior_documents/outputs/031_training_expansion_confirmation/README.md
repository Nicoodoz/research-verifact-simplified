# 031 结果与执行入口

当前仍在执行固定训练扩充/确认流程，最终科学结论以完成后的report.md为准；不提前声明方法成功或独立审计PASS。

- [事前协议](protocol_001.md)
- [GT盲患者分组](planning_001/split.json) · [2146条新增claim计数](planning_001/counts.json)
- [C48缓存与原链路材料](materials_001/) · [最终预算情景](freeze_001/budget_002.json)
- [四套扩充前模型](before_models/) · 后续[扩充后模型](after_models/)
- [API进度](execution_status.json) · [工作流状态](workflow_status.json) · [原始请求/回执](attempts/)
- [account_2鉴权失败后的用户换号授权](account_override_001.json) · [TPM限流后的发送节奏记录](pacing_amendment_001.json)
- [GT盲确认预测冻结](inference_001/) · [确认评价](analysis_001/) · [费用及独立运行角色成本](costs_001/)

原16人完整信息直接复用029；新增24人按固定ID哈希分为扩充12/确认12，不使用reserved40。API累计80元，含失败/重试/未知/在途；401不是余额耗尽，所有历史失败仍保留。限速仅改变发送节奏，不修改模型、证据、prompt或科研规则。

读取确认GT之前必须保存八套模型和全确认预测。辅助角色缺失按各方案预设退U0；主评分缺失则明确无U0，不伪造预测或只报成功子集。

原主环境保持不变。隔离环境新增依赖记录见[environment_additions_001.json](environment_additions_001.json)。不自动commit/push、032或reserved40。
