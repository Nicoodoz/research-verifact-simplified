# 026 成果入口

必读：[中文主报告](report.md)。当前状态：[CURRENT_STATUS](CURRENT_STATUS.md)；执行结束、门槛未通过，待独立审计。

| 材料 | 内容 |
|---|---|
| protocol_001.md | 发送前协议与停止门槛 |
| gate_freeze/ | 仅在024十患者训练的最终SD参数、训练ID和来源指纹 |
| preparation_001/ | 019原650条输入、1950个请求模板、模型及价格登记；Qwen模板不代表全量发送 |
| candidate_freeze/ | DeepSeek完成后、Qwen发送前冻结的52候选，生成不读GT |
| attempts/ | 1352个真实原始请求及HTTP回执，含usage |
| analysis_001/ | 002评价、完整frontier、650条预测、RHW、患者及作者结果、成本、输入输出指纹 |
| supplement_001/ | 作者内风险参考、逐条改对/改错汇总、成本分臂、计算环境 |
| figures_001/ | 完整risk–rescue及局部放大，PNG/SVG |
| verification_001/ | 执行者自检、7项测试、独立LP核验；不是独立审计 |
| audit_handoff.md | 审计重点、安全离线重放、代码与成果快照入口 |

不运行收费runner来复查。不覆盖任何冻结目录。新增调用已停止。
