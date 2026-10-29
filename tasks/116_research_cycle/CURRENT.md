# 自主研究周期1

ACTIVE。周期为2026-10-29 19:47:16至2026-10-30 07:47:16（北京时间），最长12小时；同一32GB GPU按1.58元/小时，GPU/API分别累计上限20元，跨子试验不重置。周期结束保存并通知，不自动关机。

已完成：joint_path原180条，正确S损失明显，停止扩大；claim_repeat完整1817条相对107 MCC+0.00730、正确+7、false-S+1，仅保留为低成本开发辅助信号，未达到主要目标。107仍是维护基线。

当前：single_token_768已按用户时间优先暂停在24步，实际梯度31人192条，另8人128条用于内部验证；选中第24步。single_token_short_pilot已完成：自然120正确+9、false-S-1；压力60正确-2、false-S+2。完整500已显示自然MCC-0.04324、false-S+9，压力MCC-0.04552、false-S+6，停止该配方。冻结107三代码读出也未通过：自然正确+9但压力正确-7、false-S+5，停止该读出配方。support_check在180仅净多3正确、两面板MCC正且false-S不变，是边界信号；当前GPU补齐500中的430条，不宣称阳性。gentle_refresh已用CPU准备，但未启动。三类固定token判别是唯一主任务，没有辅助loss。全部确认40人尚未用于本周期选型或确认。

support_check已补齐500：自然MCC-0.01136、正确-5、false-S-1；压力正确+1、false-S-1，停止扩大。gentle_refresh已实际启动：从107权重与Adam状态继续固定25步、2e-5，原接口与主loss不变，随后同一加载直接筛查180。真实最长12220 tokens backward通过，峰值约24.63GiB，显存余量约6.53GiB；源50步/392条状态已加载，学习率确为2e-5。工程检查不表示有效。

当前远端任务/PID与恢复信息在`.local_models/116_research_cycle/`；不要重复启动。新候选有实质开发收益后才冻结，并至多一次使用后40人确认。

[备忘](memo.md) · [阶段报告](../../outputs/116_research_cycle/report.md) · [周期状态](../../outputs/116_research_cycle/cycle_state.json) · [实时进度](../../outputs/116_research_cycle/实时进度.md)。
