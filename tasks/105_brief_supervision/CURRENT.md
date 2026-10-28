# 105当前入口：完整执行与最终分析完成

用户已确认GPU关机。两臂各196条×2轮、50步/392次消费；base_judge、label_only、evidence_brief各500条首次回执均完成。最终适配器和原始结果已回传核验，无自动关机、无新增API。

**停止当前evidence_brief配方扩大。** 相对同样本label_only，自然共同390条MCC−0.1209、PA−6.67个百分点、false-S17→19/78；压力94条MCC−0.2166、false-S16→23/94。NA损失明显；仅两臂的399/100条敏感性结论仍为负。压力共同有效覆盖94%另未达95%线，不把基线截断变成方法失败的唯一解释。

正式入口：[最终报告](../../outputs/105_brief_supervision/final_report.md)、[指标附录](../../outputs/105_brief_supervision/final_metrics.md)、[源文案例](../../outputs/105_brief_supervision/final_case_analysis.md)、[执行者自检](../../outputs/105_brief_supervision/final_selfcheck.json)。历史[镜像准备](../../outputs/105_brief_supervision/system_image_report.md)、[克隆阻塞](../../outputs/105_brief_supervision/gpu_clone_report.md)与[协议](protocol.md)保留，不代表当前仍未执行。

本地私有结果`.local_models/105_brief_supervision/a800/evidence/`；最终适配器在同级`backup/<arm>/checkpoint_a/`。实例持久路径`/root/autodl-tmp/verifact105/results/train/<arm>/checkpoint_a/`，完整optimizer留在实例，不是本地完整恢复备份。原基础模型与源盘数据未在本次执行删除。

最后可见累计费用¥16.572010＋2元共享未知余量；用户确认已关机，精确平台停机时间/旧区间账单未提供，不能冒称结算。原20元/150分钟账本保留，后续另需明确授权，不自动启动下一任务或重训。
