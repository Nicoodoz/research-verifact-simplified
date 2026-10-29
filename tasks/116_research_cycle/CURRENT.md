# 自主研究周期1

ACTIVE。周期为2026-10-29 19:47:16至2026-10-30 07:47:16（北京时间），最长12小时；同一32GB GPU按1.58元/小时，GPU/API分别累计上限20元，跨子试验不重置。周期结束保存并通知，不自动关机。

已完成：joint_path原180条，正确S损失明显，停止扩大；claim_repeat完整1817条相对107 MCC+0.00730、正确+7、false-S+1，仅保留为低成本开发辅助信号，未达到主要目标。107仍是维护基线。

当前：single_token_768已按用户时间优先暂停在24步，实际梯度31人192条，另8人128条用于内部验证；选中第24步。single_token_short_pilot已完成：自然120正确+9、false-S-1；压力60正确-2、false-S+2。当前冻结24步权重，补齐旧500中的430条；不追加训练。三类固定token判别是唯一主任务，没有辅助loss。全部确认40人尚未用于本周期选型或确认。

当前远端任务/PID与恢复信息在`.local_models/116_research_cycle/`；不要重复启动。新候选有实质开发收益后才冻结，并至多一次使用后40人确认。

[备忘](memo.md) · [阶段报告](../../outputs/116_research_cycle/report.md) · [周期状态](../../outputs/116_research_cycle/cycle_state.json) · [实时进度](../../outputs/116_research_cycle/实时进度.md)。
