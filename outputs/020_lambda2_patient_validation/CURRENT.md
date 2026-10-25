# 020 当前状态

**状态：执行与冻结分析完成，待独立审计。**

020固定019开发网格中事后候选 λ=2，在003 development顺序最后10名患者的879条valid atomic claims上完成两轮同期验证。Embedding 129/129、rerank 879/879、Judge 3516/3516完整。

总体all-micro结果：
- R0：B PA 72.92%、MCC 0.5268；U2 PA 81.68%、MCC 0.5960；O PA 76.68%、MCC 0.5022。
- R1：B PA 71.90%、MCC 0.5080；U2 PA 80.55%、MCC 0.5711；O PA 76.68%、MCC 0.5022。
- U2相对B、U0、O的总体PA/MCC患者bootstrap差值在两轮均为正，95%区间下界均>0。

边界：false-S相对B增加，NS正确数下降；LLM子组因263/269为S且MCC跨轮不一致，不能称所有子组都稳定更优。U2离线改标签不自动改reason。

费用/服务：3523次Judge发送尝试，3516个逻辑请求完整；最终回答全部来自siliconflow/account_2。累计usage估算及未知预留44.28450852元/80元，无账号明确额度耗尽，无阿里云切换。

40名reserved test未使用。40名development现均已用于开发/确认；是否开启reserved test必须另行冻结方法和评价。

正式入口：
- 主报告：report.md
- 统计附录：statistics.md
- 机器指标：analysis_001/
- 审计交接：audit_handoff.md

本页与主报告属于执行者收尾，不是独立审计PASS。
