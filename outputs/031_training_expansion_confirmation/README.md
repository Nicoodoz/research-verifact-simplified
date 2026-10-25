# 031 成果入口

**执行及执行者自检完成，待独立审计。** 以[中文主报告](report.md)和[CURRENT_STATUS](CURRENT_STATUS.md)为准：没有确认扩大训练或repeat/trace的实质增量，停止当前版本，不自动后续。

- [冻结协议](protocol_001.md)、[患者划分](planning_001/split.json)、[输入配置](freeze_001/manifest.json)
- [八模型及确认预测冻结](inference_001/manifest.json)、[完整评价](analysis_001/manifest.json)
- [角色/异常/时段](execution_diagnostics_001/summary.json)、[费用账本](costs_001/costs.json)
- [图表](figures_002/risk_rescue.png)、[执行者自检](verification_001/checks.json)
- [audit handoff及离线入口](audit_handoff.md)、[最终指纹](handoff_001/manifest.json)

attempts保留全部原生请求和回执；失败、粗预算、环境及IO修订、初次绘图和运行中状态均保留。历史快照中的running/pending只代表形成时状态，当前以本页和closeout_001为准。
