# 050：Repeated Scoring Aggregation

050研究完全相同DeepSeek scoring prompt重复调用后的label_scores稳定性，以及固定3-run聚合能否稳定U2。

Screen为32条、每条6次完全相同scoring调用；无聚合规则达到预设稳定性+性能门槛，因此58条患者隔离confirmation按协议不执行。

结果见 `../../outputs/050_repeated_score_aggregation/report.md` 与 `CURRENT_STATUS.md`；executor verification见 `verification_001.json`，独立审计未执行。
