#139 matched runtime control:160

三者共同有效160/160；缺失/invalid不补旧答案。

|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|
|---|---:|---:|---:|---:|---:|---|
|claim_control|0.570664|78.75%|126|17/57|0.6384|94.17%/25.00%/69.70%|
|full_repeat|0.584838|79.38%|127|16/57|0.6629|94.17%/33.33%/66.67%|
|old136|0.570664|78.75%|126|17/57|0.6384|94.17%/25.00%/69.70%|

full_repeat minus claim_control（N=160）：ΔMCC+0.014175、Δ正确+1、ΔFS-1。

claim_control minus old136（N=160）：ΔMCC+0.000000、Δ正确+0、ΔFS+0。

三类precision/recall/F1、混淆矩阵、false-S率、预测S假发现率、患者方向与作者/面板分组见JSON。
运行时对照不训练、不重跑full_repeat；不能把旧136与控制的差别全归因为单一batch因素。
