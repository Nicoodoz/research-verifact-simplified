# 033 成果入口

**完成执行及自检，待独立审计。** 本次033研究训练患者组成，不是已撤回的reserved实验。

- [中文主报告](report.md)、[当前状态](CURRENT_STATUS.md)
- [冻结协议](preparation_001/protocol.md)、[输入/环境指纹](preparation_001/manifest.json)
- [原141轮](historical_001/all141_sweeps.csv)、[1452固定训练集合](historical_001/training_sets.csv)、[原实际held记录](historical_001/original_observed_units.csv)
- [统一搜索面板训练subset排名](training_subset_ranking.csv)、[逐模型逐患者](historical_001/patient_metrics.csv)
- [患者入选关联](association_001/common_panel_inclusion_by_size.csv)、[高表现集合入选频率](supplement_001/top_decile_membership.csv)
- [定向计划](search_001/directed_plan.json)、[选择冻结](search_001/selection_freeze.json)
- [完整development跨患者评价](evaluation_001/metrics.csv)、[配对比较](evaluation_001/paired.json)、[同风险比较](evaluation_001/matched.json)
- [正式图表](figures_002)、[推荐模型/名单](recommendation_001/recommendation.json)
- [执行者自检](verification_001/checks.json)、[audit handoff](audit_handoff.md)、[交审指纹](handoff_001/manifest.json)

不把多模型OOF轮次当固定名单；不把原16+搜索12上的选优汇总当无偏验证。所有资料只涉及development，0新增API，没有reserved结果。
