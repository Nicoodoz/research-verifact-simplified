# 141 当前状态：正式160筛查中

15:00启动，控制进程54799，先160条。固定两条原训练侧S/NS完整示例，120权重、136目标user、三类定义和输出格式不变；无新训练，示例不是新监督，未按评价预测选取。

本160最长27154 input tokens；全池上界27962，连384输出为28346，在32768设置内。完整reference不截断；复用139 claim_control160作为batch1/context32768运行设置匹配对照。CPU结构/长度检查和首条运行成功均不代表分类有效。

首阶段1500秒计算＋600秒保存，服从09:36:01起20元GPU累计上限，API0/80。140已完成并回传后才启动本任务，没有GPU重叠；不关机或释放。首批正式结果用于吞吐与显存检查，不另跑测速。

[协议](PROTOCOL.md) · [进度](../../outputs/141_two_demos/progress.md) · [准备](../../outputs/141_two_demos/preparation.json) · [CPU检查](../../outputs/141_two_demos/cpu_check.json)
