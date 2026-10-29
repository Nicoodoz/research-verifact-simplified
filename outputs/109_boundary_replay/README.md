# 109真实困难边界回放

[最终报告](final_report.md) · [完整指标](comparison.json) · [类别/患者/作者分析](analysis_details.json) · [真实选样](mining_summary.json) · [执行自检](execution_selfcheck.json) · [费用与关机](execution_cost.json) · [当前状态](../../tasks/109_boundary_replay/CURRENT.md)。

当前固定配方无效，停止扩大。自然400条MCC0.5032→0.3733、PA79.75%→72%、false-S12→11；压力100条MCC0.3123→−0.1091、PA58%→38%、false-S16→16。NA严重转判NS，候选500条仅预测1条NA。

527条真实训练池预测、192条/24步续训和完整500评价均完成。用户确认11:35关机，GPU租金估算¥1.896、API0；最终适配器、完整optimizer与原始结果已私有回传。

[原无卡准备报告](preparation_report.md)保留其形成时范围。完整去原文候选/排除索引见[完整109归档](https://github.com/Nicoodoz/research-verifact/tree/main/outputs/109_boundary_replay)。临床原文、私有回执、凭据、模型和缓存不进入任一仓库。
