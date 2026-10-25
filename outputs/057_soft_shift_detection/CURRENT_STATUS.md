# 057 当前状态

057已完成正式执行与executor-side核验，verification_001.json共17项PASS；0 API，未使用reserved，未commit/push，独立审计未执行。

目标：验证056失败是否主要来自hard-label压缩。主方法固定使用DeepSeek T-S + Qwen完整6维scores，经source-only标准化与128维RBF Random Fourier Features形成soft mean-embedding residual；BBSE仍只负责估target prevalence。

核心结果：**soft detector比056 hard detector明显更敏感，但事前机制screen仍FAIL。**
- n=240，source=052：H0误报4.60%，H1 detection 64.43%；056 hard为55.17%，+9.27pp。
- n=240，source=053：H0误报4.87%，H1 detection 56.57%；056 hard为38.20%，+18.37pp。
- 两方向仍低于事前70% detection门槛。
- n=480时检测升至88.33% / 81.87%，说明soft signal在更大batch下明显增强。

真实052↔053无标签batch：
- 052→053 joint residual 0.0302 < q95 0.0420，p=0.2324，不报警；
- 053→052 joint residual 0.0370 < q95 0.0510，p=0.2379，不报警；
- DeepSeek-only与Qwen-only ablation也均不报警。

解盲后，055 source-only Qwen label-model在052→053虽PA/MCC略升，但false-S +4、NS recall -21.4pp；053→052则PA -3.39pp、MCC -0.081。057仍未提前抓住这两个实际安全退化环境。

结论：056的hard压缩确实丢失conditional-shift信息，但现有DeepSeek+Qwen soft scores仍不足以充当zero-label动态adaptation的安全开关。按事前协议不继续调RFF维度、bandwidth、transform或阈值。

正式报告见report.md。
