# 057：Soft Multi-view Conditional-shift Detection

057测试056的hard-label detector失败是否主要因为连续score信息被压掉。

固定主方法：
- DeepSeek Frozen PriorG hard output → BBSE估target prevalence；
- DeepSeek T-S + Qwen共6维连续scores；
- source-only z-score + RBF Random Fourier Features；
- 比较target soft mean embedding与按BBSE prior重混合的source类条件embedding；
- source纯label-shift重采样给出95% alarm阈值。

结果：soft detector较056 hard detector明显提升conditional-replacement检测率，但n=240两方向仅64.43%和56.57%，仍未达到事前70%门槛；真实052↔053两方向也均未报警。

因此057证明hard压缩确实损失信息，但当前soft multi-view信号仍不足以作为zero-label动态适配的安全开关。0 API、未使用reserved、未自动commit/push。
