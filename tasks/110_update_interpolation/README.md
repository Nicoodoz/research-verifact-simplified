# 110 update_interpolation

[当前状态](CURRENT.md) · [固定方案](protocol.md) · [配置](config.json) · [实时进度](../../outputs/110_update_interpolation/实时进度.md)。

先对109实际192条训练样本做训练后诊断，107训练前预测直接复用109挖掘回执；同时复用105损失函数比较32条原正确NA保留样本的真实标签CE。诊断不用于改插值系数，也不属于方法效果阳性。

仅两个固定点：update_quarter（.25）、update_half（.5）。以共同原9B为底座，准确拼接两端完整LoRA的有效BA/scaling；保留源FP32因子，rank16+16→32，单个BF16底座，不新增训练、SVD或后处理。源107/109与各自500结果保持只读，最多少量真实端点核对，不完整重推旧基线。

- `diagnose110.py`：192预测＋固定32NA两端真实标签CE，无optimizer或反向传播。
- `candidates110.py`：准确cat、逐模块小投影/端点检查、两个固定点各500。
- `runtime110.py`：复用原prompt/parser/解码及完整输入的推理与预算检查。
- `test_cat110.py`：纯CPU小矩阵及错误因子平均反例，使用`pwsh -File scripts/run_research.ps1 tasks/110_update_interpolation/test_cat110.py`。
- `analyze_diagnostic110.py`：配对训练角色、false-S改正/换错、NA保留与真实标签CE。
- `analyze110.py`：统一项目指标、独立sklearn核对、两候选vs107、类别/患者/作者及患者bootstrap。

当前实例11:51起按1.58元/小时累计，任务硬上限5元、API0。用户执行中已改为“完成后不要自动关机”，关机保护及回传后触发均撤销，完成后仅通知并保留实例/磁盘；等待费用继续累计。本地统计结束后按本轮授权双仓库推送；不自动111、扩范围或升级默认。临床原文、私有回执、凭据、权重与缓存不提交GitHub。
