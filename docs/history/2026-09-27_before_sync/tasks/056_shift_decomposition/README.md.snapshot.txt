# 056：Unlabeled Shift Decomposition

056测试target完全无GT时，能否把“类别比例变化”和“Judge类条件行为变化”拆开。

固定方法：
- DeepSeek Frozen PriorG hard label → BBSE估target prevalence；
- DeepSeek×Qwen 9格联合hard-output分布 → label-shift compatibility residual；
- source纯label-shift重采样给出95% alarm阈值；
- 用另一批真实P(D,Q|Y)做conditional replacement压力测试。

结果：事前机制screen未通过。n=240两方向conditional-shift detection为55.17%和38.20%，虽H0误报仅4.13%和5.70%。真实052↔053两方向也均未报警。

因此当前hard-output detector不支持直接进入reliability-gated zero-label adaptation。详见outputs/056_shift_decomposition/report.md与CURRENT_STATUS.md。

0 API、未使用reserved、executor verification 12项PASS；独立审计未执行。
