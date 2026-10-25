# 023成果入口

**执行与自检完成，待独立审计。** 本任务是固定λ=2的离线响应/敏感性分析，不产生新winner；0新增API，不改λ、API路由或历史019–022，不使用reserved40。

唯一必读[中文主报告](report.md)，明确回答Q1–Q7。

- [Figure 1：性能响应PDF](figures_001/figure1_performance.pdf) · [SVG](figures_001/figure1_performance.svg) · [PNG](figures_001/figure1_performance.png)
- [Figure 2：收益—风险PDF](figures_001/figure2_tradeoff.pdf) · [SVG](figures_001/figure2_tradeoff.svg) · [PNG](figures_001/figure2_tradeoff.png)
- [Figure S1：作者MCC](figures_001/figureS1_author_MCC.pdf)
- [统计附录](statistics.md)、[401点机器结果](analysis_001/dense_grid.csv)、[精确状态](analysis_001/exact_states.csv)、[患者曲线](analysis_001/patient_curves.csv)。
- [输入来源](preparation_001/source_manifest.json)、[锚点完整性门](preparation_001/anchor_checks.json)、[冻结方案](protocol_001.md)。
- [审计交接](audit_handoff.md)、[自检](verification_001/summary.json)、[当前状态](CURRENT_STATUS.md)。

三组均有约1.946–2.079的同标签平台，±0.05不改判；更宽区域存在风险代价和跨轮峰位漂移。023结束后停止，不自行启动024、重选参数或最终测试。
