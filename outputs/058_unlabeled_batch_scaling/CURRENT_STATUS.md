# 058 当前状态

058已完成正式执行。完全复用057 soft detector，仅扩大无标签target batch。

核心结果：
- n=240：mean detection 66.3% / 58.5%；
- n=480：86.9% / 79.9%；
- n=960：99.4% / 97.4%，但053方向最难场景仍为86.6%；
- n=1920：两方向六种场景均100%；
- H0 false-alarm始终约4–6%。

因此当前证据支持“样本量是056/057的重要瓶颈”，不能再简单说zero-label里没有Judge drift信息。

边界：n>236/237来自现有经验类条件池有放回重采样，不等价于真实新增独立claims。0 API、未用reserved、未commit/push、独立审计未执行。

详见report.md。
