# 061 当前状态

061已完成正式执行；0 API，未使用reserved，未commit/push，独立审计未执行。

目标：验证固定target prior能否解决060的prior-drift不可识别性。保持060的12维class-specific drift模型不变，只比较Oracle-fixed prior、BBSE-fixed prior与060 free-prior基线。

核心结论：**Oracle prior也不足以救回060，因此主瓶颈不是prior-drift confounding。**

Synthetic n=960：
- Oracle-fixed：delta MAE=0.407，非零方向识别96.78%，未达MAE<=0.30门槛；
- BBSE-fixed：prior L1=0.092，delta MAE=0.428，方向识别96.04%；
- Oracle diagnostic FAIL，BBSE deployable FAIL。

真实052→053：
- BBSE prior L1=0.023，R2=0.300；Oracle R2=0.307；060 free-prior R2=0.004。
真实053→052：
- BBSE prior L1=0.031，R2=0.066；Oracle R2=0.097；060 free-prior R2=-0.254。

固定prior确实改善060，但远未达到真实R2>=0.50。更关键：synthetic真实无漂移条件，Oracle-fixed仍估出约0.425平均delta MAE，说明Gaussian latent mixture会产生明显伪漂移。

结论：BBSE prevalence sensor当前不是主要瓶颈；下一步应更换/约束class-specific drift表示与估计器，而不是继续修prior。

详见report.md。
