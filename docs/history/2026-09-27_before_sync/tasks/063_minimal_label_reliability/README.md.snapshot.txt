# 063：Minimal-label Target Reliability Calibration

063测试target标签预算0/5/10/20/40，比较random、unlabeled active与oracle-balanced采样，目标是补齐zero-label无法恢复的conditional reliability。

主方法用Frozen PriorG×Qwen U0的9种hard joint pattern做Bayesian reliability更新；正式失败。

Protocol Amendment 001进一步保留4维soft log-odds，用few labels直接更新target class means；仍然失败。

两种方法即使oracle-balanced 40 labels也没有在052→053和053→052两个方向同时满足预注册安全改善标准。失败主要表现为false-S上升、NS recall下降。

因此063不能给出“5/10/20/40哪个够”的正阈值；当前证据说明calibrator/decision rule而非单纯标签量是瓶颈。

24项executor verification PASS；0 API；未使用reserved；独立审计未执行。
