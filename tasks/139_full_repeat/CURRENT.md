# 139 full_repeat：160完成，运行时对照进行中

full_repeat160全有效：MCC .5848、PA79.375%、正确127、FS16/57。相对120正确+5/FS−4；相对旧136仅+1/−1。完整输入量约1.9955倍，尚不能据小幅差异判定成本值得。

初筛后追加claim_control：同一120权重、同batch1/32768容量和384生成，只使用原136输入。当前正在运行，比较后再决定是否扩大；这不是换种子复验或重复训练。原full_repeat和136结果均保留。

最长正式样本25105 tokens已完成，峰值21.84 GiB；原RoPE/上下文参数一致。不截断、不重发、不改GT。沿09:36:01起20元GPU，原API80累计0，不关机或释放。

[初筛报告](../../outputs/139_full_repeat/report.md) · [追加控制协议](RUNTIME_CONTROL.md) · [原方案](PROTOCOL.md) · [实时进度](../../outputs/139_full_repeat/progress.md)
