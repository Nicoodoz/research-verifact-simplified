# 017成果入口

**第一阶段未达门槛，停止；尚未独立审计。**

唯一必读：[中文主报告](report.md)。192条GT盲等额样本、12名已暴露患者；19条稳定错误中0条稳定rescue，160条稳定正确中3条稳定harm；训练组2个非零utility配对。错误覆盖也低于预设24条，不将结果泛化成所有utility learning无效。

未训练selector，未启动patient-disjoint模型选择或剩余10人确认；reserved test未使用。总费估算加未知预留¥13.37319060／¥80，1574次尝试、1572有效回答；全程SiliconFlow account_2，2份HTTP400及原样重试记录保留。

| 入口 | 内容 |
|---|---|
| [事前协议](protocol_001.md)、[执行登记](execution_policy_001.json) | GT盲动作、阶段门槛、80元累计保护、路由规则 |
| [冻结输入](preparation_001/manifest.json) | 样本、候选、特征、完整请求、重复／共享映射 |
| [完整分析](analysis_001/summary.json)、[门槛](analysis_001/gate.json) | 全192条、两轮、002评价与明确停止决定 |
| [弱监督台账](analysis_001/utility_events.csv)、[病例并集](analysis_001/cases.csv) | 576个动作事件、稳定性、rescue／harm及保留理由 |
| [请求回执索引](analysis_001/attempts.csv)、[预测来源](analysis_001/canonical_provenance.csv) | 所有尝试／费用和1920逻辑条件来源；原始回执在live/headroom |
| [离线重放](verification_001/summary.json) | 32份机器结果逐字节一致，受保护历史未变 |
| [主报告重放](verification_report_001/report_sources.json) | 当前renderer与来源指纹；初版渲染登记保留 |
| [相关工作](related_work.md) | utility／下游反馈／弱监督检索的已有关系，不主张utility首创 |
| [审计交接](audit_handoff.md) | 交审HEAD、未提交状态、检查范围与限制；最终指纹见handoff_001.json |

`learning_001`与`confirmation_001`不存在是按门槛停止的结果，不是遗失成果。原始001–016材料和医生标签不改写，不补抽样本或重跑答案。
