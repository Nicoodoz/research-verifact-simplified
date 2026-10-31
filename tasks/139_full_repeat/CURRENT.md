# 139 full_repeat：固定160评价运行中

从120 final369原9B权重出发，104 system一份，完整user输入重复两遍；不训练、不添加证据、不截断reference、不修改医生GT。关闭thinking、greedy、384输出、parse105。batch1、32768容量；运行时原始RoPE参数及262144上下文元数据完全一致。

固定160（自然128/压力32）。首个最长正式ID直接用于容量和吞吐检查，成功结果保留，不另行测速。当前尚无分类结果，不以加载成功作为有效性证据。

沿09:36:01新增20元GPU窗口，最多2700秒计算另留900秒保存/回传；原API80元累计0，不关机、不释放。GPU空闲后已独占启动，不与138重叠。

[固定方案](PROTOCOL.md) · [进度](../../outputs/139_full_repeat/progress.md) · [准备统计](../../outputs/139_full_repeat/cpu_preparation.json) · [代码](worker139.py)
