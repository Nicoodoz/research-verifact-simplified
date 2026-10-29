# 自主研究周期1

CLOSED_NO_QUALIFYING_GAIN。自主研究周期1已收束，未达到主要提升目标，保留107 label_only。六项候选及全部失败结果已留存：claim_repeat在1817条仅MCC+0.00730、正确+7、false-S+1；最后gentle_refresh固定25步在180条也出现NA损失及false-S增加，停止扩大。未使用确认40人，未改变默认系统。GPU计算及关键回传完成，实例按用户政策未关机、留机仍计费。

实际收束：2026-10-29 22:50:38（北京时间）；授权最迟截止2026-10-30 07:47:16，不为用完额度延长。此次费用快照约¥4.829，API0；未自动关机。

最后一项gentle_refresh：107权重和Adam状态，原JSON/分段loss，114第二196条，固定2e-5、25步。自然120：MCC0.4078→0.3711、正确86→89、false-S4→6/24；压力60：MCC0.3069→0.2933、正确35→34、false-S7→11/60。NA净损失8/14，不能以S/NS救回掩盖。停止500扩展及参数追加。

本地完整模型状态：`.local_models/116_research_cycle/evidence/gentle_refresh/best_model/`和`single_token_768/best_model/`。全部原始回执与日志在同一evidence目录；私有内容不入Git。没有正在运行的116 GPU任务，不重复启动。

[报告](../../outputs/116_research_cycle/report.md) · [周期状态](../../outputs/116_research_cycle/cycle_state.json) · [备忘](memo.md)。
