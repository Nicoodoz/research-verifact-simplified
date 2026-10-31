# 139 full_repeat：160与匹配控制完成，主臂扩评500

full_repeat160与同运行时claim_control160均全有效；后者与旧136逐条同标签。full_repeat MCC .5848、PA79.375%、正确127、FS16/57；相对匹配控制正确+1、FS−1、ΔMCC+.0142，优势小但保留，正在补原500的缺失340条。

相同120权重、batch1/32768、384输出；控制只用136原输入，未重新训练。160条生成中位耗时full_repeat 3.31秒、控制1.89秒；输入量近2倍，尚未证明额外成本值得。最长25105 tokens首答已通过，峰值21.84 GiB，无截断或额外测速。

只补未生成ID，保留所有首答，不重发旧160；500主臂有信号后才补匹配控制340。2700秒计算＋900秒保存，沿09:36:01起20元GPU/原80元API累计，不关机或释放。

[当前报告](../../outputs/139_full_repeat/report.md) · [160完整统计](../../outputs/139_full_repeat/screen160.json) · [运行时控制](../../outputs/139_full_repeat/claim_control160.json) · [原方案](PROTOCOL.md) · [控制协议](RUNTIME_CONTROL.md) · [实时进度](../../outputs/139_full_repeat/progress.md)
