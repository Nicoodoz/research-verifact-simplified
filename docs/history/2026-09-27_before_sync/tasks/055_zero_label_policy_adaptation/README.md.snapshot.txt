# 055：Zero-label Adaptation

055研究新环境完全没有target GT时，能否自动适应类别prevalence和判定策略。初始阶段仅使用既有DeepSeek outputs；在该路线跨环境不稳定后，根据用户“实现方法不限、目标是zero-label adaptation”的要求，通过Protocol Amendment 001加入完整Qwen second opinion。

最终结果：无标签prevalence估计和shift detection已经可行；Qwen提供明显互补NS信号；若允许看target评价结果，可以找到显著优于PriorG的工作点。但当超参数/是否启用adaptation严格只由source患者CV决定时，跨052↔053不能稳定复制，安全selector最终在两方向均回退Frozen PriorG。

因此055没有宣称已经实现稳定通用的zero-label automatic adaptation。正式报告见`../../outputs/055_zero_label_policy_adaptation/report.md`；状态见`CURRENT_STATUS.md`；完整性见`verification_001.json`。

Full Qwen extension：429新调用 + 51复用，实际费用7.451754 CNY，429/429完成。未自动commit/push。
