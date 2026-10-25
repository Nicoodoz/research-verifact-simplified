# 059 当前状态

059已完成正式执行与executor-side核验，verification_001.json共15项PASS；0 API，未使用reserved，未commit/push，独立审计未执行。

目标：target无GT时，同时估target prior与每个Judge两个低维score drift参数：
- theta_S：整体更偏向/远离Supported；
- theta_NS：整体更偏向NS相对NA。
DeepSeek/Qwen各2维，共4维。

方法：利用DeepSeek+Qwen联合4维log-odds协方差先估prior；全局additive bias不改变协方差。再用target均值残差估theta。

Synthetic n=960：
- prior L1 mean = 0.074；
- theta MAE mean = 0.085；
- 非零drift sign accuracy = 99.66%；
- 三项事前synthetic门槛PASS。

真实052↔053：
- 052→053：prior L1=0.160，theta MAE=0.279，joint R2=0.170；
- 053→052：prior L1=0.117，theta MAE=0.219，joint R2=0.174；
- 两方向真实common-shift R2均远低于事前0.50门槛，因此不进入原计划060。

机制上，真实漂移强烈class-specific。052→053时Qwen的NS-vs-NA log-odds在真NS上约+3.299，但真S/真NA约-0.020/-0.012；DeepSeek也存在真NA/真NS远强于真S的变化。

结论：059证明低维drift“可估”，但当前“每个Judge两个全局bias”不足以描述真实漂移；下一步若继续，应建模class-dependent reliability drift，而不是直接把这4个theta送入动态classifier。

详见report.md。
