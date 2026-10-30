# 132 midpoint_update

固定alpha=0.5的107／120有效更新中点已构造，160条初筛已全部回传并通过预定扩展条件。没有新增训练。下一步为原500条中的340条补缺；原160条不重发。

约21:20传输扩展包时SSH断开，随后同一端口拒绝连接。扩展尚未启动，用户已明确确认实例关机。未发送关机命令；具体关机时刻和最终租金未知，不把连接拒绝当作计费截止。

[协议](PROTOCOL.md) · [阶段结果](../../outputs/132_midpoint_update/report.md) · [160条指标](../../outputs/132_midpoint_update/screen160.md)。

当前实例上保留源107、120与132适配器；本地也有完整132适配器与160条回执。后续新授权：2026-10-30 22:15开机，GPU预算19元，仍按1.58元/小时；API累计80元额度已用0。已在新实例启动340条补缺，复用原160条。新session与运行包位于私有`instance2/`，原session保留；`prepare132.py --scope old500 --runtime-root .local_models/132_midpoint_update/instance2`支持独立保存接续配置。原实例无卡开机，只用于数据回收，不再运行GPU任务。
