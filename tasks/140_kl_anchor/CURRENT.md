# 140 当前状态：已启动

2026-10-31 13:17（UTC+8）核对GPU空闲后启动，控制进程49522。原156个训练ID的缓存已完成，11349-token反向实测峰值24.21 GiB、初始KL为0.000068。现按固定数据/顺序训练48步、384次呈现，之后评价原160条。以上是运行检查，尚无分类结果。

相对138 label_replay只加入0.5×KL(p120||p_current)，T=1。医生GT和完整输入不变，不使用新18条理由，不使用评价数据训练，不重训对照。CPU数学、梯度、因果位置和缓存恢复检查通过，不能作为分类收益。

本阶段计算截止约14:17，另留20分钟保存回传，受09:36:01起20元GPU累计上限约束；API仍0/80。实例不关机、不释放。具体阶段、计数和费用见实时进度。

[进度](../../outputs/140_kl_anchor/progress.md) · [协议](PROTOCOL.md) · [准备](../../outputs/140_kl_anchor/preparation.json) · [CPU检查](../../outputs/140_kl_anchor/cpu_checks.json) · [GPU运行检查](../../outputs/140_kl_anchor/runtime_gate.json)
