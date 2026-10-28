# 105当前入口：新克隆尚不能训练

2026-10-28 GPU接续结果为**执行未完成**。存储已修复，9B原权重和105冻结输入完整；目标缺少已验证的venv103。两臂0/50步、三臂0/500预测，分类指标/继续门槛未评价。

先读[本轮报告](../../outputs/105_brief_supervision/gpu_clone_report.md)、[克隆交接](GPU_CLONE_HANDOFF.md)和[实时进度](../../outputs/105_brief_supervision/gpu_live_progress.md)。科学方案继续使用原[protocol](protocol.md)/[config](config.json)，196/500及所有监督答案不变。

唯一下一动作：在GPU关闭时，通过AutoDL控制台仅把旧实例已验证的`verifact103/venv103`选择性拷贝至新实例同路径。不要整盘复制、重新下载9B或重装环境。源实例只读，保持原件；本轮没有启动旧实例。

本轮GPU按用户11:30、6.98元/小时起计，截至12:07:57关机请求约37.95分钟；加旧无卡最低估算累计约4.470307元，另保留2元共享未知/关机余量。20元与150分钟累计约束不重置，实际结束时间/账单待控制台确认。新账本位于`/root/autodl-tmp/verifact105/budget/ledger.json`，保留了前段未确认区间；后续不得重新init。

旧[GPU_HANDOFF](GPU_HANDOFF.md)、[README](README.md)及[无卡报告](../../outputs/105_brief_supervision/nogpu_report.md)记录原实例无卡准备的READY_FOR_GPU；该历史状态不能替代新克隆环境检查。当前克隆不能直接使用旧命令开训。迁移后先在无卡阶段检查精确版本/token/文件，再按实际剩余时间/费用及短GPU吞吐核算接续，不换样本、不缩减必要对照。

已通过绑定新主机的守卫请求平台关机，随后SSH不可达；**仍需控制台确认“已关机”与最终费用**。若仍运行，请关机并保留实例/磁盘。本轮没有适配器或optimizer，少量最终保存/关机回执留实例待无卡取回。
