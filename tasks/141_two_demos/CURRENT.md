# 141 当前状态：CPU_READY

可运行的原160条包已形成并通过CPU检查，尚未运行GPU。固定两条原训练侧S/NS完整示例，120权重、136目标user、三类定义和输出格式不变。示例不是新监督，未按评价预测选取。

本160最长27154 input tokens；全池上界27962，连384输出为28346，在32768容量内。完整reference不截断；保留既有139 claim_control160为运行设置匹配对照。CPU结构/长度检查不代表分类有效。

首阶段1500秒计算＋600秒保存，服从本轮20元GPU累计上限，API0。140仍在运行，依据其正式结果选择下一项，本任务不抢占GPU、不关机或释放。

[协议](PROTOCOL.md) · [准备](../../outputs/141_two_demos/preparation.json) · [CPU检查](../../outputs/141_two_demos/cpu_check.json)
